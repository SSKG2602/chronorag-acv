from __future__ import annotations

import json
import random
import time
from collections.abc import Mapping, Sequence
from math import ceil
from typing import Any

from benchmarks.layer2_crossdomain.vertex_retry import is_retryable_vertex_error


CRITERIA = [
    "temporal_scope_correct",
    "factual_grounding",
    "behavior_justified",
    "transaction_time_clean",
    "no_overconfidence",
]

JUDGE_SYSTEM_PROMPT = """
You are an impartial temporal reasoning judge evaluating a RAG system's answer.

Your job is to determine if the answer is temporally correct and factually grounded against the provided evidence cards only.

ABSOLUTE RULES:
- Judge against evidence cards only. No outside knowledge.
- Do NOT penalize different phrasing of the same correct fact.
- Do NOT reward confident answers that contradict evidence cards.
- A correct refusal when evidence is missing is a PASS.
- A confident specific value when evidence is missing is a FAIL.
- Answer phrasing may vary freely. Truth against cards may not.
"""

JUDGE_OUTPUT_SCHEMA = {
    "temporal_scope_correct": 1,
    "factual_grounding": 1,
    "behavior_justified": 1,
    "transaction_time_clean": 1,
    "no_overconfidence": 1,
    "reasons": {
        "temporal_scope_correct": "one sentence",
        "factual_grounding": "one sentence",
        "behavior_justified": "one sentence",
        "transaction_time_clean": "one sentence",
        "no_overconfidence": "one sentence",
    },
}

REQUIRED_SCHEMA_FIELDS = {"answer", "behavior", "cited_evidence_ids", "valid_time_used", "confidence"}


def evidence_cards_from_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in rows:
        cards.append(
            {
                "evidence_id": _get(row, "id"),
                "domain": _get(row, "domain"),
                "source": _get(row, "source_family"),
                "entity": _get(row, "entity"),
                "metric": _get(row, "metric_or_claim"),
                "metric_or_claim": _get(row, "metric_or_claim"),
                "value": _get(row, "value"),
                "unit": _get(row, "unit"),
                "valid_from": _get(row, "valid_from"),
                "valid_to": _get(row, "valid_to"),
                "transaction_time": _get(row, "transaction_time"),
                "temporal_type": _get(row, "temporal_type"),
                "raw_text": _get(row, "raw_text"),
            }
        )
    return cards


def build_judge_prompt(
    case: Mapping[str, Any] | Any,
    answer: Mapping[str, Any],
    evidence_cards: Sequence[Mapping[str, Any]],
) -> str:
    question = _get(case, "question")
    behavior = _get(case, "expected_behavior")
    safe_answer = {key: answer.get(key) for key in sorted(REQUIRED_SCHEMA_FIELDS | {"transaction_time_used_as_valid_time", "conflict_warning", "partial_or_refusal", "clarification_requested"})}
    return f"""{JUDGE_SYSTEM_PROMPT.strip()}

Question:
{question}

Expected behavior type:
{behavior}

Evidence cards:
{json.dumps(list(evidence_cards), ensure_ascii=False, sort_keys=True, indent=2)}

System answer fields:
{json.dumps(safe_answer, ensure_ascii=False, sort_keys=True, indent=2)}

Scoring criteria:
{json.dumps(CRITERIA, sort_keys=True)}

Return ONLY one valid JSON object.
Do not include markdown, code fences, prose, or explanation outside JSON.
Use this exact output schema:
{json.dumps(JUDGE_OUTPUT_SCHEMA, sort_keys=True, indent=2)}
"""


