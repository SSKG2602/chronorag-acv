from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from benchmarks.layer2_crossdomain.schemas import CorpusRow
from benchmarks.layer2_crossdomain.temporal_precision import TemporalConstraint
from benchmarks.layer2_crossdomain.methods.chronorag_full.slot_assembler import assemble_top_k, classify_query_intent


TOKEN_RE = re.compile(r"[a-z0-9]+")
COMPARISON_CUE_RE = re.compile(r"\b(compare|versus|vs|difference|between|both|higher|lower|before|after)\b", re.IGNORECASE)
CONFLICT_CUE_RE = re.compile(r"\b(conflict|conflicting|disagree|disagreement|two\s+sources|surface\s+both)\b", re.IGNORECASE)
EXPLICIT_VALID_TIME_RE = re.compile(
    r"\b(valid[-\s]?time|event\s+time|effective|as[-\s]?of|report\s+date|for\s+date)\b",
    re.IGNORECASE,
)
TRANSACTION_TARGET_RE = re.compile(
    r"\b(filed|filing|published|publication|released|release|transaction[-\s]?time|ingested|observed)\b",
    re.IGNORECASE,
)
TRANSACTION_ROLES = {"transaction_time", "publication_time", "filing_time", "release_time"}
SOURCE_GENERIC_TOKENS = {"data", "document", "evidence", "file", "record", "source"}


@dataclass(frozen=True)
class AblationConfig:
    disable_tcc: bool = False
    disable_temporal_precision: bool = False
    disable_transaction_role: bool = False
    disable_source_metric: bool = False
    disable_slot_assembler: bool = False
    score_only: bool = False

    def effective(self) -> "AblationConfig":
        if not self.score_only:
            return self
        return AblationConfig(
            disable_tcc=self.disable_tcc,
            disable_temporal_precision=True,
            disable_transaction_role=True,
            disable_source_metric=True,
            disable_slot_assembler=True,
            score_only=True,
        )


def finalize_chronorag_evidence(
    candidates: list[Any],
    constraints: list[TemporalConstraint],
    query_text: str,
    top_k: int,
    ablation_config: AblationConfig | None = None,
) -> tuple[list[Any], dict[str, object]]:
    """Apply a small final evidence-selection pass after temporal fusion."""
    config = (ablation_config or AblationConfig()).effective()
    adjusted = list(candidates)
    exact_count = 0
    transaction_count = 0
    source_metric_count = 0

    if not config.disable_temporal_precision:
        adjusted, exact_count = _apply_exact_valid_time_cleanup(adjusted, constraints, query_text)
    if not config.disable_transaction_role:
        adjusted, transaction_count = _apply_transaction_role_cleanup(adjusted, constraints, query_text)
    if not config.disable_source_metric:
        adjusted, source_metric_count = _apply_source_metric_adjustments(adjusted, query_text)

    adjusted.sort(key=lambda item: item.score, reverse=True)
    assembler_pool = adjusted[: min(len(adjusted), 200)]
    intent = classify_query_intent(query_text=query_text, constraints=constraints, candidates=assembler_pool)
    if config.disable_slot_assembler:
        selected = assembler_pool[:top_k]
        slot_report = {
            "slot_assembler_disabled": True,
            "selected_evidence_ids": [item.row.id for item in selected],
        }
    else:
        selected, slot_report = assemble_top_k(assembler_pool, intent, top_k)

    metadata = {
        "retrieval_finalization_ran": True,
        "exact_time_cleanup_applied_count": exact_count,
        "transaction_role_cleanup_applied_count": transaction_count,
        "source_metric_adjustment_applied_count": source_metric_count,
        "diversified_selection_applied": intent.is_comparison or intent.is_conflict,
        "slot_aware_assembly_applied": not config.disable_slot_assembler,
        "slot_assembly_report": slot_report,
        "ablation_config": {
            "disable_tcc": config.disable_tcc,
            "disable_temporal_precision": config.disable_temporal_precision,
            "disable_transaction_role": config.disable_transaction_role,
            "disable_source_metric": config.disable_source_metric,
            "disable_slot_assembler": config.disable_slot_assembler,
            "score_only": config.score_only,
        },
        "selected_scores_after_finalization": {item.row.id: round(item.score, 4) for item in selected},
    }
    return selected, metadata


