from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from benchmarks.layer2_crossdomain.methods.metadata_temporal_rag.retrieval import retrieve
from benchmarks.layer2_crossdomain.prompts import build_direct_full_context_prompt
from benchmarks.layer2_crossdomain.schemas import load_corpus, load_questions
from benchmarks.layer2_crossdomain.validator import validate_answer

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_corpus.sample.jsonl"
QUESTIONS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_questions.sample.jsonl"
RUNNER = ROOT / "benchmarks/layer2_crossdomain/run_layer2_comparison.py"


def test_layer2_schemas_load_valid_samples():
    corpus = load_corpus(CORPUS)
    questions = load_questions(QUESTIONS)
    assert len(corpus) >= 8
    assert len(questions) >= 4
    assert {row.domain for row in corpus} >= {"finance", "software", "product"}


def test_direct_full_context_prompt_excludes_answer_keys():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[0]
    prompt, _truncated, _metadata = build_direct_full_context_prompt(case, corpus)
    forbidden = ['"expected_evidence_ids"', '"acceptable_evidence_ids"', '"required_facts"', '"forbidden_facts"', '"notes"']
    assert not any(token in prompt for token in forbidden)
    assert "l2_fin_msft_2020_revenue" in prompt
    assert "Microsoft reported revenue" in prompt


def test_metadata_retrieval_prefers_exact_valid_time_over_broad_window():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[0]
    rows = retrieve(case, corpus, top_k=3)
    assert rows[0].id == "l2_fin_msft_2020_revenue"
    assert "l2_fin_msft_broad_2019_2022" not in [row.id for row in rows[:1]]


def test_transaction_time_only_not_valid_time_for_valid_question():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[2]
    rows = retrieve(case, corpus, top_k=2)
    assert rows[0].id == "l2_software_api_v2_removed_2022"
    assert rows[0].temporal_type != "transaction_time_only"


def test_transaction_time_only_allowed_when_question_asks_transaction_records():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[2]
    transaction_case = type(case)(
        id="tx_records",
        domain=case.domain,
        question="Which records are transaction-time-only publication records for Acme API?",
        category="transaction_vs_valid_time",
        expected_behavior="answer",
        expected_evidence_ids=["l2_software_api_pub_2024"],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=["2024"],
        forbidden_facts=[],
        expected_valid_time=[],
        notes="Test transaction-time-only retrieval.",
    )
    rows = retrieve(transaction_case, corpus, top_k=2)
    assert rows[0].id == "l2_software_api_pub_2024"


def test_validator_catches_missing_required_facts():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[0]
    result = validate_answer(
        case,
        {
            "answer": "Microsoft revenue was reported.",
            "behavior": "answer",
            "cited_evidence_ids": ["l2_fin_msft_2020_revenue"],
            "valid_time_used": ["2020"],
            "transaction_time_used_as_valid_time": False,
            "confidence": "high",
        },
        corpus,
    )
    assert not result.required_facts_present
    assert not result.overall_pass


def test_validator_catches_forbidden_evidence():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[0]
    result = validate_answer(
        case,
        {
            "answer": "Microsoft revenue was 143.0 billion USD in 2020.",
            "behavior": "answer",
            "cited_evidence_ids": ["l2_fin_msft_2021_revenue"],
            "valid_time_used": ["2020"],
            "transaction_time_used_as_valid_time": False,
            "confidence": "high",
        },
        corpus,
    )
    assert not result.forbidden_evidence_absent
    assert not result.overall_pass


def test_validator_catches_transaction_time_misuse():
    corpus = load_corpus(CORPUS)
    case = load_questions(QUESTIONS)[2]
    result = validate_answer(
        case,
        {
            "answer": "LegacyToken was removed in 2024.",
            "behavior": "answer",
            "cited_evidence_ids": ["l2_software_api_pub_2024"],
            "valid_time_used": ["2024"],
            "transaction_time_used_as_valid_time": True,
            "confidence": "high",
        },
        corpus,
    )
    assert not result.transaction_time_not_misused
    assert not result.overall_pass


def test_runner_estimate_only():
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--method",
            "direct_llm_full_context",
            "--mode",
            "vertex",
            "--limit",
            "1",
            "--estimate-only",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Estimated Vertex calls: 1" in completed.stdout


def test_runner_dry_run_prompts_without_vertex(tmp_path):
    suffix = "pytest_dryrun"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--method",
            "metadata_temporal_rag",
            "--mode",
            "vertex",
            "--limit",
            "1",
            "--dry-run-prompts",
            "--result-suffix",
            suffix,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Wrote:" in completed.stdout
    result = ROOT / f"benchmarks/layer2_crossdomain/results/layer2_metadata_temporal_rag_{suffix}_results.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["results"][0]["prompt_preview"]
    result.unlink()
    result.with_suffix(".md").unlink()


def test_chronorag_full_reports_existing_framework_adapter():
    suffix = "pytest_chrono_est"
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--method",
            "chronorag_full",
            "--mode",
            "light",
            "--limit",
            "1",
            "--result-suffix",
            suffix,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Wrote:" in completed.stdout
    result = ROOT / f"benchmarks/layer2_crossdomain/results/layer2_chronorag_full_{suffix}_results.json"
    payload = json.loads(result.read_text(encoding="utf-8"))
    metadata = payload["results"][0]["metadata"]
    assert metadata["method_family"] == "chronorag_full"
    assert metadata["uses_existing_chronorag_framework"] is True
    assert metadata["adapter_used"] is True
    result.unlink()
    result.with_suffix(".md").unlink()
