from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


BUILDER = Path("benchmarks/build_temporal_eval_v2.py")
RUNNER = Path("benchmarks/run_temporal_eval_v2.py")
CORPUS = Path("data/sample/temporal_eval_v2/temporal_eval_v2_corpus.jsonl")
CASES = Path("benchmarks/temporal_eval_v2_15.jsonl")
RESULT_JSON = Path("benchmarks/results/temporal_eval_v2_results.json")
RESULT_MD = Path("benchmarks/results/temporal_eval_v2_results.md")

REQUIRED_FAMILIES = {
    "maddison_project_2023",
    "owid_maddison_gdppc",
    "owid_maddison_gdp",
    "owid_global_gdp_long_run",
    "oecd_world_economy_pdf",
    "synthetic_temporal_traps",
}
REQUIRED_ROW_FIELDS = {
    "id",
    "source_family",
    "source_file",
    "source_kind",
    "source_uri",
    "source_page",
    "source_table",
    "entity",
    "region",
    "metric",
    "value",
    "unit",
    "valid_from",
    "valid_to",
    "transaction_time",
    "temporal_granularity",
    "temporal_type",
    "raw_text",
    "retrieval_text",
    "expected_use",
}
VALID_TEMPORAL_TYPES = {
    "valid_time_exact",
    "valid_time_range",
    "transaction_time_only",
    "ambiguous_time",
    "conflict_claim",
}
VALID_BEHAVIORS = {"answer", "compare", "prefer_exact", "partial", "refuse", "conflict_warning", "clarify"}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_temporal_eval_v2_scripts_exist() -> None:
    assert BUILDER.exists()
    assert RUNNER.exists()


def test_temporal_eval_v2_builder_outputs_schema() -> None:
    subprocess.run([sys.executable, str(BUILDER)], check=True)
    assert CORPUS.exists()
    rows = load_jsonl(CORPUS)
    assert 150 <= len(rows) <= 200
    families = {row["source_family"] for row in rows}
    assert len(families) >= 5
    assert REQUIRED_FAMILIES.issubset(families)
    for row in rows:
        assert REQUIRED_ROW_FIELDS.issubset(row)
        assert row["temporal_type"] in VALID_TEMPORAL_TYPES
        if row["source_kind"] == "pdf_derived_passage":
            assert len(row["raw_text"]) <= 260


def test_temporal_eval_v2_cases_reference_existing_evidence() -> None:
    if not CORPUS.exists():
        subprocess.run([sys.executable, str(BUILDER)], check=True)
    rows = load_jsonl(CORPUS)
    ids = {row["id"] for row in rows}
    cases = load_jsonl(CASES)
    assert len(cases) == 15
    categories = {case["category"][0] for case in cases}
    assert categories == {"A", "B", "C", "D", "E", "F"}
    for case in cases:
        assert case["expected_behavior"] in VALID_BEHAVIORS
        assert case["question"]
        for field in ["expected_evidence_ids", "acceptable_evidence_ids", "distractor_evidence_ids"]:
            for evidence_id in case[field]:
                assert evidence_id in ids, f"{evidence_id} missing for {case['id']}"


def test_temporal_eval_v2_runner_generates_light_results() -> None:
    subprocess.run([sys.executable, str(BUILDER)], check=True)
    subprocess.run([sys.executable, str(RUNNER), "--light"], check=True)
    assert RESULT_JSON.exists()
    assert RESULT_MD.exists()
    payload = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    assert payload["corpus"]["row_count"] >= 150
    assert payload["benchmark"]["case_count"] == 15
    assert payload["summary"]
