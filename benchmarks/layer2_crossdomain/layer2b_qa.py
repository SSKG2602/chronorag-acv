from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import (
    ChronoRAGPreparedContext,
    prepare_chronorag_context,
    retrieve_with_chronorag_prepared,
)
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase, load_corpus
from benchmarks.layer2_crossdomain.validate_layer2b_manual_qa import (
    ALLOWED_ANSWER_BEHAVIORS,
    ALLOWED_DIFFICULTIES,
    ALLOWED_QUESTION_TYPES,
    ID_FIELDS,
    REQUIRED_FIELDS,
)
from benchmarks.layer2_crossdomain.vertex_retry import call_with_backoff


DEFAULT_QA_PATH = Path("benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl")
DEFAULT_CORPUS_PATH = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
RESULTS_ROOT = Path("benchmarks/layer2_crossdomain/results")
METHOD_NAME = "chronorag_full"

ANSWER_BEHAVIORS = {"answer", "compare", "warn_conflict", "partial", "refuse_or_clarify"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
ANSWER_REQUIRED_FIELDS = {
    "answer",
    "cited_evidence_ids",
    "valid_time_used",
    "answer_behavior",
    "conflict_warning",
    "partial_or_refusal",
    "confidence",
}

QUESTION_TYPE_TO_CATEGORY = {
    "exact_lookup": "exact_valid_time_retrieval",
    "comparison": "cross_domain_temporal_comparison",
    "wrong_time_trap": "same_entity_wrong_time_trap",
    "transaction_valid_time_trap": "valid_time_vs_transaction_time",
    "broad_window_trap": "exact_vs_broad_temporal_preference",
    "conflict": "conflict_detection",
    "partial_or_insufficient": "partial_or_insufficient_evidence",
    "ambiguous_time": "ambiguous_time_query",
    "chronology": "multi_slot_temporal_coverage",
}

ANSWER_BEHAVIOR_TO_EXPECTED_BEHAVIOR = {
    "answer": "answer",
    "compare": "compare",
    "warn_conflict": "conflict_warning",
    "partial": "partial",
    "refuse_or_clarify": "clarify",
}


@dataclass(frozen=True)
class Layer2BQACase:
    question_id: str
    question: str
    reference_answer: str
    expected_evidence_ids: list[str]
    expected_valid_time: str
    source_family: str
    question_type: str
    answer_behavior: str
    difficulty: str
    why_this_is_a_good_temporal_case: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any], line_number: int) -> "Layer2BQACase":
        errors = validate_case_payload(payload)
        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"Invalid Layer 2B case at line {line_number}: {joined}")
        return cls(
            question_id=str(payload["question_id"]),
            question=str(payload["question"]),
            reference_answer=str(payload["reference_answer"]),
            expected_evidence_ids=[str(item) for item in payload["expected_evidence_ids"]],
            expected_valid_time=str(payload["expected_valid_time"]),
            source_family=str(payload["source_family"]),
            question_type=str(payload["question_type"]),
            answer_behavior=str(payload["answer_behavior"]),
            difficulty=str(payload["difficulty"]),
            why_this_is_a_good_temporal_case=str(payload["why_this_is_a_good_temporal_case"]),
        )

    def to_question_case(self) -> QuestionCase:
        return QuestionCase(
            id=self.question_id,
            domain=self.source_family,
            question=self.question,
            category=QUESTION_TYPE_TO_CATEGORY[self.question_type],
            expected_behavior=ANSWER_BEHAVIOR_TO_EXPECTED_BEHAVIOR[self.answer_behavior],
            expected_evidence_ids=list(self.expected_evidence_ids),
            acceptable_evidence_ids=[],
            forbidden_evidence_ids=[],
            required_facts=[],
            forbidden_facts=[],
            expected_valid_time=_split_expected_valid_time(self.expected_valid_time),
            notes=self.why_this_is_a_good_temporal_case,
            synthetic_evidence_ids=[],
        )


