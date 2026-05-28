from __future__ import annotations

from benchmarks.layer2_crossdomain.prompts import build_evidence_fact_sentence, build_grounded_prompt
from benchmarks.layer2_crossdomain.run_layer2_comparison import _postprocess_answer_with_cited_evidence
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


def _fred_row() -> CorpusRow:
    return CorpusRow(
        id="l2:macro_fred:dgs10:1962-08-15",
        domain="macro_fred",
        source_family="macro_fred",
        source_file="dgs10.csv",
        source_kind="time_series",
        entity="United States 10-year Treasury",
        related_entities=["DGS10"],
        metric_or_claim="10-year Treasury yield",
        value="3.98",
        unit="percent",
        valid_from="1962-08-15",
        valid_to="1962-08-15",
        transaction_time=None,
        temporal_type="valid_time_exact",
        raw_text="United States 10-year Treasury 10-year Treasury yield was 3.98 percent on 1962-08-15.",
    )


def _github_row() -> CorpusRow:
    return CorpusRow(
        id="l2:github_releases:kubernetes:181360153",
        domain="github_releases",
        source_family="github_releases",
        source_file="kubernetes_releases.json",
        source_kind="github_release",
        entity="kubernetes",
        related_entities=["v1.30.6"],
        metric_or_claim="release v1.30.6",
        value="v1.30.6",
        unit=None,
        valid_from="2024-10-23",
        valid_to="2024-10-23",
        transaction_time="2024-10-23",
        temporal_type="valid_time_exact",
        raw_text="kubernetes released v1.30.6 on 2024-10-23.",
    )


def _case() -> QuestionCase:
    return QuestionCase(
        id="case",
        domain="macro_fred",
        question="What was United States 10-year Treasury yield on 1962-08-15?",
        category="exact_valid_time_retrieval",
        expected_behavior="answer",
        expected_evidence_ids=["l2:macro_fred:dgs10:1962-08-15"],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=["United States 10-year Treasury", "1962", "3.98"],
        forbidden_facts=[],
        expected_valid_time=["1962"],
        notes="fixture",
    )


def test_prompt_evidence_packet_includes_structured_fields():
    prompt = build_grounded_prompt(_case(), [_fred_row()], "chronorag_full")
    for token in (
        '"id"',
        '"domain"',
        '"entity"',
        '"metric_or_claim"',
        '"value"',
        '"unit"',
        '"valid_from"',
        '"valid_to"',
        '"transaction_time"',
        '"temporal_type"',
        '"raw_text"',
    ):
        assert token in prompt


def test_prompt_excludes_answer_key_fields():
    prompt = build_grounded_prompt(_case(), [_fred_row()], "chronorag_full")
    for forbidden in (
        "required_facts",
        "forbidden_facts",
        "expected_evidence_ids",
        "acceptable_evidence_ids",
        "forbidden_evidence_ids",
        "expected_valid_time",
        "expected_behavior",
    ):
        assert forbidden not in prompt


def test_prompt_instructs_answer_field_to_include_required_evidence_facts():
    prompt = build_grounded_prompt(_case(), [_fred_row()], "chronorag_full")
    assert 'the JSON "answer" field MUST include the entity, metric_or_claim, value, unit if available' in prompt
    assert "Do not answer with only a number and unit" in prompt


def test_evidence_fact_sentence_for_fred_row():
    assert (
        build_evidence_fact_sentence(_fred_row())
        == "United States 10-year Treasury 10-year Treasury yield was 3.98 percent on 1962-08-15."
    )


def test_evidence_fact_sentence_for_github_release_row():
    assert build_evidence_fact_sentence(_github_row()) == "kubernetes release v1.30.6 was v1.30.6 on 2024-10-23."


def test_postprocessor_appends_missing_cited_evidence_facts():
    answer, metadata = _postprocess_answer_with_cited_evidence(
        {
            "answer": "The yield was 3.98.",
            "behavior": "answer",
            "cited_evidence_ids": ["l2:macro_fred:dgs10:1962-08-15"],
            "valid_time_used": ["1962-08-15"],
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": False,
            "clarification_requested": False,
            "confidence": "high",
        },
        [_fred_row()],
    )
    assert metadata["answer_fact_postprocessed"] is True
    assert "United States 10-year Treasury 10-year Treasury yield was 3.98 percent on 1962-08-15." in answer["answer"]


def test_postprocessor_does_not_run_for_partial_refuse_or_clarify():
    for behavior in ("partial", "refuse", "clarify"):
        answer, metadata = _postprocess_answer_with_cited_evidence(
            {
                "answer": "Evidence is insufficient.",
                "behavior": behavior,
                "cited_evidence_ids": ["l2:macro_fred:dgs10:1962-08-15"],
            },
            [_fred_row()],
        )
        assert metadata["answer_fact_postprocessed"] is False
        assert answer["answer"] == "Evidence is insufficient."


def test_postprocessor_does_not_use_uncited_evidence():
    answer, metadata = _postprocess_answer_with_cited_evidence(
        {
            "answer": "The yield was 3.98.",
            "behavior": "answer",
            "cited_evidence_ids": ["missing"],
        },
        [_fred_row()],
    )
    assert metadata["answer_fact_postprocessed"] is False
    assert answer["answer"] == "The yield was 3.98."