def run_judge(
    case,
    answer,
    evidence_cards,
    provider,
    runs: int = 3,
    temperature: float = 0.3,
    max_output_tokens: int = 600,
    request_sleep_seconds: float = 6,
    retry_max_attempts: int = 4,
    retry_base_sleep_seconds: float = 8,
    retry_max_sleep_seconds: float = 90,
    json_retry_max_attempts: int = 1,
) -> dict[str, Any]:
    raw_run_scores: list[dict[str, Any]] = []
    judge_parse_failures = 0
    judge_provider_failures = 0
    judge_retry_attempts = 0

    for run_index in range(max(1, runs)):
        if run_index > 0 and request_sleep_seconds > 0:
            time.sleep(request_sleep_seconds)
        prompt = build_judge_prompt(case, answer, evidence_cards)
        raw_score, diagnostics = _run_single_judge(
            prompt,
            provider,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            retry_max_attempts=retry_max_attempts,
            retry_base_sleep_seconds=retry_base_sleep_seconds,
            retry_max_sleep_seconds=retry_max_sleep_seconds,
            json_retry_max_attempts=json_retry_max_attempts,
        )
        raw_run_scores.append(raw_score)
        judge_parse_failures += diagnostics["parse_failures"]
        judge_provider_failures += diagnostics["provider_failures"]
        judge_retry_attempts += diagnostics["retry_attempts"]

    threshold = ceil(max(1, runs) / 2)
    criteria_scores = {
        criterion: int(sum(int(run.get(criterion, 0)) for run in raw_run_scores) >= threshold)
        for criterion in CRITERIA
    }
    criteria_reasons = {
        criterion: _majority_reason(criterion, raw_run_scores, criteria_scores[criterion])
        for criterion in CRITERIA
    }
    criteria_passed = sum(criteria_scores.values())
    return {
        "criteria_passed": criteria_passed,
        "criteria_scores": criteria_scores,
        "criteria_reasons": criteria_reasons,
        "raw_run_scores": raw_run_scores,
        "judge_parse_failures": judge_parse_failures,
        "judge_provider_failures": judge_provider_failures,
        "judge_retry_attempts": judge_retry_attempts,
        "judge_runs": max(1, runs),
        "judge_overall_pass": criteria_passed >= 4,
    }


def validate_case_v3(
    case,
    answer,
    evidence_cards,
    provider,
    runs: int = 3,
    temperature: float = 0.3,
    max_output_tokens: int = 600,
    request_sleep_seconds: float = 6,
    retry_max_attempts: int = 4,
    retry_base_sleep_seconds: float = 8,
    retry_max_sleep_seconds: float = 90,
    json_retry_max_attempts: int = 1,
) -> dict[str, Any]:
    answer_dict = dict(answer)
    judge = run_judge(
        case,
        answer_dict,
        evidence_cards,
        provider,
        runs=runs,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        request_sleep_seconds=request_sleep_seconds,
        retry_max_attempts=retry_max_attempts,
        retry_base_sleep_seconds=retry_base_sleep_seconds,
        retry_max_sleep_seconds=retry_max_sleep_seconds,
        json_retry_max_attempts=json_retry_max_attempts,
    )
    diagnostics = _diagnostics(case, answer_dict, evidence_cards)
    strict_overall_pass = (
        bool(judge["judge_overall_pass"])
        and diagnostics["cited_ids_grounded"]
        and diagnostics["schema_fields_present"]
    )
    failed_criteria = [criterion for criterion, passed in judge["criteria_scores"].items() if not passed]
    failed_diagnostics = [name for name, passed in diagnostics.items() if not passed]
    return {
        "case_id": _get(case, "id"),
        "judge_overall_pass": bool(judge["judge_overall_pass"]),
        "strict_overall_pass": strict_overall_pass,
        "criteria_passed": judge["criteria_passed"],
        "criteria_scores": judge["criteria_scores"],
        "criteria_reasons": judge["criteria_reasons"],
        "diagnostics": diagnostics,
        "raw_run_scores": judge["raw_run_scores"],
        "judge_parse_failures": judge["judge_parse_failures"],
        "judge_provider_failures": judge["judge_provider_failures"],
        "judge_retry_attempts": judge["judge_retry_attempts"],
        "judge_runs": judge["judge_runs"],
        "overall_pass": strict_overall_pass,
        "failure_reasons": [*failed_criteria, *failed_diagnostics],
    }


