from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


@dataclass(frozen=True)
class ValidationResult:
    required_facts_present: bool
    forbidden_facts_absent: bool
    evidence_correct: bool
    forbidden_evidence_absent: bool
    valid_time_correct: bool
    transaction_time_not_misused: bool
    conflict_warning_correct: bool
    partial_refusal_correct: bool
    clarification_correct: bool
    confidence_correct: bool
    behavior_correct: bool
    grounding_correct: bool
    cross_domain_dependency_correct: bool
    overall_pass: bool
    failure_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def normalize_answer(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for key in ("cited_evidence_ids", "valid_time_used"):
        value = normalized.get(key)
        if value is None:
            normalized[key] = []
        elif isinstance(value, str):
            normalized[key] = [value]
        elif isinstance(value, list):
            normalized[key] = [str(item) for item in value]
        else:
            normalized[key] = []
    for key in ("behavior", "confidence"):
        if isinstance(normalized.get(key), str):
            normalized[key] = normalized[key].lower()
    for key in (
        "transaction_time_used_as_valid_time",
        "conflict_warning",
        "partial_or_refusal",
        "clarification_requested",
    ):
        if isinstance(normalized.get(key), str):
            normalized[key] = normalized[key].lower() == "true"
    normalized.setdefault("answer", "")
    normalized.setdefault("behavior", "")
    normalized.setdefault("confidence", "low")
    normalized.setdefault("transaction_time_used_as_valid_time", False)
    normalized.setdefault("conflict_warning", False)
    normalized.setdefault("partial_or_refusal", normalized.get("behavior") in {"partial", "refuse"})
    normalized.setdefault("clarification_requested", normalized.get("behavior") == "clarify")
    return normalized


def validate_answer(
    case: QuestionCase,
    answer_payload: dict[str, Any],
    corpus: list[CorpusRow],
) -> ValidationResult:
    answer = normalize_answer(answer_payload)
    answer_text = str(answer.get("answer", "")).lower()
    cited = set(answer.get("cited_evidence_ids", []))
    corpus_ids = {row.id for row in corpus}
    row_by_id = {row.id: row for row in corpus}
    expected = set(case.expected_evidence_ids)
    acceptable = set(case.acceptable_evidence_ids)
    allowed = expected | acceptable

    required_facts_present = all(fact.lower() in answer_text for fact in case.required_facts)
    forbidden_facts_absent = not any(fact.lower() in answer_text for fact in case.forbidden_facts)
    evidence_correct = _evidence_correct(expected, acceptable, cited)
    forbidden_evidence_absent = not bool(cited & set(case.forbidden_evidence_ids))
    grounding_correct = cited.issubset(corpus_ids)
    valid_time_correct = _valid_time_correct(case, answer, cited, row_by_id)
    transaction_time_not_misused = not bool(answer.get("transaction_time_used_as_valid_time"))
    conflict_warning_correct = case.expected_behavior != "conflict_warning" or bool(answer.get("conflict_warning"))
    partial_refusal_correct = case.expected_behavior not in {"partial", "refuse"} or bool(answer.get("partial_or_refusal"))
    clarification_correct = case.expected_behavior != "clarify" or bool(answer.get("clarification_requested"))
    confidence_correct = _confidence_correct(case, answer)
    behavior_correct = _behavior_correct(case, answer)
    cross_domain_dependency_correct = _cross_domain_dependency_correct(case, cited, row_by_id)

    checks = {
        "required_facts_present": required_facts_present,
        "forbidden_facts_absent": forbidden_facts_absent,
        "evidence_correct": evidence_correct,
        "forbidden_evidence_absent": forbidden_evidence_absent,
        "valid_time_correct": valid_time_correct,
        "transaction_time_not_misused": transaction_time_not_misused,
        "conflict_warning_correct": conflict_warning_correct,
        "partial_refusal_correct": partial_refusal_correct,
        "clarification_correct": clarification_correct,
        "confidence_correct": confidence_correct,
        "behavior_correct": behavior_correct,
        "grounding_correct": grounding_correct,
        "cross_domain_dependency_correct": cross_domain_dependency_correct,
    }
    failure_reasons = [name for name, passed in checks.items() if not passed]
    return ValidationResult(overall_pass=not failure_reasons, failure_reasons=failure_reasons, **checks)


def _valid_time_correct(
    case: QuestionCase,
    answer: dict[str, Any],
    cited: set[str],
    row_by_id: dict[str, CorpusRow],
) -> bool:
    if not case.expected_valid_time:
        return True
    expected_times = [item for item in case.expected_valid_time if item]
    if any(expected in str(item) for expected in expected_times for item in answer.get("valid_time_used", [])):
        return True
    for evidence_id in cited:
        row = row_by_id.get(evidence_id)
        if row and row.valid_from and any(expected in row.valid_from for expected in expected_times):
            return True
    return False


def _evidence_correct(expected: set[str], acceptable: set[str], cited: set[str]) -> bool:
    expected = {item for item in expected if not item.startswith("synthetic:")}
    acceptable = {item for item in acceptable if not item.startswith("synthetic:")}
    if expected:
        return expected.issubset(cited)
    if acceptable:
        return bool(acceptable & cited)
    return True


def _confidence_correct(case: QuestionCase, answer: dict[str, Any]) -> bool:
    confidence = answer.get("confidence")
    if case.expected_behavior in {"partial", "refuse", "clarify"}:
        return confidence in {"low", "medium"}
    return confidence in {"low", "medium", "high"}


def _behavior_correct(case: QuestionCase, answer: dict[str, Any]) -> bool:
    behavior = answer.get("behavior")
    if behavior == case.expected_behavior:
        return True
    if case.expected_behavior == "answer" and behavior in {"answer", "compare", "prefer_exact"}:
        return True
    return False


def _cross_domain_dependency_correct(
    case: QuestionCase,
    cited: set[str],
    row_by_id: dict[str, CorpusRow],
) -> bool:
    if case.category not in {"cross_domain_dependency", "cross_domain_temporal_comparison"}:
        return True
    domains = {row_by_id[item].domain for item in cited if item in row_by_id}
    return len(domains) >= 2
