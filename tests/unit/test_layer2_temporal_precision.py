from __future__ import annotations

from pathlib import Path

from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import retrieve_with_chronorag_adapter
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase, load_corpus, load_questions
from benchmarks.layer2_crossdomain.temporal_precision import extract_temporal_constraints, score_temporal_precision


ROOT = Path(__file__).resolve().parents[2]
REAL_CORPUS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
REAL_QUESTIONS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl"


def _constraint(text: str):
    return extract_temporal_constraints(text)[0]


def _case(question: str, category: str = "exact_valid_time_retrieval", expected_valid_time: list[str] | None = None) -> QuestionCase:
    return QuestionCase(
        id="test",
        domain="macro_fred",
        question=question,
        category=category,
        expected_behavior="answer",
        expected_evidence_ids=[],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=[],
        forbidden_facts=[],
        expected_valid_time=expected_valid_time or [],
        notes="test",
    )


def _row(row_id: str, valid_from: str | None, valid_to: str | None = None, temporal_type: str = "valid_time_exact", transaction_time: str | None = None) -> CorpusRow:
    return CorpusRow(
        id=row_id,
        domain="macro_fred",
        source_family="macro_fred",
        source_file="fixture",
        source_kind="time_series",
        entity="United States",
        related_entities=[],
        metric_or_claim="yield",
        value="1.0",
        unit="percent",
        valid_from=valid_from,
        valid_to=valid_to or valid_from,
        transaction_time=transaction_time,
        temporal_type=temporal_type,
        raw_text="fixture",
    )


def test_extract_yyyy_mm_dd():
    c = _constraint("yield on 1962-08-15")
    assert c.normalized_start == "1962-08-15"
    assert c.granularity == "day"


def test_extract_unambiguous_dd_mm_yyyy():
    c = _constraint("yield on 13/04/2024")
    assert c.normalized_start == "2024-04-13"


def test_ambiguous_numeric_date_marked_ambiguous():
    c = _constraint("yield on 03/04/2024")
    assert c.ambiguous_parse is True


def test_extract_month_dd_yyyy():
    c = _constraint("released on October 23, 2024")
    assert c.normalized_start == "2024-10-23"


def test_extract_dd_month_yyyy():
    c = _constraint("released on 23 October 2024")
    assert c.normalized_start == "2024-10-23"


def test_extract_hh_mm():
    c = _constraint("at 14:30")
    assert c.normalized_start == "14:30:00"
    assert c.granularity == "minute"


def test_extract_hh_mm_ss():
    c = _constraint("at 14:30:15")
    assert c.normalized_start == "14:30:15"
    assert c.granularity == "second"


def test_extract_noon():
    c = _constraint("at noon")
    assert c.normalized_start == "12:00:00"


def test_extract_midnight():
    c = _constraint("at midnight")
    assert c.normalized_start == "00:00:00"


def test_extract_dayparts():
    constraints = {item.original_text.lower(): item for item in extract_temporal_constraints("morning afternoon evening night")}
    assert constraints["morning"].normalized_start == "06:00:00"
    assert constraints["afternoon"].normalized_start == "12:00:00"
    assert constraints["evening"].normalized_start == "17:00:00"
    assert constraints["night"].normalized_start == "21:00:00"


def test_extract_early_mid_late_year():
    items = {item.original_text.lower(): item for item in extract_temporal_constraints("early 2024 mid 2025 late 2026")}
    assert items["early 2024"].normalized_start == "2024-01-01"
    assert items["mid 2025"].normalized_start == "2025-05-01"
    assert items["late 2026"].normalized_start == "2026-09-01"


def test_extract_early_mid_late_month():
    items = {item.original_text.lower(): item for item in extract_temporal_constraints("early December 2024 mid January 2025 late February 2026")}
    assert items["early december 2024"].normalized_end == "2024-12-10"
    assert items["mid january 2025"].normalized_start == "2025-01-11"
    assert items["late february 2026"].normalized_start == "2026-02-21"


def test_extract_q1_q2_q3_q4():
    items = {item.original_text.lower(): item for item in extract_temporal_constraints("Q1 2024 Q2 2024 Q3 2024 Q4 2024")}
    assert items["q1 2024"].normalized_start == "2024-01-01"
    assert items["q2 2024"].normalized_start == "2024-04-01"
    assert items["q3 2024"].normalized_start == "2024-07-01"
    assert items["q4 2024"].normalized_start == "2024-10-01"


