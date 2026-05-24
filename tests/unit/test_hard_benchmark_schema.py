from __future__ import annotations

import json
from pathlib import Path


CASES = Path("benchmarks/temporal_qa_hard_15.jsonl")
DATASET = Path("data/sample/hard_temporal")
ALLOWED_BEHAVIORS = {
    "success",
    "partial",
    "conflict_warning",
    "insufficient_evidence",
    "ambiguity",
}
REQUIRED_FIELDS = {
    "id",
    "question",
    "expected_valid_window",
    "expected_source",
    "expected_text_signals",
    "expected_behavior",
    "difficulty",
    "feature_tested",
    "notes",
}


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_hard_benchmark_dataset_exists() -> None:
    assert DATASET.exists()
    assert any(DATASET.glob("*.jsonl"))


def test_hard_benchmark_jsonl_schema() -> None:
    cases = _load_cases()
    assert len(cases) == 15
    for case in cases:
        assert REQUIRED_FIELDS.issubset(case)
        assert case["expected_behavior"] in ALLOWED_BEHAVIORS
        assert case["feature_tested"]
        window = case["expected_valid_window"]
        assert window.get("from")
        assert window.get("to")
        assert "data/sample/docs/aihistory1.txt" not in json.dumps(case)


def test_hard_benchmark_contains_expected_behavior_mix() -> None:
    behaviors = {case["expected_behavior"] for case in _load_cases()}
    assert {"success", "partial", "conflict_warning", "insufficient_evidence", "ambiguity"}.issubset(behaviors)
