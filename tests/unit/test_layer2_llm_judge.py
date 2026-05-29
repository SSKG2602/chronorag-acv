from __future__ import annotations

import json

from benchmarks.layer2_crossdomain import llm_judge
from benchmarks.layer2_crossdomain import run_layer2_comparison as runner
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


def _case(expected_behavior: str = "answer") -> dict:
    return {
        "id": "case1",
        "question": "What was United States 10-year Treasury yield on 1962-08-15?",
        "expected_behavior": expected_behavior,
        "required_facts": ["do-not-leak"],
        "expected_evidence_ids": ["do-not-leak"],
    }


def _answer(cited: list[str] | None = None) -> dict:
    return {
        "answer": "United States 10-year Treasury yield was 3.98 percent on 1962-08-15.",
        "behavior": "answer",
        "cited_evidence_ids": cited if cited is not None else ["e1"],
        "valid_time_used": ["1962-08-15"],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }


def _cards() -> list[dict]:
    return [
        {
            "evidence_id": "e1",
            "domain": "macro_fred",
            "source": "macro_fred",
            "entity": "United States 10-year Treasury",
            "metric": "10-year Treasury yield",
            "metric_or_claim": "10-year Treasury yield",
            "value": "3.98",
            "unit": "percent",
            "valid_from": "1962-08-15",
            "valid_to": "1962-08-15",
            "transaction_time": None,
            "temporal_type": "valid_time_exact",
            "raw_text": "United States 10-year Treasury yield was 3.98 percent on 1962-08-15.",
        }
    ]


def _judge_json(passed: int = 5) -> str:
    scores = [1 if index < passed else 0 for index, _criterion in enumerate(llm_judge.CRITERIA)]
    return json.dumps(
        {
            "scores": scores,
            "reason": "grounded and temporally correct",
        }
    )


def _verbose_judge_json(passed: int = 5) -> str:
    scores = {criterion: 1 for criterion in llm_judge.CRITERIA}
    for criterion in llm_judge.CRITERIA[passed:]:
        scores[criterion] = 0
    return json.dumps(
        {
            **scores,
            "reasons": {criterion: f"{criterion} reason" for criterion in llm_judge.CRITERIA},
        }
    )


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def synthesize_grounded_answer(self, _prompt: str, *, temperature: float, max_output_tokens: int):
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_judge_prompt_contains_evidence_cards():
    prompt = llm_judge.build_judge_prompt(_case(), _answer(), _cards())
    assert "Evidence cards:" in prompt
    assert "e1" in prompt
    assert "3.98" in prompt
    assert "Return only compact JSON" in prompt
    assert '"scores": [' in prompt
    assert "step-by-step" in prompt


def test_judge_prompt_does_not_contain_forbidden_answer_key_fields():
    prompt = llm_judge.build_judge_prompt(_case(), _answer(), _cards())
    for forbidden in (
        "expected_evidence_ids",
        "acceptable_evidence_ids",
        "forbidden_evidence_ids",
        "required_facts",
        "forbidden_facts",
        "expected_valid_time",
        "expected_behavior",
    ):
        assert forbidden not in prompt
    assert "Expected behavior type:" in prompt


