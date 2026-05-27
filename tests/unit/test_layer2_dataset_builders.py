from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from benchmarks.layer2_crossdomain.schemas import load_corpus, load_questions

ROOT = Path(__file__).resolve().parents[2]
CORPUS_BUILDER = ROOT / "benchmarks/layer2_crossdomain/build_layer2_corpus.py"
QUESTION_BUILDER = ROOT / "benchmarks/layer2_crossdomain/build_layer2_questions.py"
VALIDATOR = ROOT / "benchmarks/layer2_crossdomain/validate_layer2_dataset.py"


def test_corpus_builder_writes_valid_schema_rows(tmp_path):
    out = tmp_path / "corpus.jsonl"
    subprocess.run(
        [sys.executable, str(CORPUS_BUILDER), "--target-rows", "50", "--out", str(out)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    rows = load_corpus(out)
    assert len(rows) == 50
    assert len({row.id for row in rows}) == 50
    assert {row.domain for row in rows}


def test_question_builder_writes_valid_schema_cases(tmp_path):
    corpus_out = tmp_path / "corpus.jsonl"
    questions_out = tmp_path / "questions.jsonl"
    subprocess.run(
        [sys.executable, str(CORPUS_BUILDER), "--target-rows", "120", "--out", str(corpus_out)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, str(QUESTION_BUILDER), "--corpus", str(corpus_out), "--target-questions", "20", "--out", str(questions_out)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    questions = load_questions(questions_out)
    assert len(questions) == 20
    assert len({case.id for case in questions}) == 20
    assert {case.category for case in questions} >= {"exact_valid_time_retrieval", "transaction_time_vs_valid_time"}


def test_integrity_validator_catches_missing_evidence_ids(tmp_path):
    corpus_out = tmp_path / "corpus.jsonl"
    questions_out = tmp_path / "questions.jsonl"
    subprocess.run(
        [sys.executable, str(CORPUS_BUILDER), "--target-rows", "50", "--out", str(corpus_out)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    bad_question = {
        "id": "bad",
        "domain": "macro_fred",
        "question": "What was CPI in 2020?",
        "category": "exact_valid_time_retrieval",
        "expected_behavior": "answer",
        "expected_evidence_ids": ["missing:evidence"],
        "acceptable_evidence_ids": [],
        "forbidden_evidence_ids": [],
        "required_facts": ["2020"],
        "forbidden_facts": [],
        "expected_valid_time": ["2020"],
        "notes": "bad fixture",
    }
    questions_out.write_text(json.dumps(bad_question) + "\n", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--corpus",
            str(corpus_out),
            "--questions",
            str(questions_out),
            "--expected-corpus-rows",
            "50",
            "--expected-questions",
            "1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 1
    assert "missing evidence ID" in completed.stdout


def test_direct_prompt_has_no_answer_key_metadata(tmp_path):
    corpus_out = tmp_path / "corpus.jsonl"
    questions_out = tmp_path / "questions.jsonl"
    subprocess.run(
        [sys.executable, str(CORPUS_BUILDER), "--target-rows", "120", "--out", str(corpus_out)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, str(QUESTION_BUILDER), "--corpus", str(corpus_out), "--target-questions", "20", "--out", str(questions_out)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    from benchmarks.layer2_crossdomain.methods.direct_llm_full_context.runner import build_prompt

    corpus = load_corpus(corpus_out)
    case = load_questions(questions_out)[0]
    prompt = build_prompt(case, corpus, top_k=5)["prompt"]
    assert "expected_evidence_ids" not in prompt
    assert "required_facts" not in prompt


def test_baseline_and_chronorag_import_boundaries():
    baseline_retrieval = (ROOT / "benchmarks/layer2_crossdomain/methods/metadata_temporal_rag/retrieval.py").read_text()
    chrono_runner = (ROOT / "benchmarks/layer2_crossdomain/methods/chronorag_full/runner.py").read_text()
    chrono_adapter = (ROOT / "benchmarks/layer2_crossdomain/methods/chronorag_full/adapter.py").read_text()
    assert "temporal_contextual_chunker" not in baseline_retrieval
    assert "monotone_temporal_fusion" not in baseline_retrieval
    assert "metadata_temporal_rag" not in chrono_runner
    assert "build_temporal_contextual_chunks" in chrono_adapter