def test_extract_named_quarters():
    items = {item.original_text.lower(): item for item in extract_temporal_constraints("first quarter 2024 second quarter 2024 third quarter 2024 fourth quarter 2024")}
    assert items["first quarter 2024"].normalized_start == "2024-01-01"
    assert items["second quarter 2024"].normalized_start == "2024-04-01"
    assert items["third quarter 2024"].normalized_start == "2024-07-01"
    assert items["fourth quarter 2024"].normalized_start == "2024-10-01"


def test_extract_before_after_between_from_to():
    texts = [
        "before 2024-10-23",
        "after 2024-10-23",
        "between 2024-10-20 and 2024-10-23",
        "from 2024-10-20 to 2024-10-23",
    ]
    assert all(extract_temporal_constraints(text)[0].granularity == "range" for text in texts)


def test_extract_around_year():
    c = _constraint("around 2024")
    assert c.normalized_start == "2024-01-01"
    assert c.normalized_end == "2024-12-31"


def test_extract_around_exact_date():
    c = _constraint("around 2024-10-23")
    assert c.normalized_start == "2024-10-20"
    assert c.normalized_end == "2024-10-26"


def test_score_exact_date_above_same_year_wrong_date():
    case = _case("What was the yield on 1962-08-15?")
    exact = score_temporal_precision(case, _row("exact", "1962-08-15"))
    wrong = score_temporal_precision(case, _row("wrong", "1962-01-18"))
    assert exact > wrong


def test_score_exact_month_above_same_year_outside_month():
    case = _case("What was the yield in August 1962?")
    in_month = score_temporal_precision(case, _row("month", "1962-08-15"))
    outside = score_temporal_precision(case, _row("outside", "1962-01-18"))
    assert in_month > outside


def test_score_timestamp_exact_match_above_same_day_wrong_time():
    case = _case("What happened on 2024-10-23T14:30:22?")
    exact = score_temporal_precision(case, _row("exact", "2024-10-23T14:30:22"))
    wrong = score_temporal_precision(case, _row("wrong", "2024-10-23T15:30:22"))
    assert exact > wrong


def test_transaction_time_only_penalized_for_valid_time_query():
    case = _case("What was the value on 2024-10-23?")
    tx = score_temporal_precision(case, _row("tx", None, temporal_type="transaction_time_only", transaction_time="2024-10-23"))
    valid = score_temporal_precision(case, _row("valid", "2024-10-23"))
    assert valid > tx


def test_transaction_time_only_allowed_for_publication_query():
    case = _case("Which publication records were published on 2024-10-23?", category="transaction_time_vs_valid_time")
    tx = score_temporal_precision(case, _row("tx", None, temporal_type="transaction_time_only", transaction_time="2024-10-23"))
    assert tx >= 0.7


def test_chronorag_adapter_first_five_expected_ids_in_top5():
    corpus = load_corpus(REAL_CORPUS)
    questions = load_questions(REAL_QUESTIONS)[:5]
    expected = [
        "l2:github_releases:kubernetes:181360153",
        "l2:github_releases:pandas:6599258",
        "l2:macro_fred:dgs10:1962-08-15",
        "l2:macro_fred:dgs10:1974-06-20",
        "l2:macro_fred:dgs10:1986-05-22",
    ]
    assert [case.expected_evidence_ids[0] for case in questions] == expected
    for case in questions:
        rows, metadata = retrieve_with_chronorag_adapter(case, corpus, top_k=5)
        ids = [row.id for row in rows]
        assert case.expected_evidence_ids[0] in ids
        assert metadata["temporal_precision_applied"] is True


def test_metadata_temporal_rag_remains_independent():
    retrieval_source = (ROOT / "benchmarks/layer2_crossdomain/methods/metadata_temporal_rag/retrieval.py").read_text(encoding="utf-8")
    assert "chronorag_full" not in retrieval_source
    assert "temporal_contextual_chunker" not in retrieval_source
    assert "monotone_temporal_fusion" not in retrieval_source
