from __future__ import annotations

import json
import random
import re
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
- Think privately. Return only compact JSON.
- Judge against evidence cards only. No outside knowledge.
- Do NOT penalize different phrasing of the same correct fact.
- Do NOT reward confident answers that contradict evidence cards.
- A correct refusal when evidence is missing is a PASS.
- A refusal when sufficient evidence exists is a FAIL.
- A confident specific value when evidence is missing is a FAIL.
- Answer phrasing may vary freely. Truth against cards may not.
- Different dates in a time series are not conflict.
- Transaction/publication time is not valid time unless the question asks for it.
- Do not return markdown.
- Do not include prose before or after JSON.
- Give one short reason under 20 words, not step-by-step reasoning.
"""

JUDGE_OUTPUT_SCHEMA = {
    "scores": [1, 1, 1, 1, 1],
    "reason": "grounded and temporally correct",
}

REQUIRED_SCHEMA_FIELDS = {"answer", "behavior", "cited_evidence_ids", "valid_time_used", "confidence"}

LAYER2B_JUDGE_FIELDS = [
    "semantic_answer_correct",
    "reference_supported",
    "evidence_grounded",
    "expected_evidence_used",
    "valid_time_correct",
    "behavior_correct",
    "partial_refusal_correct",
    "conflict_handling_correct",
    "no_hallucination",
    "overall_judge_pass",
]

LAYER2B_JUDGE_SEVERITIES = {"pass", "minor", "major", "critical"}

LAYER2B_JUDGE_OUTPUT_SCHEMA = {
    "semantic_answer_correct": True,
    "reference_supported": True,
    "evidence_grounded": True,
    "expected_evidence_used": True,
    "valid_time_correct": True,
    "behavior_correct": True,
    "partial_refusal_correct": True,
    "conflict_handling_correct": True,
    "no_hallucination": True,
    "overall_judge_pass": True,
    "severity": "pass | minor | major | critical",
    "failure_reasons": [],
    "brief_rationale": "grounded and temporally correct",
}


def evidence_cards_from_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    """Build compact judge cards; large raw text made prior Vertex judge JSON truncate."""
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
                "raw_text": _truncate(str(_get(row, "raw_text") or ""), 360),
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

Score mapping:
- scores[0] = temporal_scope_correct
- scores[1] = factual_grounding
- scores[2] = behavior_justified
- scores[3] = transaction_time_clean
- scores[4] = no_overconfidence

Return ONLY one valid JSON object.
Do not include markdown, code fences, prose, or explanation outside JSON.
Do not return nested reasons.
Use this compact output schema:
{json.dumps(JUDGE_OUTPUT_SCHEMA, sort_keys=True, indent=2)}
"""