def test_majority_vote_works(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([_judge_json(5), _judge_json(5), _judge_json(0)])
    result = llm_judge.run_judge(_case(), _answer(), _cards(), provider, runs=3, request_sleep_seconds=0)
    assert result["criteria_passed"] == 5
    assert result["judge_overall_pass"] is True
    assert result["judge_scored_runs"] == 3
    assert result["judge_unscored_runs"] == 0


def test_old_verbose_criterion_format_still_parses(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([_verbose_judge_json(5)])
    result = llm_judge.validate_case_v3(_case(), _answer(), _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["criteria_passed"] == 5
    assert result["judge_overall_pass"] is True


def test_fenced_judge_json_parses(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([f"```json\n{_judge_json(5)}\n```"])
    result = llm_judge.validate_case_v3(_case(), _answer(), _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["judge_overall_pass"] is True


def test_judge_json_with_text_before_after_parses(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([f"Here is JSON: {_judge_json(5)} done"])
    result = llm_judge.validate_case_v3(_case(), _answer(), _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["judge_overall_pass"] is True


def test_four_of_five_criteria_passes_judge_overall(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([_judge_json(4)])
    result = llm_judge.validate_case_v3(_case(), _answer(), _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["criteria_passed"] == 4
    assert result["judge_overall_pass"] is True


def test_three_of_five_criteria_fails_judge_overall(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([_judge_json(3)])
    result = llm_judge.validate_case_v3(_case(), _answer(), _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["criteria_passed"] == 3
    assert result["judge_overall_pass"] is False


def test_one_parse_failure_does_not_kill_judge_result(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider(["plain English", _judge_json(5), _judge_json(5)])
    result = llm_judge.validate_case_v3(
        _case(),
        _answer(),
        _cards(),
        provider,
        runs=3,
        request_sleep_seconds=0,
        json_retry_max_attempts=1,
    )
    assert result["judge_parse_failures"] == 1
    assert result["judge_scored_runs"] == 2
    assert result["judge_unscored_runs"] == 1
    assert result["judge_overall_pass"] is True


def test_all_parse_failures_are_infrastructure_not_semantic(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider(["plain English", '{"scores": [1, 1'])
    result = llm_judge.validate_case_v3(
        _case(),
        _answer(),
        _cards(),
        provider,
        runs=2,
        request_sleep_seconds=0,
        json_retry_max_attempts=1,
    )
    assert result["judge_parse_failures"] == 2
    assert result["judge_infrastructure_failure"] is True
    assert result["judge_scored_runs"] == 0
    assert result["judge_unscored_runs"] == 2
    assert set(result["criteria_reasons"].values()) == {"unscored_due_to_judge_failure"}
    assert result["judge_overall_pass"] is False


def test_provider_failure_for_one_run_does_not_kill_case(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(llm_judge.random, "uniform", lambda _a, _b: 1.0)
    provider = FakeProvider([RuntimeError("429 ResourceExhausted"), _judge_json(5), _judge_json(5)])
    result = llm_judge.validate_case_v3(
        _case(),
        _answer(),
        _cards(),
        provider,
        runs=3,
        request_sleep_seconds=0,
        retry_max_attempts=1,
    )
    assert result["judge_provider_failures"] == 1
    assert result["judge_scored_runs"] == 2
    assert result["judge_unscored_runs"] == 1
    assert result["judge_overall_pass"] is True


def test_strict_overall_requires_grounded_citations_and_schema_fields(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([_judge_json(5)])
    result = llm_judge.validate_case_v3(_case(), _answer(cited=["missing"]), _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["judge_overall_pass"] is True
    assert result["diagnostics"]["cited_ids_grounded"] is False
    assert result["strict_overall_pass"] is False


def test_diagnostics_do_not_alter_judge_overall(monkeypatch):
    monkeypatch.setattr(llm_judge.time, "sleep", lambda _seconds: None)
    provider = FakeProvider([_judge_json(5)])
    answer = _answer()
    answer.pop("confidence")
    result = llm_judge.validate_case_v3(_case(expected_behavior="refuse"), answer, _cards(), provider, runs=1, request_sleep_seconds=0)
    assert result["judge_overall_pass"] is True
    assert result["diagnostics"]["behavior_label_match"] is False
    assert result["diagnostics"]["schema_fields_present"] is False
    assert result["strict_overall_pass"] is False


def test_cli_default_judge_max_output_tokens_is_1000():
    args = runner.build_arg_parser().parse_args([])
    assert args.judge_max_output_tokens == 1000


def test_deterministic_validator_path_remains_available(tmp_path):
    case = QuestionCase(
        id="case1",
        domain="macro_fred",
        question="What was the value on 1962-08-15?",
        category="exact_valid_time_retrieval",
        expected_behavior="answer",
        expected_evidence_ids=["e1"],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=["3.98"],
        forbidden_facts=[],
        expected_valid_time=["1962"],
        notes="fixture",
    )
    row = CorpusRow(
        id="e1",
        domain="macro_fred",
        source_family="macro_fred",
        source_file="fixture",
        source_kind="time_series",
        entity="United States 10-year Treasury",
        related_entities=[],
        metric_or_claim="10-year Treasury yield",
        value="3.98",
        unit="percent",
        valid_from="1962-08-15",
        valid_to="1962-08-15",
        transaction_time=None,
        temporal_type="valid_time_exact",
        raw_text="United States 10-year Treasury yield was 3.98 percent on 1962-08-15.",
    )
    payload = runner.run_method(
        method="metadata_temporal_rag",
        corpus=[row],
        questions=[case],
        mode="light",
        top_k=1,
        dry_run_prompts=False,
        max_output_tokens=16,
        suffix="pytest",
        validator="deterministic",
        write_partial=True,
        json_path=tmp_path / "result.json",
        md_path=tmp_path / "result.md",
    )
    assert payload["validator"] == "deterministic"
    assert "judge_overall_pass" not in payload["results"][0]["validation"]
