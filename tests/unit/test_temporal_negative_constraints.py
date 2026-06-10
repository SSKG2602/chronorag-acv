from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import retrieve_with_chronorag_adapter
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase, load_corpus, load_questions
from benchmarks.layer2_crossdomain.temporal_precision import (
    extract_temporal_constraints,
    has_negative_exact_temporal_match,
    score_temporal_precision,
)


ROOT = Path(__file__).resolve().parents[2]
REAL_CORPUS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
REAL_QUESTIONS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl"


def _case(question: str, expected_valid_time: list[str] | None = None) -> QuestionCase:
    return QuestionCase(
        id="test",
        domain="macro_fred",
        question=question,
        category="same_entity_wrong_time_trap",
        expected_behavior="answer",
        expected_evidence_ids=[],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=[],
        forbidden_facts=[],
        expected_valid_time=expected_valid_time or [],
        notes="test",
    )


def _row(row_id: str, valid_from: str) -> CorpusRow:
    return CorpusRow(
        id=row_id,
        domain="macro_fred",
        source_family="macro_fred",
        source_file="fixture",
        source_kind="time_series",
        entity="United States 10-year Treasury",
        related_entities=[],
        metric_or_claim="10-year Treasury yield",
        value="1.0",
        unit="percent",
        valid_from=valid_from,
        valid_to=valid_from,
        transaction_time=None,
        temporal_type="valid_time_exact",
        raw_text=f"United States 10-year Treasury yield was 1.0 percent on {valid_from}.",
    )


def test_positive_date_extraction_defaults_to_positive() -> None:
    constraints = extract_temporal_constraints("yield for 1990-04-20")
    assert constraints[0].normalized_start == "1990-04-20"
    assert constraints[0].polarity == "positive"


def test_negative_date_extraction_after_not() -> None:
    constraints = {item.normalized_start: item for item in extract_temporal_constraints("yield for 1990-04-20, not 1990-03-28")}
    assert constraints["1990-04-20"].polarity == "positive"
    assert constraints["1990-03-28"].polarity == "negative"


@pytest.mark.parametrize(
    ("question", "negative_date"),
    [
        ("yield for 2022-03-25 rather than 2022-03-03", "2022-03-03"),
        ("yield for 2024-04-23 instead of 2024-04-01", "2024-04-01"),
        ("yield for 1968-12-30 excluding 1968-12-05", "1968-12-05"),
        ("yield for 1968-12-30 as opposed to 1968-12-05", "1968-12-05"),
    ],
)
def test_negative_phrase_variants(question: str, negative_date: str) -> None:
    constraints = {item.normalized_start: item for item in extract_temporal_constraints(question)}
    assert constraints[negative_date].polarity == "negative"


def test_negative_date_penalty_makes_target_score_higher() -> None:
    case = _case("For Treasury yield, answer value for 1990-04-20, not 1990-03-28.")
    target = score_temporal_precision(case, _row("target", "1990-04-20"))
    forbidden = score_temporal_precision(case, _row("forbidden", "1990-03-28"))
    assert target > forbidden
    assert forbidden == 0.0


def test_negative_exact_match_detects_forbidden_row_only() -> None:
    case = _case("For Treasury yield, answer value for 1990-04-20, not 1990-03-28.")
    constraints = extract_temporal_constraints(case.question)
    assert has_negative_exact_temporal_match(case, _row("forbidden", "1990-03-28"), constraints)
    assert not has_negative_exact_temporal_match(case, _row("target", "1990-04-20"), constraints)
    assert not has_negative_exact_temporal_match(case, _row("same_year", "1990-05-01"), constraints)


def test_year_only_query_has_no_negative_constraints_and_scores_normally() -> None:
    case = _case("What was the yield in 1990?")
    constraints = extract_temporal_constraints(case.question)
    assert constraints
    assert all(item.polarity == "positive" for item in constraints)
    assert score_temporal_precision(case, _row("target", "1990-04-20")) > 0.0


def test_layer2_same_time_traps_rank_expected_above_forbidden() -> None:
    corpus = load_corpus(REAL_CORPUS)
    cases = [
        case
        for case in load_questions(REAL_QUESTIONS)
        if case.category == "same_entity_wrong_time_trap"
        and case.expected_evidence_ids
        and case.forbidden_evidence_ids
    ][:3]

    assert len(cases) >= 3

    for case in cases:
        rows, _metadata = retrieve_with_chronorag_adapter(case, corpus, top_k=5)
        selected = [row.id for row in rows]
        expected = case.expected_evidence_ids[0]
        forbidden = case.forbidden_evidence_ids[0]
        assert expected in selected
        assert selected[0] != forbidden
        if forbidden in selected:
            assert selected.index(expected) < selected.index(forbidden)