def run_judge(
    case,
    answer,
    evidence_cards,
    provider,
    runs: int = 3,
    temperature: float = 0.3,
    max_output_tokens: int = 1000,
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

    # Majority vote uses only parsed judge runs. Parse/provider failures are
    # infrastructure gaps, not semantic zeroes for the answer under test.
    scored_runs = [run for run in raw_run_scores if run.get("judge_run_status") == "scored"]
    unscored_runs = len(raw_run_scores) - len(scored_runs)
    recovered_runs = sum(1 for run in scored_runs if run.get("judge_recovered_partial_json"))
    if not scored_runs:
        criteria_scores = {criterion: 0 for criterion in CRITERIA}
        criteria_reasons = {
            criterion: "unscored_due_to_judge_failure"
            for criterion in CRITERIA
        }
        return {
            "criteria_passed": 0,
            "criteria_scores": criteria_scores,
            "criteria_reasons": criteria_reasons,
            "raw_run_scores": raw_run_scores,
            "judge_parse_failures": judge_parse_failures,
            "judge_provider_failures": judge_provider_failures,
            "judge_retry_attempts": judge_retry_attempts,
            "judge_runs": max(1, runs),
            "judge_scored_runs": 0,
            "judge_unscored_runs": unscored_runs,
            "judge_recovered_partial_json_count": 0,
            "judge_infrastructure_failure": True,
            "judge_reason": "unscored_due_to_judge_failure",
            "judge_overall_pass": False,
        }

    threshold = ceil(len(scored_runs) / 2)
    criteria_scores = {
        criterion: int(sum(int(run.get(criterion, 0)) for run in scored_runs) >= threshold)
        for criterion in CRITERIA
    }
    criteria_reasons = {
        criterion: _majority_reason(criterion, scored_runs, criteria_scores[criterion])
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
        "judge_scored_runs": len(scored_runs),
        "judge_unscored_runs": unscored_runs,
        "judge_recovered_partial_json_count": recovered_runs,
        "judge_infrastructure_failure": False,
        "judge_reason": _first_scored_reason(scored_runs),
        "judge_overall_pass": criteria_passed >= 4,
    }


def validate_case_v3(
    case,
    answer,
    evidence_cards,
    provider,
    runs: int = 3,
    temperature: float = 0.3,
    max_output_tokens: int = 1000,
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
        "judge_infrastructure_failure": judge["judge_infrastructure_failure"],
        "judge_reason": judge["judge_reason"],
        "diagnostics": diagnostics,
        "raw_run_scores": judge["raw_run_scores"],
        "judge_parse_failures": judge["judge_parse_failures"],
        "judge_provider_failures": judge["judge_provider_failures"],
        "judge_retry_attempts": judge["judge_retry_attempts"],
        "judge_scored_runs": judge["judge_scored_runs"],
        "judge_unscored_runs": judge["judge_unscored_runs"],
        "judge_recovered_partial_json_count": judge["judge_recovered_partial_json_count"],
        "judge_runs": judge["judge_runs"],
        "overall_pass": strict_overall_pass,
        "failure_reasons": [*failed_criteria, *failed_diagnostics],
    }


def build_layer2b_judge_prompt(
    case: Mapping[str, Any] | Any,
    answer: Mapping[str, Any],
    evidence_cards: Sequence[Mapping[str, Any]],
    deterministic_validation: Mapping[str, Any] | None = None,
) -> str:
    safe_case = {
        "question_id": _get(case, "question_id") or _get(case, "id"),
        "question": _get(case, "question"),
        "reference_answer": _get(case, "reference_answer"),
        "expected_evidence_ids": _get(case, "expected_evidence_ids") or [],
        "expected_valid_time": _get(case, "expected_valid_time"),
        "expected_answer_behavior": _get(case, "answer_behavior") or _get(case, "expected_answer_behavior") or _get(case, "expected_behavior"),
        "question_type": _get(case, "question_type"),
        "source_family": _get(case, "source_family") or _get(case, "domain"),
    }
    safe_answer = {
        "answer": answer.get("answer", ""),
        "cited_evidence_ids": answer.get("cited_evidence_ids", []),
        "valid_time_used": answer.get("valid_time_used", ""),
        "answer_behavior": answer.get("answer_behavior", answer.get("behavior", "")),
        "conflict_warning": answer.get("conflict_warning", False),
        "partial_or_refusal": answer.get("partial_or_refusal", False),
        "confidence": answer.get("confidence", "low"),
    }
    return f"""You are ChronoRAG's Layer 2B strict-but-fair temporal answer judge.

Judge only the system answer against the reference answer and supplied evidence cards. Do not use outside knowledge.

Fairness rules:
- Accept paraphrases, concise answers, equivalent wording, and harmless formatting differences.
- Do not require exact reference wording or citation order.
- Accept extra explanation only when it is supported by supplied evidence.
- Do not mark an answer wrong solely because it is shorter than the reference.

Strictness rules:
- Fail wrong dates, wrong time type, wrong entity, wrong value, wrong status, wrong document/release/form, or wrong evidence.
- Fail unsupported claims, hallucinated details, outside knowledge, or overconfident answers when evidence is insufficient.
- Valid time means when the fact is true, observed, effective, reported, or applies.
- Transaction time means when the record was filed, published, released, stored, or made available.
- Use the time requested by the question. If both valid and transaction time matter, both must be distinguished.
- For partial/refusal cases, a cautious partial answer can pass; an unsupported specific answer must fail.
- For conflict cases, the answer must surface the conflict and avoid collapsing disagreement.

Evaluate these dimensions:
- semantic_answer_correct: answer matches the reference answer in meaning, not exact wording.
- reference_supported: answer is compatible with reference_answer and expected evidence.
- evidence_grounded: answer uses only supplied evidence and cites used evidence.
- expected_evidence_used: answer cites all required expected_evidence_ids unless correct behavior is partial/refusal due to missing evidence.
- valid_time_correct: answer uses expected valid time or correctly distinguishes valid time from transaction/publication/filing/release time.
- behavior_correct: answer_behavior matches expected answer_behavior, allowing partial/refuse_or_clarify interchange only for expected partial/refuse_or_clarify.
- partial_refusal_correct: insufficient or ambiguous cases avoid overclaiming.
- conflict_handling_correct: conflict cases surface disagreement; non-conflict cases do not invent conflict.
- no_hallucination: no unsupported facts, outside knowledge, invented values, dates, entities, or details.
- overall_judge_pass: true only when the answer is semantically correct, grounded, temporally correct, behaviorally correct, and not hallucinated.

Layer 2B case:
{json.dumps(safe_case, ensure_ascii=False, sort_keys=True, indent=2)}

System answer:
{json.dumps(safe_answer, ensure_ascii=False, sort_keys=True, indent=2)}

Deterministic hard-contract result from answer runner:
{json.dumps(dict(deterministic_validation or {}), ensure_ascii=False, sort_keys=True, indent=2)}

Evidence cards supplied to the answer model:
{json.dumps(list(evidence_cards), ensure_ascii=False, sort_keys=True, indent=2)}

Return exactly one JSON object.
No markdown fences.
No prose outside JSON.
Never use null; use false, [], or "".
brief_rationale must be short.
Use exactly this JSON schema:
{json.dumps(LAYER2B_JUDGE_OUTPUT_SCHEMA, ensure_ascii=False, sort_keys=True, indent=2)}
"""


def run_layer2b_judge(
    case: Mapping[str, Any] | Any,
    answer: Mapping[str, Any],
    evidence_cards: Sequence[Mapping[str, Any]],
    provider: Any,
    deterministic_validation: Mapping[str, Any] | None = None,
    runs: int = 1,
    temperature: float = 0.0,
    max_output_tokens: int = 3000,
    request_sleep_seconds: float = 10,
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
        prompt = build_layer2b_judge_prompt(case, answer, evidence_cards, deterministic_validation)
        raw_score, diagnostics = _run_single_layer2b_judge(
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

    scored_runs = [run for run in raw_run_scores if run.get("judge_run_status") == "scored"]
    unscored_runs = len(raw_run_scores) - len(scored_runs)
    recovered_runs = sum(1 for run in scored_runs if run.get("judge_recovered_partial_json"))
    if not scored_runs:
        return {
            **{field: False for field in LAYER2B_JUDGE_FIELDS},
            "severity": "critical",
            "failure_reasons": ["unscored_due_to_judge_failure"],
            "brief_rationale": "Judge did not return a scorable result.",
            "raw_run_scores": raw_run_scores,
            "judge_parse_failures": judge_parse_failures,
            "judge_provider_failures": judge_provider_failures,
            "judge_retry_attempts": judge_retry_attempts,
            "judge_runs": max(1, runs),
            "judge_scored_runs": 0,
            "judge_unscored_runs": unscored_runs,
            "judge_recovered_partial_json_count": 0,
            "judge_infrastructure_failure": True,
        }

    threshold = ceil(len(scored_runs) / 2)
    aggregate = {
        field: sum(1 for run in scored_runs if bool(run.get(field))) >= threshold
        for field in LAYER2B_JUDGE_FIELDS
    }
    overall = bool(aggregate["overall_judge_pass"]) and all(
        aggregate[field] for field in LAYER2B_JUDGE_FIELDS if field != "overall_judge_pass"
    )
    aggregate["overall_judge_pass"] = overall
    failure_reasons = _layer2b_failure_reasons(scored_runs, aggregate)
    return {
        **aggregate,
        "severity": "pass" if overall else _worst_layer2b_severity(scored_runs),
        "failure_reasons": failure_reasons,
        "brief_rationale": _first_layer2b_rationale(scored_runs),
        "raw_run_scores": raw_run_scores,
        "judge_parse_failures": judge_parse_failures,
        "judge_provider_failures": judge_provider_failures,
        "judge_retry_attempts": judge_retry_attempts,
        "judge_runs": max(1, runs),
        "judge_scored_runs": len(scored_runs),
        "judge_unscored_runs": unscored_runs,
        "judge_recovered_partial_json_count": recovered_runs,
        "judge_infrastructure_failure": False,
    }


def _run_single_layer2b_judge(
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
                return _normalize_layer2b_judge_json(json.loads(_extract_json_object(raw_text))), {
                    "parse_failures": parse_failures,
                    "provider_failures": provider_failures,
                    "retry_attempts": retry_attempts,
                }
            except Exception as exc:
                parse_failures += 1
                if parse_failures >= json_limit:
                    return _unscored_layer2b_judge_run("parse_failure", f"Judge JSON parse failure: {exc}"), {
                        "parse_failures": parse_failures,
                        "provider_failures": provider_failures,
                        "retry_attempts": retry_attempts,
                    }
                continue
        except Exception as exc:
            provider_failures += 1
            provider_attempts += 1
            if provider_attempts >= provider_limit or not is_retryable_vertex_error(exc):
                return _unscored_layer2b_judge_run("provider_failure", f"Judge provider failure: {exc}"), {
                    "parse_failures": parse_failures,
                    "provider_failures": provider_failures,
                    "retry_attempts": retry_attempts,
                }
            retry_attempts += 1
            sleep_seconds = min(retry_max_sleep_seconds, retry_base_sleep_seconds * (2 ** (provider_attempts - 1)))
            sleep_seconds *= random.uniform(0.8, 1.25)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    return _unscored_layer2b_judge_run("provider_failure", "Judge provider failure: exhausted retries"), {
        "parse_failures": parse_failures,
        "provider_failures": provider_failures,
        "retry_attempts": retry_attempts,
    }


def _normalize_layer2b_judge_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {
        field: _as_bool_strict(payload.get(field), field)
        for field in LAYER2B_JUDGE_FIELDS
    }
    severity = str(payload.get("severity") or "").strip().lower()
    if severity not in LAYER2B_JUDGE_SEVERITIES:
        raise ValueError(f"Invalid Layer 2B judge severity: {severity!r}")
    failure_reasons = payload.get("failure_reasons")
    if failure_reasons is None:
        failure_reasons = []
    if not isinstance(failure_reasons, list):
        raise ValueError("Layer 2B judge failure_reasons must be a list.")
    rationale = str(payload.get("brief_rationale") or "")[:500]
    normalized.update(
        {
            "severity": severity,
            "failure_reasons": [str(item) for item in failure_reasons],
            "brief_rationale": _compact_reason(rationale),
            "judge_run_status": "scored",
            "judge_recovered_partial_json": False,
        }
    )
    return normalized


def _unscored_layer2b_judge_run(status: str, reason: str) -> dict[str, Any]:
    return {
        "judge_run_status": status,
        "severity": "critical",
        "failure_reasons": [reason],
        "brief_rationale": reason,
        **{field: False for field in LAYER2B_JUDGE_FIELDS},
    }


def _layer2b_failure_reasons(
    scored_runs: Sequence[Mapping[str, Any]],
    aggregate: Mapping[str, bool],
) -> list[str]:
    reasons: list[str] = []
    for field in LAYER2B_JUDGE_FIELDS:
        if field != "overall_judge_pass" and not aggregate.get(field):
            reasons.append(field)
    for run in scored_runs:
        for reason in run.get("failure_reasons") or []:
            text = str(reason)
            if text and text not in reasons:
                reasons.append(text)
    return reasons


def _worst_layer2b_severity(scored_runs: Sequence[Mapping[str, Any]]) -> str:
    rank = {"pass": 0, "minor": 1, "major": 2, "critical": 3}
    worst = "pass"
    for run in scored_runs:
        severity = str(run.get("severity") or "pass").lower()
        if rank.get(severity, 0) > rank[worst]:
            worst = severity
    return worst


def _first_layer2b_rationale(scored_runs: Sequence[Mapping[str, Any]]) -> str:
    for run in scored_runs:
        rationale = str(run.get("brief_rationale") or "")
        if rationale:
            return _compact_reason(rationale)
    return "No rationale supplied."


def _as_bool_strict(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise ValueError(f"Layer 2B judge field {field} must be boolean.")


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
                recovered = _recover_scores_from_partial_text(raw_text)
                if recovered is not None:
                    return recovered, {
                        "parse_failures": parse_failures,
                        "provider_failures": provider_failures,
                        "retry_attempts": retry_attempts,
                    }
                parse_failures += 1
                if parse_failures >= json_limit:
                    return _unscored_run("parse_failure", f"Judge JSON parse failure: {exc}"), {
                        "parse_failures": parse_failures,
                        "provider_failures": provider_failures,
                        "retry_attempts": retry_attempts,
                    }
                continue
        except Exception as exc:
            provider_failures += 1
            provider_attempts += 1
            if provider_attempts >= provider_limit or not is_retryable_vertex_error(exc):
                return _unscored_run("provider_failure", f"Judge provider failure: {exc}"), {
                    "parse_failures": parse_failures,
                    "provider_failures": provider_failures,
                    "retry_attempts": retry_attempts,
                }
            retry_attempts += 1
            sleep_seconds = min(retry_max_sleep_seconds, retry_base_sleep_seconds * (2 ** (provider_attempts - 1)))
            sleep_seconds *= random.uniform(0.8, 1.25)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    return _unscored_run("provider_failure", "Judge provider failure: exhausted retries"), {
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
    if "scores" in payload:
        scores = payload.get("scores")
        if not isinstance(scores, list) or len(scores) != len(CRITERIA):
            raise ValueError("Judge compact scores must be a list of exactly five values.")
        normalized = {
            criterion: _as_binary(scores[index])
            for index, criterion in enumerate(CRITERIA)
        }
        reason = str(payload.get("reason") or "No reason supplied.")[:500]
        normalized.update(
            {
                "scores": [normalized[criterion] for criterion in CRITERIA],
                "reason": _compact_reason(reason),
                "reasons": {criterion: reason for criterion in CRITERIA},
                "judge_run_status": "scored",
                "judge_recovered_partial_json": False,
            }
        )
        return normalized

    reasons = dict(payload.get("reasons") or {})
    normalized = {
        criterion: _as_binary(payload.get(criterion))
        for criterion in CRITERIA
    }
    normalized["reasons"] = {
        criterion: str(reasons.get(criterion) or "No reason supplied.")[:500]
        for criterion in CRITERIA
    }
    normalized["scores"] = [normalized[criterion] for criterion in CRITERIA]
    normalized["reason"] = _compact_reason(_first_reason(normalized["reasons"]))
    normalized["judge_run_status"] = "scored"
    normalized["judge_recovered_partial_json"] = False
    return normalized


def _recover_scores_from_partial_text(text: str) -> dict[str, Any] | None:
    match = re.search(r'"scores"\s*:\s*\[([^\]]+)\]', text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    raw_items = [item.strip().strip('"').strip("'") for item in match.group(1).split(",")]
    if len(raw_items) != len(CRITERIA):
        return None
    scores = [_as_binary(item) for item in raw_items]
    normalized = {
        criterion: scores[index]
        for index, criterion in enumerate(CRITERIA)
    }
    reason_match = re.search(r'"reason"\s*:\s*"([^"]{1,160})"', text, flags=re.IGNORECASE | re.DOTALL)
    reason = _compact_reason(reason_match.group(1)) if reason_match else "recovered scores from partial JSON"
    normalized.update(
        {
            "scores": scores,
            "reason": reason,
            "reasons": {criterion: reason for criterion in CRITERIA},
            "judge_run_status": "scored",
            "judge_recovered_partial_json": True,
        }
    )
    return normalized


def _unscored_run(status: str, reason: str) -> dict[str, Any]:
    return {
        "judge_run_status": status,
        "scores": None,
        "reason": reason,
        "reasons": {criterion: reason for criterion in CRITERIA},
    }


def _majority_reason(criterion: str, raw_run_scores: list[dict[str, Any]], passed: int) -> str:
    target = 1 if passed else 0
    for run in raw_run_scores:
        if int(run.get(criterion, 0)) == target:
            return str((run.get("reasons") or {}).get(criterion) or "")
    return ""


def _first_scored_reason(raw_run_scores: list[dict[str, Any]]) -> str:
    for run in raw_run_scores:
        reason = str(run.get("reason") or "")
        if reason:
            return reason
    return ""


def _first_reason(reasons: Mapping[str, Any]) -> str:
    for criterion in CRITERIA:
        reason = str(reasons.get(criterion) or "")
        if reason:
            return reason
    return "No reason supplied."


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
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    starts = [idx for idx, char in enumerate(stripped) if char == "{"]
    if not starts:
        raise ValueError("Judge response did not contain a JSON object.")
    for start in starts:
        candidate = _balanced_json_from(stripped, start)
        if candidate is not None:
            return candidate
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        return stripped[first : last + 1]
    raise ValueError("Judge response contained incomplete JSON.")


def _balanced_json_from(text: str, start: int) -> str | None:
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
    return None


def _as_binary(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if value >= 1 else 0
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "pass", "passed", "yes"} else 0
    return 0


def _compact_reason(reason: str) -> str:
    words = str(reason).replace("\n", " ").split()
    return " ".join(words[:20]) or "No reason supplied."


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def _get(item: Any, key: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)