def _apply_exact_valid_time_cleanup(
    candidates: list[Any],
    constraints: list[TemporalConstraint],
    query_text: str,
) -> tuple[list[Any], int]:
    constraint = _single_positive_exact_constraint(constraints)
    if constraint is None or _should_diversify(query_text):
        return candidates, 0

    exact_neighborhoods = {
        _neighborhood_key(item.row)
        for item in candidates
        if _row_matches_constraint_valid_time(item.row, constraint)
    }
    exact_neighborhoods.discard(())
    if not exact_neighborhoods:
        return candidates, 0

    updated: list[Any] = []
    changed = 0
    for item in candidates:
        row = item.row
        score = item.score
        if _row_matches_constraint_valid_time(row, constraint):
            new_score = min(1.0, score + 0.04)
        elif _has_valid_time(row) and _neighborhood_key(row) in exact_neighborhoods:
            new_score = score * 0.18
        else:
            new_score = score
        if new_score != score:
            changed += 1
        updated.append(_with_score(item, new_score))
    return updated, changed


def _apply_transaction_role_cleanup(
    candidates: list[Any],
    constraints: list[TemporalConstraint],
    query_text: str,
) -> tuple[list[Any], int]:
    if not _query_needs_valid_time(query_text, constraints) or _query_targets_transaction_time(query_text, constraints):
        return candidates, 0
    if not any(_has_valid_time(item.row) for item in candidates):
        return candidates, 0

    updated: list[Any] = []
    changed = 0
    for item in candidates:
        row = item.row
        score = item.score
        if row.temporal_type == "transaction_time_only":
            new_score = score * 0.10
        elif row.transaction_time and not row.valid_from:
            new_score = score * 0.45
        else:
            new_score = score
        if new_score != score:
            changed += 1
        updated.append(_with_score(item, new_score))
    return updated, changed


def _apply_source_metric_adjustments(candidates: list[Any], query_text: str) -> tuple[list[Any], int]:
    query_tokens = _tokens(query_text)
    if not query_tokens:
        return candidates, 0

    source_intent = any(_source_match_strength(item.row, query_tokens) >= 0.50 for item in candidates)
    metric_intent = "metric" in query_tokens or any(_metric_match_strength(item.row, query_tokens) >= 0.45 for item in candidates)

    updated: list[Any] = []
    changed = 0
    for item in candidates:
        row = item.row
        score = item.score
        if score == 0.0:
            updated.append(item)
            continue
        multiplier = 1.0
        delta = 0.0

        source_strength = _source_match_strength(row, query_tokens)
        if source_strength >= 0.50:
            delta += 0.06 * source_strength
        elif source_intent and _has_source_fields(row):
            multiplier *= 0.92

        metric_strength = _metric_match_strength(row, query_tokens)
        if metric_strength >= 0.45:
            delta += 0.08 * metric_strength
        elif metric_intent and row.metric_or_claim:
            multiplier *= 0.90

        new_score = (score * multiplier) + delta
        if new_score != score:
            changed += 1
        updated.append(_with_score(item, new_score))
    return updated, changed


def _select_diversified_topk(candidates: list[Any], top_k: int, query_text: str) -> list[Any]:
    if top_k <= 0:
        return []
    if not _should_diversify(query_text):
        return candidates[:top_k]

    primary_groups = {_primary_diversity_group(item.row) for item in candidates}
    primary_groups.discard(())
    group_fn = _primary_diversity_group if len(primary_groups) > 1 else _temporal_diversity_group

    selected: list[Any] = []
    seen_groups: set[tuple[str, ...]] = set()
    for item in candidates:
        group = group_fn(item.row)
        if group and group in seen_groups:
            continue
        selected.append(item)
        if group:
            seen_groups.add(group)
        if len(selected) == top_k:
            return selected

    selected_ids = {item.row.id for item in selected}
    for item in candidates:
        if item.row.id in selected_ids:
            continue
        selected.append(item)
        if len(selected) == top_k:
            break
    return selected