def _run_single_judge(
    prompt: str,
    provider: Any,
    *,
    temperature: float,
    max_output_tokens: int,
    retry_max_attempts: int,
    retry_base_sleep_seconds: float,
    retry_max_sleep_seconds: float,
    json_retry_max_attempts: int,
) -> tuple[dict[str, Any], dict[str, int]]:
    provider_attempts = 0
    parse_failures = 0
    provider_failures = 0
    retry_attempts = 0
    json_limit = max(1, json_retry_max_attempts)
    provider_limit = max(1, retry_max_attempts)

    while provider_attempts < provider_limit:
        try:
            raw_text = _call_provider(provider, prompt, temperature, max_output_tokens)
            try:
                return _normalize_judge_json(json.loads(_extract_json_object(raw_text))), {
                    "parse_failures": parse_failures,
                    "provider_failures": provider_failures,
                    "retry_attempts": retry_attempts,
                }
            except Exception as exc:
                parse_failures += 1
                if parse_failures >= json_limit:
                    return _failed_run(f"Judge JSON parse failure: {exc}"), {
                        "parse_failures": parse_failures,
                        "provider_failures": provider_failures,
                        "retry_attempts": retry_attempts,
                    }
                continue
        except Exception as exc:
            provider_failures += 1
            provider_attempts += 1
            if provider_attempts >= provider_limit or not is_retryable_vertex_error(exc):
                return _failed_run(f"Judge provider failure: {exc}"), {
                    "parse_failures": parse_failures,
                    "provider_failures": provider_failures,
                    "retry_attempts": retry_attempts,
                }
            retry_attempts += 1
            sleep_seconds = min(retry_max_sleep_seconds, retry_base_sleep_seconds * (2 ** (provider_attempts - 1)))
            sleep_seconds *= random.uniform(0.8, 1.25)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    return _failed_run("Judge provider failure: exhausted retries"), {
        "parse_failures": parse_failures,
        "provider_failures": provider_failures,
        "retry_attempts": retry_attempts,
    }


def _call_provider(provider: Any, prompt: str, temperature: float, max_output_tokens: int) -> str:
    if callable(provider) and not hasattr(provider, "synthesize_grounded_answer"):
        response = provider(prompt)
    else:
        response = provider.synthesize_grounded_answer(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    if isinstance(response, str):
        return response
    if isinstance(response, Mapping):
        return str(response.get("text", ""))
    ok = getattr(response, "ok", True)
    if not ok:
        raise RuntimeError(getattr(response, "provider_error", None) or "Judge provider failed.")
    return str(getattr(response, "text", response) or "")


def _normalize_judge_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    reasons = dict(payload.get("reasons") or {})
    normalized = {
        criterion: _as_binary(payload.get(criterion))
        for criterion in CRITERIA
    }
    normalized["reasons"] = {
        criterion: str(reasons.get(criterion) or "No reason supplied.")[:500]
        for criterion in CRITERIA
    }
    return normalized


def _failed_run(reason: str) -> dict[str, Any]:
    return {
        **{criterion: 0 for criterion in CRITERIA},
        "reasons": {criterion: reason for criterion in CRITERIA},
    }


def _majority_reason(criterion: str, raw_run_scores: list[dict[str, Any]], passed: int) -> str:
    target = 1 if passed else 0
    for run in raw_run_scores:
        if int(run.get(criterion, 0)) == target:
            return str((run.get("reasons") or {}).get(criterion) or "")
    return ""


def _diagnostics(case: Any, answer: Mapping[str, Any], evidence_cards: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    expected_behavior = str(_get(case, "expected_behavior") or "").lower()
    behavior = str(answer.get("behavior") or "").lower()
    allowed_ids = {str(card.get("evidence_id")) for card in evidence_cards if card.get("evidence_id")}
    cited = answer.get("cited_evidence_ids") or []
    if isinstance(cited, str):
        cited = [cited]
    return {
        "behavior_label_match": behavior == expected_behavior,
        "cited_ids_grounded": all(str(item) in allowed_ids for item in cited),
        "schema_fields_present": REQUIRED_SCHEMA_FIELDS.issubset(answer.keys()),
    }


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        raise ValueError("Judge response did not contain a JSON object.")
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        char = text[idx]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    raise ValueError("Judge response contained incomplete JSON.")


def _as_binary(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if value >= 1 else 0
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "pass", "passed", "yes"} else 0
    return 0


def _get(item: Any, key: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)
