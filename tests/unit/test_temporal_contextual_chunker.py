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
