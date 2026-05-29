from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.layer2_crossdomain import run_layer2_comparison as runner
from benchmarks.layer2_crossdomain.prompts import build_grounded_prompt
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


def _row(row_id: str = "e1", valid_from: str = "1990-01-01", value: str = "8.0") -> CorpusRow:
    return CorpusRow(
        id=row_id,
        domain="macro_fred",
        source_family="macro_fred",
        source_file="fixture",
        source_kind="time_series",
        entity="United States 10-year Treasury",
        related_entities=["DGS10"],
        metric_or_claim="10-year Treasury yield",
        value=value,
        unit="percent",
        valid_from=valid_from,
        valid_to=valid_from,
        transaction_time=None,
        temporal_type="valid_time_exact",
        raw_text=f"United States 10-year Treasury yield was {value} percent on {valid_from}.",
    )


def _case() -> QuestionCase:
    return QuestionCase(
        id="l2q:0023:same_entity_wrong_year_trap",
        domain="macro_fred",
        question="What was United States 10-year Treasury yield on 1990-01-01? Do not use the wrong-year record.",
        category="same_entity_wrong_year_trap",
        expected_behavior="answer",
        expected_evidence_ids=["e1"],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=["e2"],
        required_facts=["8.0"],
        forbidden_facts=["7.0"],
        expected_valid_time=["1990"],
        notes="same-entity wrong-year formatting test",
    )


def test_prompt_contains_json_only_contract():
    prompt = build_grounded_prompt(_case(), [_row()], "chronorag_full")
    assert "Return ONLY one valid JSON object" in prompt
    assert "Do not wrap the JSON in markdown or code fences" in prompt
    assert "Do not include prose before JSON" in prompt
    assert "Do not include prose after JSON" in prompt


def test_prompt_instructs_json_for_same_entity_multi_evidence_case():
    prompt = build_grounded_prompt(_case(), [_row("e1", "1990-01-01", "8.0"), _row("e2", "1989-01-01", "7.0")], "chronorag_full")
    assert "same-entity wrong-year" in prompt
    assert "still return JSON" in prompt
    assert '"behavior": "answer|partial|refuse|clarify"' in prompt
    assert "Do not refuse merely because multiple same-year rows exist." in prompt


def test_json_extraction_handles_fenced_json():
    text = '```json\n{"answer": "ok", "behavior": "answer"}\n```'
    assert runner._extract_json_object(text) == '{"answer": "ok", "behavior": "answer"}'


def test_json_extraction_handles_text_before_and_after_json():
    text = 'Here is the object: {"answer": "ok", "behavior": "answer"} trailing prose'
    assert runner._extract_json_object(text) == '{"answer": "ok", "behavior": "answer"}'


def test_json_parse_failure_retry_cap_is_lower_than_provider_retry_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls = {"count": 0}

    def plain_english(_prompt: str, _max_output_tokens: int):
        calls["count"] += 1
        raise runner.ProviderJSONError("Vertex response did not contain a JSON object; raw_response_preview=Multiple yields are available.")

    monkeypatch.setattr(runner, "_vertex_answer", plain_english)
    payload = runner.run_method(
        method="chronorag_full",
        corpus=[_row()],
        questions=[_case()],
        mode="vertex",
        top_k=1,
        dry_run_prompts=False,
        max_output_tokens=64,
        suffix="pytest_json",
        request_sleep_seconds=0,
        retry_max_attempts=6,
        retry_base_sleep_seconds=0,
        retry_max_sleep_seconds=0,
        json_retry_max_attempts=2,
        write_partial=True,
        json_path=tmp_path / "json.json",
        md_path=tmp_path / "json.md",
    )
    assert calls["count"] == 2
    assert payload["results"][0]["failure_type"] == "JSON Parse Failure"
    assert payload["results"][0]["metadata"]["json_parse_failures"] == 2
    assert payload["summary"]["json_parse_failure_count"] == 1


def test_plain_english_response_does_not_crash_whole_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def plain_english(_prompt: str, _max_output_tokens: int):
        raise runner.ProviderJSONError("Vertex response did not contain a JSON object; raw_response_preview=Multiple yields are available.")

    monkeypatch.setattr(runner, "_vertex_answer", plain_english)
    payload = runner.run_method(
        method="metadata_temporal_rag",
        corpus=[_row()],
        questions=[_case()],
        mode="vertex",
        top_k=1,
        dry_run_prompts=False,
        max_output_tokens=64,
        suffix="pytest_json",
        request_sleep_seconds=0,
        retry_max_attempts=5,
        retry_base_sleep_seconds=0,
        retry_max_sleep_seconds=0,
        json_retry_max_attempts=1,
        write_partial=True,
        json_path=tmp_path / "plain.json",
        md_path=tmp_path / "plain.md",
    )
    row = payload["results"][0]
    assert row["status"] == "provider_error"
    assert row["infrastructure_failure"] is True
    assert row["validation"]["infrastructure_failure"] is True
    assert payload["summary"]["scored_case_count"] == 0