def _single_positive_exact_constraint(constraints: list[TemporalConstraint]) -> TemporalConstraint | None:
    positive = [
        item
        for item in constraints
        if item.polarity != "negative" and not item.ambiguous_parse and item.granularity in {"day", "hour", "minute", "second"}
    ]
    return positive[0] if len(positive) == 1 else None


def _row_matches_constraint_valid_time(row: CorpusRow, constraint: TemporalConstraint) -> bool:
    row_start = _parse_isoish(row.valid_from)
    row_end = _parse_isoish(row.valid_to or row.valid_from)
    constraint_start = _parse_isoish(constraint.normalized_start)
    constraint_end = _parse_isoish(constraint.normalized_end) or constraint_start
    if not row_start or not row_end or not constraint_start or not constraint_end:
        return False
    if constraint.granularity in {"hour", "minute", "second"} and "T" in constraint.normalized_start:
        return row_start == constraint_start and row_end == constraint_end
    return row_start.date() == constraint_start.date() and row_end.date() == constraint_end.date()


def _query_needs_valid_time(query_text: str, constraints: list[TemporalConstraint]) -> bool:
    if EXPLICIT_VALID_TIME_RE.search(query_text):
        return True
    positive_roles = [item.temporal_role for item in constraints if item.polarity != "negative"]
    return bool(positive_roles) and any(role == "valid_time" for role in positive_roles)


def _query_targets_transaction_time(query_text: str, constraints: list[TemporalConstraint]) -> bool:
    if EXPLICIT_VALID_TIME_RE.search(query_text):
        return False
    positive_roles = [item.temporal_role for item in constraints if item.polarity != "negative"]
    if positive_roles and all(role in TRANSACTION_ROLES for role in positive_roles):
        return True
    return bool(TRANSACTION_TARGET_RE.search(query_text)) and not any(role == "valid_time" for role in positive_roles)


def _should_diversify(query_text: str) -> bool:
    return bool(COMPARISON_CUE_RE.search(query_text) or CONFLICT_CUE_RE.search(query_text))


def _source_match_strength(row: CorpusRow, query_tokens: set[str]) -> float:
    fields = [
        row.source_family,
        row.source_kind,
        row.domain,
        Path(row.source_file).stem if row.source_file else None,
    ]
    return max((_field_overlap(query_tokens, _tokens(field or "") - SOURCE_GENERIC_TOKENS) for field in fields), default=0.0)


def _metric_match_strength(row: CorpusRow, query_tokens: set[str]) -> float:
    return _field_overlap(query_tokens, _tokens(row.metric_or_claim or ""))


def _field_overlap(query_tokens: set[str], field_tokens: set[str]) -> float:
    if not field_tokens:
        return 0.0
    return len(query_tokens & field_tokens) / len(field_tokens)


def _has_source_fields(row: CorpusRow) -> bool:
    return bool(row.source_family or row.source_kind or row.domain or row.source_file)


def _has_valid_time(row: CorpusRow) -> bool:
    return bool(row.valid_from) and row.temporal_type != "transaction_time_only"


def _neighborhood_key(row: CorpusRow) -> tuple[str, ...]:
    return (_normalize(row.entity), _normalize(row.source_family), _normalize(row.metric_or_claim))


def _primary_diversity_group(row: CorpusRow) -> tuple[str, ...]:
    return (_normalize(row.entity), _normalize(row.source_family or row.source_file), _normalize(row.metric_or_claim))


def _temporal_diversity_group(row: CorpusRow) -> tuple[str, ...]:
    return (_normalize(row.valid_from), _normalize(row.valid_to or row.valid_from), _normalize(row.transaction_time))


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower().replace("_", " ").replace("-", " ")))


def _normalize(value: object) -> str:
    return " ".join(sorted(_tokens(str(value or ""))))


def _parse_isoish(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _with_score(item: Any, score: float) -> Any:
    return replace(item, score=round(max(0.0, min(1.0, score)), 6))
