from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.layer2_crossdomain import run_layer2_comparison as runner
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase
from benchmarks.layer2_crossdomain.vertex_retry import call_with_backoff, is_retryable_vertex_error


def _case() -> QuestionCase:
    return QuestionCase(
        id="case1",
        domain="macro_fred",
        question="What was the value on 2024-10-23?",
        category="exact_valid_time_retrieval",
        expected_behavior="answer",
        expected_evidence_ids=["e1"],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=["42"],
        forbidden_facts=[],
        expected_valid_time=["2024"],
        notes="fixture",
    )


def _corpus() -> list[CorpusRow]:
    return [
        CorpusRow(
            id="e1",
            domain="macro_fred",
            source_family="macro_fred",
            source_file="fixture",
            source_kind="time_series",
            entity="Value",
            related_entities=[],
            metric_or_claim="metric",
            value="42",
            unit="units",
            valid_from="2024-10-23",
            valid_to="2024-10-23",
            transaction_time=None,
            temporal_type="valid_time_exact",
            raw_text="Value was 42 units on 2024-10-23.",
        )
    ]


def test_429_like_exception_retries():
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("429 ResourceExhausted")
        return "ok"

    assert call_with_backoff(flaky, max_attempts=3, base_sleep=0, jitter=False, label="case=x method=y") == "ok"
    assert calls["count"] == 3


def test_503_like_exception_retries():
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("503 ServiceUnavailable")
        return "ok"

    assert call_with_backoff(flaky, max_attempts=2, base_sleep=0, jitter=False) == "ok"
    assert calls["count"] == 2


def test_non_retryable_exception_does_not_retry():
    calls = {"count": 0}

    def fails():
        calls["count"] += 1
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")

    with pytest.raises(RuntimeError):
        call_with_backoff(fails, max_attempts=5, base_sleep=0, jitter=False)
    assert calls["count"] == 1


def test_backoff_stops_at_max_attempts():
    calls = {"count": 0}

    def fails():
        calls["count"] += 1
        raise RuntimeError("stream removed")

    with pytest.raises(RuntimeError):
        call_with_backoff(fails, max_attempts=3, base_sleep=0, jitter=False)
    assert calls["count"] == 3


def test_retryable_classifier_handles_vertex_patterns():
    assert is_retryable_vertex_error(RuntimeError("TSI_DATA_CORRUPTED"))
    assert is_retryable_vertex_error(RuntimeError("Vertex response did not contain a JSON object"))
    assert is_retryable_vertex_error(runner.ProviderJSONError("json.loads failed"))
    assert not is_retryable_vertex_error(RuntimeError("Application Default Credentials missing"))


def test_resume_skips_completed_case_ids(tmp_path: Path):
    existing = {
        "results": [
            {
                "case_id": "case1",
                "status": "completed",
                "prompt_truncated": False,
                "selected_evidence_ids": ["e1"],
                "answer": {"behavior": "answer", "cited_evidence_ids": ["e1"]},
                "validation": {"overall_pass": True},
                "metadata": {},
            }
        ]
    }
    payload = runner.run_method(
        method="metadata_temporal_rag",
        corpus=_corpus(),
        questions=[_case()],
        mode="light",
        top_k=1,
        dry_run_prompts=False,
        max_output_tokens=16,
        suffix="pytest",
        write_partial=True,
        json_path=tmp_path / "resume.json",
        md_path=tmp_path / "resume.md",
        existing_payload=existing,
    )
    assert len(payload["results"]) == 1
    assert payload["results"][0]["case_id"] == "case1"


def test_provider_errors_recorded_separately_from_validation_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def fail_vertex(_prompt: str, _max_output_tokens: int):
        raise RuntimeError("429 ResourceExhausted")

    monkeypatch.setattr(runner, "_vertex_answer", fail_vertex)
    payload = runner.run_method(
        method="metadata_temporal_rag",
        corpus=_corpus(),
        questions=[_case()],
        mode="vertex",
        top_k=1,
        dry_run_prompts=False,
        max_output_tokens=16,
        suffix="pytest",
        request_sleep_seconds=0,
        retry_max_attempts=1,
        retry_base_sleep_seconds=0,
        retry_max_sleep_seconds=0,
        write_partial=True,
        json_path=tmp_path / "provider.json",
        md_path=tmp_path / "provider.md",
    )
    row = payload["results"][0]
    assert row["status"] == "provider_error"
    assert row["infrastructure_failure"] is True
    assert row["validation"]["infrastructure_failure"] is True
    assert payload["summary"]["infrastructure_failure_count"] == 1
    assert payload["summary"]["scored_case_count"] == 0
