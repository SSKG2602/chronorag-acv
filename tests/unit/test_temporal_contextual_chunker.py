from __future__ import annotations

from core.ingestion.temporal_contextual_chunker import (
    build_temporal_contextual_chunks,
    infer_temporal_metadata,
)


def test_explicit_year_in_text_creates_exact_valid_window() -> None:
    temporal = infer_temporal_metadata("GDP per capita in Western Europe was 1,960 in 1870.")

    assert temporal.valid_from == "1870-01-01"
    assert temporal.valid_to == "1870-12-31"
    assert temporal.granularity == "year"
    assert temporal.temporal_source == "chunk_explicit"
    assert temporal.temporal_confidence == 0.95
    assert temporal.temporal_ambiguity is False


def test_row_metadata_year_creates_exact_valid_window() -> None:
    temporal = infer_temporal_metadata(
        "Western Europe GDP per capita benchmark.",
        payload={"year": 1913},
    )

    assert temporal.valid_from == "1913-01-01"
    assert temporal.valid_to == "1913-12-31"
    assert temporal.temporal_source == "row_metadata"
    assert temporal.temporal_confidence == 0.90


def test_section_range_creates_broad_lower_confidence_window() -> None:
    temporal = infer_temporal_metadata(
        "GDP per capita increased during the period.",
        payload={"section": "Western Europe GDP per capita 1870-1913"},
    )

    assert temporal.valid_from == "1870-01-01"
    assert temporal.valid_to == "1913-12-31"
    assert temporal.granularity == "range"
    assert temporal.temporal_source == "section_range"
    assert temporal.temporal_confidence < 0.90


def test_publication_year_is_transaction_time_only() -> None:
    temporal = infer_temporal_metadata("This OECD publication was released in 2006.")

    assert temporal.valid_from is None
    assert temporal.valid_to is None
    assert temporal.tx_start == "2006-01-01"
    assert temporal.temporal_source == "document_tx_time"
    assert temporal.temporal_ambiguity is True


def test_no_timestamp_is_unknown_valid_time() -> None:
    temporal = infer_temporal_metadata("Historical GDP estimates use purchasing power parity adjustments.")

    assert temporal.valid_from is None
    assert temporal.valid_to is None
    assert temporal.temporal_source == "unknown"
    assert temporal.temporal_confidence == 0.0
    assert temporal.temporal_ambiguity is True


def test_multiple_years_are_split_when_sentence_boundaries_are_safe() -> None:
    chunks = build_temporal_contextual_chunks(
        "GDP per capita was 1,960 in 1870. GDP per capita was 3,473 in 1913.",
        payload={"section": "Western Europe GDP per capita"},
        facets={"domain": "world-economy", "source": "oecd-maddison"},
        uri="file:///mnt/data/world_economy.pdf",
        units=["intl_1990_usd"],
        entities=["Region:Western Europe"],
    )

    assert len(chunks) == 2
    assert {chunk.temporal.valid_from for chunk in chunks} == {"1870-01-01", "1913-01-01"}


def test_multiple_years_without_safe_split_are_marked_ambiguous() -> None:
    temporal = infer_temporal_metadata("GDP per capita values for 1870 and 1913 are listed together.")

    assert temporal.temporal_ambiguity is True
    assert temporal.temporal_confidence < 0.95


def test_context_inferred_time_is_lower_confidence_than_explicit_text() -> None:
    section_temporal = infer_temporal_metadata(
        "GDP per capita increased during the period.",
        payload={"section": "Western Europe GDP per capita 1870-1913"},
    )
    explicit_temporal = infer_temporal_metadata("GDP per capita was 1,960 in 1870.")

    assert section_temporal.temporal_confidence < explicit_temporal.temporal_confidence
    assert section_temporal.temporal_source == "section_range"


