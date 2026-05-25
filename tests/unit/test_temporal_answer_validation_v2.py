from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from benchmarks.answer_validation_v2 import (
    build_chronorag_grounded_synthesis_prompt,
    build_tcc_evidence_cards,
    load_cases,
    load_corpus,
    retrieve_top_k,
    validate_answer,
)


CASES = Path("benchmarks/temporal_answer_validation_v2_15.jsonl")
RUNNER = Path("benchmarks/run_temporal_answer_validation_v2.py")
REQUIRED_FIELDS = {
    "id",
    "category",
    "question",
    "expected_behavior",
    "feature_under_test",
    "expected_evidence_ids",
    "acceptable_evidence_ids",
    "distractor_evidence_ids",
    "must_include",
    "must_not_include",
    "readable_expected_answer",
    "validation_notes",
}


def test_answer_validation_case_file_schema_and_ids() -> None:
    assert CASES.exists()
    corpus_ids = {row["id"] for row in load_corpus()}
    cases = load_cases()
    assert len(cases) == 15
    for case in cases:
        assert REQUIRED_FIELDS.issubset(case)
        for field in ["expected_evidence_ids", "acceptable_evidence_ids", "distractor_evidence_ids"]:
            for evidence_id in case[field]:
                assert evidence_id in corpus_ids


def test_tcc_evidence_cards_and_prompt_rules() -> None:
    case = load_cases()[0]
    rows = retrieve_top_k(case["question"], load_corpus(), top_k=5)
    cards = build_tcc_evidence_cards(rows)
    assert cards
    card = cards[0]
    assert "valid_from" in card
    assert "valid_to" in card
    assert "transaction_time" in card
    assert "valid_time=" in card["tcc_context"]
    assert "transaction_time=" in card["tcc_context"]
    assert "raw_evidence=" in card["tcc_context"]
    assert "retrieval_context=" in card["tcc_context"]

    prompt = build_chronorag_grounded_synthesis_prompt(case, cards)
    assert "You are ChronoRAG's grounded temporal answer synthesizer." in prompt
    assert "Use only the TCC-enriched evidence cards." in prompt
    assert "Do not treat transaction_time as valid_time." in prompt
    assert "Always cite evidence IDs." in prompt


def test_light_runner_writes_results(tmp_path: Path) -> None:
    out_json = tmp_path / "light.json"
    out_md = tmp_path / "light.md"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "light",
            "--top-k",
            "5",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        check=True,
    )
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["mode"] == "light"
    assert payload["case_count"] == 15
    assert len(payload["details"]) == 15
    assert "Temporal Answer Validation v2 Results" in out_md.read_text(encoding="utf-8")


def test_dry_run_and_estimate_only(tmp_path: Path) -> None:
    out_json = tmp_path / "dry.json"
    out_md = tmp_path / "dry.md"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "light",
            "--dry-run-prompts",
            "--limit",
            "2",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        check=True,
    )
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["prompt_count"] == 2
    assert "TCC-enriched evidence cards" in out_md.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "light", "--estimate-only"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Selected cases: 15" in result.stdout
    assert "Estimated Vertex calls: 0" in result.stdout


def test_vertex_mode_without_env_fails_clearly() -> None:
    env = dict(os.environ)
    env.pop("GOOGLE_CLOUD_PROJECT", None)
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "vertex", "--limit", "1"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "Vertex mode requested" in result.stderr or "Vertex mode requested" in result.stdout


def test_validator_detects_answer_failures() -> None:
    case = next(item for item in load_cases() if item["id"] == "av2_q03_transaction_time_avoidance")
    cards = build_tcc_evidence_cards(retrieve_top_k(case["question"], load_corpus(), top_k=5))
    bad = {
        "answer": "2006 is the valid time. GDP valid year 2006.",
        "behavior": "answer",
        "cited_evidence_ids": [],
        "valid_time_used": ["2006"],
        "transaction_time_used_as_valid_time": True,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
    }
    result = validate_answer(case, bad, cards)
    assert not result["transaction_time_not_misused"]
    assert not result["forbidden_facts_absent"]
    assert not result["expected_evidence_cited"]

    conflict_case = next(item for item in load_cases() if item["expected_behavior"] == "conflict_warning")
    conflict_result = validate_answer(
        conflict_case,
        {
            "answer": "Western Europe 1913 answer without conflict.",
            "behavior": "answer",
            "cited_evidence_ids": conflict_case["expected_evidence_ids"],
            "valid_time_used": ["1913-01-01 to 1913-12-31"],
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": False,
            "clarification_requested": False,
        },
        cards,
    )
    assert not conflict_result["conflict_warning_correct"]

    partial_case = next(item for item in load_cases() if item["expected_behavior"] == "partial")
    partial_result = validate_answer(
        partial_case,
        {
            "answer": "confident exact China answer",
            "behavior": "answer",
            "cited_evidence_ids": partial_case["acceptable_evidence_ids"],
            "valid_time_used": [],
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": False,
            "clarification_requested": False,
        },
        cards,
    )
    assert not partial_result["partial_refusal_correct"]