def validate_case_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(payload))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    for field in ("question_id", "question", "reference_answer", "expected_valid_time", "source_family"):
        if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
            errors.append(f"{field} must be a non-empty string")
    expected_ids = payload.get("expected_evidence_ids")
    if not isinstance(expected_ids, list) or not expected_ids or not all(isinstance(item, str) and item for item in expected_ids):
        errors.append("expected_evidence_ids must be a non-empty list of strings")
    if payload.get("question_type") not in ALLOWED_QUESTION_TYPES:
        errors.append(f"invalid question_type: {payload.get('question_type')!r}")
    if payload.get("answer_behavior") not in ALLOWED_ANSWER_BEHAVIORS:
        errors.append(f"invalid answer_behavior: {payload.get('answer_behavior')!r}")
    if payload.get("difficulty") not in ALLOWED_DIFFICULTIES:
        errors.append(f"invalid difficulty: {payload.get('difficulty')!r}")
    return errors


def load_layer2b_cases(path: str | Path = DEFAULT_QA_PATH) -> list[Layer2BQACase]:
    cases: list[Layer2BQACase] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: expected object")
            cases.append(Layer2BQACase.from_dict(payload, line_number))
    return cases


def load_selected_corpus(path: str | Path = DEFAULT_CORPUS_PATH) -> list[CorpusRow]:
    return load_corpus(path)


def build_evidence_lookup(corpus: Iterable[CorpusRow]) -> dict[str, CorpusRow]:
    lookup: dict[str, CorpusRow] = {}
    for row in corpus:
        lookup[row.id] = row
        for field in ID_FIELDS:
            value = getattr(row, field, None)
            if isinstance(value, str) and value:
                lookup.setdefault(value, row)
        for field in ID_FIELDS:
            value = row.metadata.get(field)
            if isinstance(value, str) and value:
                lookup.setdefault(value, row)
    return lookup


def prepare_retrieval_context(corpus: list[CorpusRow]) -> ChronoRAGPreparedContext:
    return prepare_chronorag_context(corpus)


def retrieve_chronorag_full(
    case: Layer2BQACase,
    prepared_context: ChronoRAGPreparedContext,
    top_k: int,
) -> tuple[list[CorpusRow], dict[str, Any]]:
    return retrieve_with_chronorag_prepared(case.to_question_case(), prepared_context, top_k)


def build_layer2b_prompt(case: Layer2BQACase, evidence_rows: list[CorpusRow]) -> str:
    cards = "\n".join(json.dumps(_evidence_card(row, index), ensure_ascii=True, sort_keys=True) for index, row in enumerate(evidence_rows, start=1))
    schema = {
        "answer": "string",
        "cited_evidence_ids": ["string"],
        "valid_time_used": "string",
        "answer_behavior": "answer | compare | warn_conflict | partial | refuse_or_clarify",
        "conflict_warning": False,
        "partial_or_refusal": False,
        "confidence": "high | medium | low",
    }
    return f"""You are ChronoRAG's Layer 2B grounded temporal answer synthesizer.

Return only one strict JSON object. Do not include markdown, code fences, or prose outside JSON.

Rules:
- Use only the retrieved evidence cards below.
- Cite only evidence IDs from the provided evidence cards.
- Do not invent evidence IDs.
- Do not use outside knowledge.
- If evidence is insufficient, use answer_behavior "partial" or "refuse_or_clarify".
- Distinguish filing, publication, release, and transaction time from valid, effective, report, event, or observation time.
- For SEC records, filing date is transaction/publication time and report date is valid/event time when present.
- For Federal Register records, publication date is transaction/publication time and effective date is valid time when present.
- For FRED and market index rows, observation date is valid time.
- For GitHub releases, release timestamp/date is valid event time for this benchmark.
- Preserve exact values and dates from evidence.
- Do not hallucinate details not present in evidence.
- If multiple evidence rows are needed for comparison or chronology, cite all rows used.

User question:
{case.question}

Expected answer behavior label for evaluation:
{case.answer_behavior}

Required answer JSON schema:
{json.dumps(schema, sort_keys=True)}

Retrieved evidence cards:
{cards}
"""


