from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


TemporalType = Literal[
    "valid_time_exact",
    "valid_time_range",
    "transaction_time_only",
    "ambiguous_time",
    "conflict_claim",
    "revision",
    "missing_or_unknown",
]

QuestionCategory = Literal[
    "exact_valid_time",
    "exact_valid_time_retrieval",
    "wrong_year_trap",
    "same_entity_wrong_year_trap",
    "transaction_vs_valid_time",
    "transaction_time_vs_valid_time",
    "broad_window_vs_exact",
    "broad_window_distractor",
    "conflict_or_revision",
    "conflict_detection",
    "cross_domain_dependency",
    "cross_domain_temporal_comparison",
    "missing_evidence",
    "partial_or_insufficient_evidence",
    "ambiguous_temporal_query",
    "ambiguous_time_query",
    "metric_confusion",
    "metric_specific_query",
    "source_family_grounding",
    "source_specific_temporal_query",
]

ExpectedBehavior = Literal[
    "answer",
    "compare",
    "prefer_exact",
    "partial",
    "refuse",
    "conflict_warning",
    "clarify",
]

VALID_TEMPORAL_TYPES = set(TemporalType.__args__)
VALID_CATEGORIES = set(QuestionCategory.__args__)
VALID_BEHAVIORS = set(ExpectedBehavior.__args__)


@dataclass(frozen=True)
class CorpusRow:
    id: str
    domain: str
    source_family: str
    source_file: str | None
    source_kind: str | None
    entity: str
    related_entities: list[str]
    metric_or_claim: str
    value: Any
    unit: str | None
    valid_from: str | None
    valid_to: str | None
    transaction_time: str | None
    temporal_type: TemporalType
    raw_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CorpusRow":
        temporal_type = payload.get("temporal_type")
        if temporal_type not in VALID_TEMPORAL_TYPES:
            raise ValueError(f"Invalid temporal_type for {payload.get('id')}: {temporal_type}")
        return cls(
            id=payload["id"],
            domain=payload["domain"],
            source_family=payload["source_family"],
            source_file=payload["source_file"],
            source_kind=payload["source_kind"],
            entity=payload["entity"],
            related_entities=list(payload.get("related_entities") or []),
            metric_or_claim=payload["metric_or_claim"],
            value=payload.get("value"),
            unit=payload.get("unit"),
            valid_from=payload.get("valid_from"),
            valid_to=payload.get("valid_to"),
            transaction_time=payload.get("transaction_time"),
            temporal_type=temporal_type,
            raw_text=payload["raw_text"],
            metadata=dict(payload.get("metadata") or {}),
            tags=list(payload.get("tags") or []),
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        """Return only evidence fields, never answer-key fields."""
        return {
            "id": self.id,
            "domain": self.domain,
            "source_family": self.source_family,
            "source_file": self.source_file,
            "source_kind": self.source_kind,
            "entity": self.entity,
            "related_entities": self.related_entities,
            "metric_or_claim": self.metric_or_claim,
            "value": self.value,
            "unit": self.unit,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "transaction_time": self.transaction_time,
            "temporal_type": self.temporal_type,
            "raw_text": self.raw_text,
        }


@dataclass(frozen=True)
class QuestionCase:
    id: str
    domain: str
    question: str
    category: QuestionCategory
    expected_behavior: ExpectedBehavior
    expected_evidence_ids: list[str]
    acceptable_evidence_ids: list[str]
    forbidden_evidence_ids: list[str]
    required_facts: list[str]
    forbidden_facts: list[str]
    expected_valid_time: list[str]
    notes: str | None
    synthetic_evidence_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QuestionCase":
        category = payload.get("category")
        behavior = payload.get("expected_behavior")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category for {payload.get('id')}: {category}")
        if behavior not in VALID_BEHAVIORS:
            raise ValueError(f"Invalid expected_behavior for {payload.get('id')}: {behavior}")
        return cls(
            id=payload["id"],
            domain=payload["domain"],
            question=payload["question"],
            category=category,
            expected_behavior=behavior,
            expected_evidence_ids=list(payload.get("expected_evidence_ids") or []),
            acceptable_evidence_ids=list(payload.get("acceptable_evidence_ids") or []),
            forbidden_evidence_ids=list(payload.get("forbidden_evidence_ids") or []),
            required_facts=list(payload.get("required_facts") or []),
            forbidden_facts=list(payload.get("forbidden_facts") or []),
            expected_valid_time=_as_list(payload.get("expected_valid_time")),
            notes=payload.get("notes", ""),
            synthetic_evidence_ids=list(payload.get("synthetic_evidence_ids") or []),
        )


@dataclass(frozen=True)
class ModelAnswer:
    answer: str
    behavior: ExpectedBehavior | str
    cited_evidence_ids: list[str]
    valid_time_used: list[str]
    transaction_time_used_as_valid_time: bool
    conflict_warning: bool
    partial_or_refusal: bool
    clarification_requested: bool
    confidence: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModelAnswer":
        return cls(
            answer=str(payload.get("answer", "")),
            behavior=str(payload.get("behavior", "")),
            cited_evidence_ids=_as_list(payload.get("cited_evidence_ids")),
            valid_time_used=_as_list(payload.get("valid_time_used")),
            transaction_time_used_as_valid_time=_as_bool(payload.get("transaction_time_used_as_valid_time")),
            conflict_warning=_as_bool(payload.get("conflict_warning")),
            partial_or_refusal=_as_bool(payload.get("partial_or_refusal")),
            clarification_requested=_as_bool(payload.get("clarification_requested")),
            confidence=str(payload.get("confidence", "low")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "behavior": self.behavior,
            "cited_evidence_ids": self.cited_evidence_ids,
            "valid_time_used": self.valid_time_used,
            "transaction_time_used_as_valid_time": self.transaction_time_used_as_valid_time,
            "conflict_warning": self.conflict_warning,
            "partial_or_refusal": self.partial_or_refusal,
            "clarification_requested": self.clarification_requested,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class MethodResult:
    method: str
    case_id: str
    answer: ModelAnswer
    selected_evidence_ids: list[str]
    prompt_truncated: bool
    provider_mode: str
    latency_ms: float | None
    validation: dict[str, Any]
    metadata: dict[str, Any]


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_corpus(path: str | Path) -> list[CorpusRow]:
    return [CorpusRow.from_dict(row) for row in load_jsonl(path)]


def load_questions(path: str | Path) -> list[QuestionCase]:
    return [QuestionCase.from_dict(row) for row in load_jsonl(path)]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)
