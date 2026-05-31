from __future__ import annotations

import json
from pathlib import Path

from benchmarks.layer2_crossdomain.evaluate_retrieval_only import compare_reports, evaluate_result_file, score_case
from benchmarks.layer2_crossdomain.schemas import QuestionCase


def _case(
    *,
    case_id: str = "case",
    category: str = "exact_valid_time_retrieval",
    expected: list[str] | None = None,
    acceptable: list[str] | None = None,
    forbidden: list[str] | None = None,
    behavior: str = "answer",
    question: str = "What happened in 2020?",
    synthetic: list[str] | None = None,
) -> QuestionCase:
    return QuestionCase(
        id=case_id,
        domain="fixture",
        question=question,
        category=category,  # type: ignore[arg-type]
        expected_behavior=behavior,  # type: ignore[arg-type]
        expected_evidence_ids=expected or ["target"],
        acceptable_evidence_ids=acceptable or [],
        forbidden_evidence_ids=forbidden or [],
        required_facts=[],
        forbidden_facts=[],
        expected_valid_time=["2020"],
        notes="fixture",
        synthetic_evidence_ids=synthetic or [],
    )


def test_exact_valid_time_scoring_keeps_generic_and_category_metrics():
    report = score_case(_case(expected=["target"], forbidden=["bad"]), ["target", "bad"])
    scores = report["scores"]
    assert scores["generic_hit@1"] is True
    assert scores["expected_hit_at_1"] is True
    assert scores["expected_hit_at_k"] is True
    assert scores["generic_forbidden_absent@5"] is False
    assert scores["forbidden_absent_at_k"] is False
    assert scores["category_primary_pass"] is False
    assert report["retrieval_pass_reason"] == "fail: forbidden_absent_at_k"


def test_selected_evidence_ids_drive_scoring_not_answer_text(tmp_path: Path):
    questions = {"case_ok": _case(case_id="case_ok", expected=["target"], forbidden=["bad"])}
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            {
                "method": "fixture_method",
                "results": [
                    {
                        "case_id": "case_ok",
                        "selected_evidence_ids": ["target"],
                        "answer": {
                            "answer": "DRY RUN: prompt generated without provider call.",
                            "cited_evidence_ids": ["bad"],
                            "behavior": "partial",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    report = evaluate_result_file(path, questions)
    case_report = report["case_reports"][0]
    assert case_report["scores"]["expected_hit_at_k"] is True
    assert case_report["scores"]["forbidden_absent_at_k"] is True
    assert case_report["retrieval_pass"] is True


def test_transaction_time_scoring_requires_valid_hit_and_forbidden_absence():
    report = score_case(
        _case(category="transaction_time_vs_valid_time", expected=["valid"], forbidden=["transaction_only"]),
        ["valid", "transaction_only"],
    )
    scores = report["scores"]
    assert scores["valid_time_hit_at_k"] is True
    assert scores["transaction_time_trap_avoidance"] is False
    assert scores["category_primary_pass"] is False


def test_wrong_year_scoring_flags_malformed_question():
    report = score_case(
        _case(
            category="same_entity_wrong_year_trap",
            expected=["target_1968"],
            forbidden=["wrong_1969"],
            question="For GDP in 1968, answer for 1968, not 1968.",
        ),
        ["target_1968"],
    )
    assert "malformed_wrong_year_question" in report["warnings"]
    assert report["scores"]["malformed_wrong_year_question"] is True


def test_conflict_detection_requires_two_sides_when_two_expected_ids_exist():
    one_side = score_case(
        _case(category="conflict_detection", expected=["side_a", "side_b"], behavior="conflict_warning"),
        ["side_a"],
    )
    both_sides = score_case(
        _case(category="conflict_detection", expected=["side_a", "side_b"], behavior="conflict_warning"),
        ["side_a", "side_b"],
    )
    assert one_side["scores"]["conflict_side_coverage@5"] is False
    assert one_side["scores"]["category_primary_pass"] is False
    assert both_sides["scores"]["conflict_side_coverage@5"] is True
    assert both_sides["scores"]["category_primary_pass"] is True


def test_behavior_target_categories_do_not_use_primary_retrieval_pass():
    report = score_case(
        _case(category="ambiguous_time_query", expected=["maybe"], behavior="clarify"),
        ["unrelated"],
    )
    assert report["scores"]["category_primary_pass"] is None
    assert "behavior_target_clarify" not in report["scores"]
    assert "answer_semantics_not_scored_by_retrieval_validator" in report["warnings"]


def test_evaluate_result_file_reports_skips_and_missing_cases(tmp_path: Path):
    questions = {
        "case_ok": _case(case_id="case_ok", expected=["target"]),
        "case_missing": _case(case_id="case_missing", expected=["target2"]),
    }
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps(
            {
                "method": "fixture_method",
                "results": [
                    {"case_id": "case_ok", "selected_evidence_ids": ["target"]},
                    {"case_id": "unknown", "selected_evidence_ids": ["target"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    report = evaluate_result_file(path, questions)
    assert report["benchmark_cases_total"] == 2
    assert report["result_rows_total"] == 2
    assert report["evaluated_cases"] == 1
    assert report["skipped_cases"] == 2
    assert report["skip_reasons"]["case_id not found in benchmark questions"] == 1
    assert report["skip_reasons"]["benchmark case missing from result file"] == 1


def test_pairwise_comparison_uses_same_case_ids(tmp_path: Path):
    questions = {
        "a": _case(case_id="a", expected=["target_a"]),
        "b": _case(case_id="b", expected=["target_b"]),
    }
    left_path = tmp_path / "left.json"
    right_path = tmp_path / "right.json"
    left_path.write_text(
        json.dumps({"method": "left", "results": [{"case_id": "a", "selected_evidence_ids": ["target_a"]}]}),
        encoding="utf-8",
    )
    right_path.write_text(
        json.dumps(
            {
                "method": "right",
                "results": [
                    {"case_id": "a", "selected_evidence_ids": ["miss"]},
                    {"case_id": "b", "selected_evidence_ids": ["target_b"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    left = evaluate_result_file(left_path, questions)
    right = evaluate_result_file(right_path, questions)
    comparison = compare_reports([left, right], questions)
    assert comparison["common_evaluated_cases"] == 1
    assert comparison["generic_hit@5"]["left_only"] == 1
    assert comparison["right_only_evaluated_cases"] == ["b"]