def test_raw_text_is_preserved_separately_from_retrieval_text() -> None:
    raw = "GDP per capita in Western Europe was 1,960 in 1870."
    chunk = build_temporal_contextual_chunks(
        raw,
        payload={"section": "Western Europe GDP per capita"},
        facets={"domain": "world-economy", "source": "oecd-maddison"},
        uri="file:///mnt/data/world_economy.pdf",
        units=["intl_1990_usd"],
        entities=["Region:Western Europe"],
    )[0]

    assert chunk.raw_text == raw
    assert chunk.retrieval_text != raw
    assert "Original chunk:" in chunk.retrieval_text
    assert "Document:" in chunk.retrieval_text
    assert "Temporal scope: 1870." in chunk.retrieval_text
    assert len(chunk.retrieval_text.split()) < 100


def test_exact_iso_date_preserved_as_day_precision() -> None:
    raw = "United States 10-year Treasury yield was 3.98 percent on 1962-08-15."
    chunk = build_temporal_contextual_chunks(raw)[0]

    assert chunk.raw_text == raw
    assert chunk.temporal.normalized_start == "1962-08-15"
    assert chunk.temporal.normalized_end == "1962-08-15"
    assert chunk.temporal.precision == "day"
    assert chunk.temporal.temporal_role == "valid_time"
    assert "[valid_time=1962-08-15 precision=day]" in chunk.retrieval_text


def test_datetime_preserved_to_second_precision() -> None:
    temporal = infer_temporal_metadata("The incident happened on 2024-10-23T14:30:22.")

    assert temporal.normalized_start == "2024-10-23T14:30:22"
    assert temporal.precision == "second"
    assert temporal.valid_from == "2024-10-23"


def test_datetime_preserved_to_minute_precision() -> None:
    temporal = infer_temporal_metadata("The incident happened on 2024-10-23 14:30.")

    assert temporal.normalized_start == "2024-10-23T14:30:00"
    assert temporal.precision == "minute"


def test_noon_and_midnight_normalize_to_exact_times() -> None:
    noon = infer_temporal_metadata("The event happened at noon.")
    midnight = infer_temporal_metadata("The event happened at midnight.")

    assert noon.normalized_start == "12:00:00"
    assert midnight.normalized_start == "00:00:00"


def test_dayparts_become_ranges() -> None:
    morning = infer_temporal_metadata("The update happened in the morning.")
    night = infer_temporal_metadata("The update happened at night.")

    assert morning.normalized_start == "06:00:00"
    assert morning.normalized_end == "11:59:59"
    assert morning.precision == "daypart"
    assert night.normalized_start == "21:00:00"
    assert night.normalized_end == "05:59:59"


def test_mid_december_2024_becomes_fuzzy_range() -> None:
    temporal = infer_temporal_metadata("The rule changed in mid December 2024.")

    assert temporal.normalized_start == "2024-12-11"
    assert temporal.normalized_end == "2024-12-20"
    assert temporal.precision == "fuzzy"


def test_q2_2024_becomes_quarter_range() -> None:
    temporal = infer_temporal_metadata("The filing applied in Q2 2024.")

    assert temporal.normalized_start == "2024-04-01"
    assert temporal.normalized_end == "2024-06-30"
    assert temporal.precision == "range"


def test_transaction_time_phrase_is_not_marked_valid_time() -> None:
    temporal = infer_temporal_metadata("The document was published on 2025-05-19.")

    assert temporal.valid_from is None
    assert temporal.tx_start == "2025-05-19"
    assert temporal.temporal_role == "publication_time"


def test_valid_time_phrase_is_not_marked_transaction_time() -> None:
    temporal = infer_temporal_metadata("The yield was 3.98 percent on 1962-08-15.")

    assert temporal.valid_from == "1962-08-15"
    assert temporal.temporal_role == "valid_time"


def test_valid_time_and_publication_time_remain_separate() -> None:
    temporal = infer_temporal_metadata("Data for 1870 was published in 2006.")

    assert temporal.valid_from == "1870-01-01"
    assert temporal.tx_start == "2006-01-01"
    assert temporal.temporal_role == "valid_time"
    roles = {item["original_text"]: item["temporal_role"] for item in temporal.temporal_constraints}
    assert roles["1870"] == "valid_time"
    assert roles["2006"] == "publication_time"


def test_ambiguous_numeric_date_is_marked_ambiguous() -> None:
    temporal = infer_temporal_metadata("The event happened on 03/04/2024.")

    assert temporal.ambiguous_parse is True
    assert temporal.temporal_ambiguity is True
