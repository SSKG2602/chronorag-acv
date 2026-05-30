from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from benchmarks.layer2_crossdomain.evaluate_retrieval_only import evaluate_result_file, render_markdown
from benchmarks.layer2_crossdomain.schemas import QuestionCase

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "benchmarks/layer2_crossdomain/validate_layer2_dataset.py"


def _case(
    *,
    case_id: str = "case_1",
    category: str = "exact_valid_time_retrieval",
    question: str = "What was the value in 2020?",
    expected: list[str] | None = None,
    acceptable: list[str] | None = None,
    forbidden: list[str] | None = None,
) -> QuestionCase:
    return QuestionCase(
        id=case_id,
        domain="fixture",
        question=question,
        category=category,  # type: ignore[arg-type]
        expected_behavior="answer",
        expected_evidence_ids=expected or ["target"],
        acceptable_evidence_ids=acceptable or [],
        forbidden_evidence_ids=forbidden or [],
        required_facts=["2020"],
        forbidden_facts=[],
        expected_valid_time=["2020"],
        notes="fixture",
        synthetic_evidence_ids=[],
    )


def test_validation_cards_read_selected_evidence_ids_from_result_rows(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "method": "fixture_method",
                "results": [
                    {
                        "case_id": "case_1",
                        "selected_evidence_ids": ["target", "bad"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = evaluate_result_file(
        result_path,
        {"case_1": _case(expected=["target"], acceptable=["near"], forbidden=["bad"])},
    )

    case_report = report["case_reports"][0]
    assert case_report["selected_evidence_ids"] == ["target", "bad"]
    assert case_report["selected_expected_overlap"] == ["target"]
    assert case_report["selected_forbidden_overlap"] == ["bad"]

    markdown = render_markdown([report])
    assert "### Validation cards" in markdown
    assert "target, bad" in markdown
    assert "This prevents raw-result fields from being mistaken for scored fields." in markdown


def test_dataset_validator_catches_malformed_wrong_year_and_forbidden_overlap(tmp_path: Path) -> None:
    corpus_path = tmp_path / "corpus.jsonl"
    questions_path = tmp_path / "questions.jsonl"
    corpus_path.write_text(
        json.dumps(
            {
                "id": "target",
                "domain": "fixture",
                "source_family": "fixture",
                "source_file": "fixture.jsonl",
                "source_kind": "fixture",
                "entity": "GDP",
                "related_entities": [],
                "metric_or_claim": "value",
                "value": 1,
                "unit": "index",
                "valid_from": "1968-01-01",
                "valid_to": None,
                "transaction_time": None,
                "temporal_type": "valid_time_exact",
                "raw_text": "GDP value in 1968 was 1.",
                "metadata": {},
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    questions_path.write_text(
        json.dumps(
            {
                "id": "bad_wrong_year",
                "domain": "fixture",
                "question": "For GDP in 1968, answer for 1968, not 1968.",
                "category": "same_entity_wrong_year_trap",
                "expected_behavior": "answer",
                "expected_evidence_ids": ["target"],
                "acceptable_evidence_ids": [],
                "forbidden_evidence_ids": ["target"],
                "required_facts": ["1968"],
                "forbidden_facts": [],
                "expected_valid_time": ["1968"],
                "notes": "fixture",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--corpus",
            str(corpus_path),
            "--questions",
            str(questions_path),
            "--expected-corpus-rows",
            "1",
            "--expected-questions",
            "1",
            "--methods",
            "metadata_temporal_rag",
            "chronorag_full",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "malformed wrong-time wording" in completed.stdout
    assert "both allowed and forbidden" in completed.stdout


def test_dataset_validator_allows_same_year_when_full_dates_differ(tmp_path: Path) -> None:
    corpus_path = tmp_path / "corpus.jsonl"
    questions_path = tmp_path / "questions.jsonl"
    row = {
        "id": "target",
        "domain": "fixture",
        "source_family": "fixture",
        "source_file": "fixture.jsonl",
        "source_kind": "fixture",
        "entity": "GDP",
        "related_entities": [],
        "metric_or_claim": "value",
        "value": 1,
        "unit": "index",
        "valid_from": "1968-12-30",
        "valid_to": "1968-12-30",
        "transaction_time": None,
        "temporal_type": "valid_time_exact",
        "raw_text": "GDP value on 1968-12-30 was 1.",
        "metadata": {},
        "tags": [],
    }
    corpus_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    questions_path.write_text(
        json.dumps(
            {
                "id": "date_trap",
                "domain": "fixture",
                "question": "For GDP, answer value for 1968-12-30, not 1968-12-05.",
                "category": "same_entity_wrong_year_trap",
                "expected_behavior": "answer",
                "expected_evidence_ids": ["target"],
                "acceptable_evidence_ids": [],
                "forbidden_evidence_ids": [],
                "required_facts": ["1968-12-30"],
                "forbidden_facts": ["1968-12-05"],
                "expected_valid_time": ["1968-12-30"],
                "notes": "fixture",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--corpus",
            str(corpus_path),
            "--questions",
            str(questions_path),
            "--expected-corpus-rows",
            "1",
            "--expected-questions",
            "1",
            "--methods",
            "metadata_temporal_rag",
            "chronorag_full",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "malformed wrong-time wording" not in completed.stdout
    assert "Corpus domain distribution collapsed" in completed.stdout