def parse_answer_json(raw_text: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    diagnostics = {
        "json_parse_error": None,
        "json_recovered": False,
        "json_recovery_method": None,
    }
    try:
        return json.loads(raw_text.strip()), diagnostics
    except json.JSONDecodeError as first_exc:
        extracted, method = _extract_first_json_object(raw_text)
        if extracted is None:
            diagnostics["json_parse_error"] = str(first_exc)
            return None, diagnostics
        try:
            diagnostics["json_recovered"] = True
            diagnostics["json_recovery_method"] = method
            return json.loads(extracted), diagnostics
        except json.JSONDecodeError as exc:
            diagnostics["json_parse_error"] = str(exc)
            return None, diagnostics


def validate_answer_contract(
    case: Layer2BQACase,
    answer_payload: dict[str, Any] | None,
    raw_text: str,
    retrieved_evidence_ids: list[str],
    corpus_lookup: dict[str, CorpusRow],
) -> dict[str, Any]:
    normalized = normalize_answer_payload(answer_payload)
    schema_pass = normalized is not None
    cited = normalized.get("cited_evidence_ids", []) if normalized else []
    answer_text = normalized.get("answer", "") if normalized else raw_text
    valid_time_used = normalized.get("valid_time_used", "") if normalized else ""
    behavior = normalized.get("answer_behavior", "") if normalized else ""
    conflict_warning = bool(normalized.get("conflict_warning")) if normalized else False
    partial_or_refusal = bool(normalized.get("partial_or_refusal")) if normalized else False

    expected = set(case.expected_evidence_ids)
    cited_set = set(cited)
    retrieved_set = set(retrieved_evidence_ids)
    corpus_ids = set(corpus_lookup)
    expected_evidence_cited = bool(expected) and expected.issubset(cited_set)
    unknown_citation_absent = all(item in retrieved_set and item in corpus_ids for item in cited)
    valid_time_present = _expected_valid_time_present(case.expected_valid_time, valid_time_used, answer_text)
    answer_behavior_correct = _answer_behavior_correct(case.answer_behavior, behavior)
    partial_refusal_correct = _partial_refusal_correct(case.answer_behavior, behavior, partial_or_refusal)
    conflict_warning_correct = _conflict_warning_correct(case.answer_behavior, behavior, conflict_warning)

    checks = {
        "schema_pass": schema_pass,
        "expected_evidence_cited": expected_evidence_cited,
        "unknown_citation_absent": unknown_citation_absent,
        "valid_time_present": valid_time_present,
        "answer_behavior_correct": answer_behavior_correct,
        "partial_refusal_correct": partial_refusal_correct,
        "conflict_warning_correct": conflict_warning_correct,
    }
    failure_reasons = [name for name, passed in checks.items() if not passed]
    return {
        **checks,
        "overall_contract_pass": all(checks.values()),
        "failure_reasons": failure_reasons,
        "normalized_answer": normalized,
        "unknown_cited_evidence_ids": sorted(cited_set - (retrieved_set & corpus_ids)),
    }


def dry_run_validation(case: Layer2BQACase, retrieved_evidence_ids: list[str]) -> dict[str, Any]:
    missing = [evidence_id for evidence_id in case.expected_evidence_ids if evidence_id not in set(retrieved_evidence_ids)]
    return {
        "expected_evidence_retrieved_at_k": not missing,
        "missing_expected_evidence_ids": missing,
        "schema_pass": None,
        "expected_evidence_cited": None,
        "unknown_citation_absent": None,
        "valid_time_present": None,
        "answer_behavior_correct": None,
        "partial_refusal_correct": None,
        "conflict_warning_correct": None,
        "overall_contract_pass": None,
        "failure_reasons": ["answer_contract_not_applicable_in_dry_run"],
    }


def normalize_answer_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    missing = ANSWER_REQUIRED_FIELDS - set(payload)
    if missing:
        return None
    normalized = dict(payload)
    if not isinstance(normalized.get("answer"), str):
        return None
    cited = normalized.get("cited_evidence_ids")
    if isinstance(cited, str):
        cited = [cited]
    if not isinstance(cited, list) or not all(isinstance(item, str) for item in cited):
        return None
    normalized["cited_evidence_ids"] = cited
    valid_time = normalized.get("valid_time_used")
    if isinstance(valid_time, list):
        valid_time = "/".join(str(item) for item in valid_time if item)
    if not isinstance(valid_time, str):
        return None
    normalized["valid_time_used"] = valid_time
    behavior = str(normalized.get("answer_behavior") or "").strip().lower()
    if behavior not in ANSWER_BEHAVIORS:
        return None
    normalized["answer_behavior"] = behavior
    for field in ("conflict_warning", "partial_or_refusal"):
        value = normalized.get(field)
        if isinstance(value, str):
            value = value.strip().lower() == "true"
        if not isinstance(value, bool):
            return None
        normalized[field] = value
    confidence = str(normalized.get("confidence") or "").strip().lower()
    if confidence not in CONFIDENCE_LEVELS:
        return None
    normalized["confidence"] = confidence
    return normalized


def build_dry_run_result(
    case: Layer2BQACase,
    evidence_rows: list[CorpusRow],
    retrieval_metadata: dict[str, Any],
    *,
    top_k: int,
    suffix: str,
) -> dict[str, Any]:
    selected_ids = [row.id for row in evidence_rows]
    return {
        "benchmark": "layer2b_manual_qa",
        "method": METHOD_NAME,
        "mode": "dry_run",
        "result_suffix": suffix,
        "question_id": case.question_id,
        "question": case.question,
        "question_type": case.question_type,
        "expected_answer_behavior": case.answer_behavior,
        "difficulty": case.difficulty,
        "source_family": case.source_family,
        "expected_evidence_ids": case.expected_evidence_ids,
        "selected_evidence_ids": selected_ids,
        "top_k": top_k,
        "status": "completed",
        "answer": None,
        "raw_model_response": None,
        "provider_error": None,
        "validation": dry_run_validation(case, selected_ids),
        "retrieval_metadata": retrieval_metadata,
    }


def build_provider_error_result(
    case: Layer2BQACase,
    evidence_rows: list[CorpusRow],
    retrieval_metadata: dict[str, Any],
    *,
    top_k: int,
    suffix: str,
    error: Exception,
    latency_ms: float,
) -> dict[str, Any]:
    selected_ids = [row.id for row in evidence_rows]
    return {
        "benchmark": "layer2b_manual_qa",
        "method": METHOD_NAME,
        "mode": "vertex",
        "result_suffix": suffix,
        "question_id": case.question_id,
        "question": case.question,
        "question_type": case.question_type,
        "expected_answer_behavior": case.answer_behavior,
        "difficulty": case.difficulty,
        "source_family": case.source_family,
        "expected_evidence_ids": case.expected_evidence_ids,
        "selected_evidence_ids": selected_ids,
        "top_k": top_k,
        "status": "provider_error",
        "answer": None,
        "raw_model_response": None,
        "provider_error": _preview(str(error), 800),
        "latency_ms": round(latency_ms, 2),
        "validation": {
            "schema_pass": False,
            "expected_evidence_cited": False,
            "unknown_citation_absent": True,
            "valid_time_present": False,
            "answer_behavior_correct": False,
            "partial_refusal_correct": False,
            "conflict_warning_correct": False,
            "overall_contract_pass": False,
            "failure_reasons": ["provider_error"],
        },
        "retrieval_metadata": retrieval_metadata,
    }


def build_vertex_result(
    case: Layer2BQACase,
    evidence_rows: list[CorpusRow],
    retrieval_metadata: dict[str, Any],
    *,
    top_k: int,
    suffix: str,
    raw_response: str,
    answer_payload: dict[str, Any] | None,
    parse_diagnostics: dict[str, Any],
    corpus_lookup: dict[str, CorpusRow],
    latency_ms: float,
) -> dict[str, Any]:
    selected_ids = [row.id for row in evidence_rows]
    validation = validate_answer_contract(case, answer_payload, raw_response, selected_ids, corpus_lookup)
    return {
        "benchmark": "layer2b_manual_qa",
        "method": METHOD_NAME,
        "mode": "vertex",
        "result_suffix": suffix,
        "question_id": case.question_id,
        "question": case.question,
        "question_type": case.question_type,
        "expected_answer_behavior": case.answer_behavior,
        "difficulty": case.difficulty,
        "source_family": case.source_family,
        "expected_evidence_ids": case.expected_evidence_ids,
        "selected_evidence_ids": selected_ids,
        "top_k": top_k,
        "status": "completed",
        "answer": validation.pop("normalized_answer"),
        "raw_model_response": raw_response,
        "provider_error": None,
        "parse_diagnostics": parse_diagnostics,
        "latency_ms": round(latency_ms, 2),
        "validation": validation,
        "retrieval_metadata": retrieval_metadata,
    }


def run_vertex_prompt(
    prompt: str,
    *,
    temperature: float,
    max_output_tokens: int,
    retry_max_attempts: int,
    retry_base_sleep_seconds: float,
    retry_max_sleep_seconds: float,
    label: str,
) -> str:
    from core.generator.vertex_provider import VertexGeminiProvider

    provider = VertexGeminiProvider()

    def call() -> str:
        result = provider.synthesize_grounded_answer(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if not result.ok:
            detail = " ".join(item for item in (result.provider_error, result.debug) if item)
            raise RuntimeError(detail or "Vertex provider failed.")
        return result.text

    return call_with_backoff(
        call,
        max_attempts=retry_max_attempts,
        base_sleep=retry_base_sleep_seconds,
        max_sleep=retry_max_sleep_seconds,
        label=label,
    )


def result_paths(result_suffix: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", result_suffix):
        raise ValueError("--result-suffix may contain only letters, numbers, underscore, and hyphen")
    base = RESULTS_ROOT / f"layer2b_{METHOD_NAME}_{result_suffix}_results"
    return base.with_suffix(".jsonl"), base.with_suffix(".md")


def load_existing_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Cannot resume from invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Cannot resume from non-object JSONL row at {path}:{line_number}")
            rows.append(payload)
    return rows


def completed_successful_case_ids(results: Iterable[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("question_id"))
        for row in results
        if row.get("question_id") and row.get("status") == "completed"
    }


def append_jsonl_row(handle: Any, row: dict[str, Any]) -> None:
    handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    handle.flush()


def write_markdown_summary(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    mode: str,
    top_k: int,
    result_suffix: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_summary(rows, mode=mode, top_k=top_k, result_suffix=result_suffix), encoding="utf-8")


def render_markdown_summary(rows: list[dict[str, Any]], *, mode: str, top_k: int, result_suffix: str) -> str:
    provider_errors = sum(1 for row in rows if row.get("status") == "provider_error")
    schema_failures = _count_validation_false(rows, "schema_pass")
    retrieved_expected = sum(1 for row in rows if row.get("validation", {}).get("expected_evidence_retrieved_at_k"))
    expected_cited = sum(1 for row in rows if row.get("validation", {}).get("expected_evidence_cited"))
    valid_time_correct = sum(1 for row in rows if row.get("validation", {}).get("valid_time_present"))
    behavior_correct = sum(1 for row in rows if row.get("validation", {}).get("answer_behavior_correct"))
    contract_pass = sum(1 for row in rows if row.get("validation", {}).get("overall_contract_pass"))
    lines = [
        f"# Layer 2B Results: {METHOD_NAME}",
        "",
        "This is a controlled Layer 2B manual-QA runner report, not a SOTA or publication-grade claim.",
        "",
        f"- Mode: `{mode}`",
        f"- Method: `{METHOD_NAME}`",
        f"- Cases: {len(rows)}",
        f"- Top-k: {top_k}",
        f"- Result suffix: `{result_suffix}`",
        f"- Provider errors: {provider_errors}",
        f"- JSON/schema failures: {schema_failures}",
        f"- Expected evidence retrieved@k: {retrieved_expected} / {len(rows)}",
        f"- Expected evidence cited: {expected_cited} / {len(rows)}",
        f"- Valid time correctness: {valid_time_correct} / {len(rows)}",
        f"- Behavior correctness: {behavior_correct} / {len(rows)}",
        f"- Overall contract pass: {contract_pass} / {len(rows)}",
        "",
    ]
    if mode == "dry_run":
        lines.extend(
            [
                "Dry run retrieves evidence and checks retrieval coverage only. It does not call Vertex and does not evaluate generated answer quality.",
                "",
            ]
        )
    lines.extend(
        [
            "| Question ID | Type | Expected Behavior | Status | Retrieved Expected Evidence | Contract Pass | Failure Reasons |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    for row in rows:
        validation = row.get("validation", {})
        retrieved = validation.get("expected_evidence_retrieved_at_k")
        if retrieved is None:
            expected = set(row.get("expected_evidence_ids") or [])
            selected = set(row.get("selected_evidence_ids") or [])
            retrieved = bool(expected) and expected.issubset(selected)
        contract = validation.get("overall_contract_pass")
        failures = ", ".join(str(item) for item in validation.get("failure_reasons") or [])
        lines.append(
            "| {qid} | {qtype} | {behavior} | {status} | {retrieved} | {contract} | {failures} |".format(
                qid=row.get("question_id", ""),
                qtype=row.get("question_type", ""),
                behavior=row.get("expected_answer_behavior", ""),
                status=row.get("status", ""),
                retrieved=_format_bool(retrieved),
                contract="n/a" if contract is None else _format_bool(contract),
                failures=failures,
            )
        )
    return "\n".join(lines) + "\n"


def sleep_between_vertex_requests(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _evidence_card(row: CorpusRow, rank: int) -> dict[str, Any]:
    card = row.to_prompt_dict()
    card["rank"] = rank
    return card


def _split_expected_valid_time(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split("/") if part.strip()]


def _extract_first_json_object(text: str) -> tuple[str | None, str | None]:
    stripped = text.strip()
    method = "balanced_json"
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
        method = "fenced_json"
    start = stripped.find("{")
    if start < 0:
        return None, None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(stripped)):
        char = stripped[index]
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
                return stripped[start : index + 1], method
    return None, None


def _expected_valid_time_present(expected: str, valid_time_used: str, answer_text: str) -> bool:
    haystack = f"{valid_time_used} {answer_text}"
    parts = _split_expected_valid_time(expected)
    return all(part in haystack for part in parts) if parts else True


def _answer_behavior_correct(expected: str, actual: str) -> bool:
    if expected == "answer":
        return actual == "answer"
    if expected == "compare":
        return actual == "compare"
    if expected == "partial":
        return actual in {"partial", "refuse_or_clarify"}
    if expected == "refuse_or_clarify":
        return actual in {"refuse_or_clarify", "partial"}
    if expected == "warn_conflict":
        return actual == "warn_conflict"
    return False


def _partial_refusal_correct(expected: str, actual: str, partial_or_refusal: bool) -> bool:
    if expected not in {"partial", "refuse_or_clarify"}:
        return True
    return partial_or_refusal or actual in {"partial", "refuse_or_clarify"}


def _conflict_warning_correct(expected: str, actual: str, conflict_warning: bool) -> bool:
    if expected == "warn_conflict":
        return conflict_warning or actual == "warn_conflict"
    return actual != "warn_conflict"


def _preview(text: str, limit: int) -> str:
    return text.replace("\n", " ").strip()[:limit]


def _count_validation_false(rows: list[dict[str, Any]], key: str) -> int:
    count = 0
    for row in rows:
        value = row.get("validation", {}).get(key)
        if value is False:
            count += 1
    return count


def _format_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"
