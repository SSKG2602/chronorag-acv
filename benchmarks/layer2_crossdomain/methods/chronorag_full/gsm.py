from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Iterable

from app.utils.fusion import monotone_temporal_fusion
from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import (
    AdaptedChronoEvidence,
    adapt_corpus,
    retrieve_with_chronorag_adapter,
)
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase
from benchmarks.layer2_crossdomain.temporal_precision import extract_temporal_constraints, score_temporal_precision
from core.retrieval.lexical_bm25 import bm25_search


YEAR_RE = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9./+-]*")

SUPPORTED_DOMAINS = {
    "macro_fred",
    "market_index",
    "sec_submissions",
    "federal_register",
    "github_releases",
}
DOMAIN_ALIASES = {
    "fred": "macro_fred",
    "macro": "macro_fred",
    "market": "market_index",
    "market index": "market_index",
    "sec": "sec_submissions",
    "sec submissions": "sec_submissions",
    "federal register": "federal_register",
    "github": "github_releases",
    "github releases": "github_releases",
}
FORM_RE = re.compile(r"\b(10-K|10-Q|8-K|4/A|4)\b", re.IGNORECASE)


class GSMQueryMode(str, Enum):
    EXACT_VALID_TIME = "exact_valid_time"
    YEAR_REPRESENTATIVE = "year_representative"
    SAME_ENTITY_WRONG_YEAR_TRAP = "same_entity_wrong_year_trap"
    TRANSACTION_TIME_VS_VALID_TIME = "transaction_time_vs_valid_time"
    CONFLICT_DETECTION = "conflict_detection"
    PARTIAL_OR_INSUFFICIENT = "partial_or_insufficient"
    SOURCE_SPECIFIC = "source_specific"
    METRIC_SPECIFIC = "metric_specific"
    CROSS_DOMAIN_COMPARISON = "cross_domain_comparison"
    AMBIGUOUS_TIME = "ambiguous_time"
    BROAD_WINDOW_DISTRACTOR = "broad_window_distractor"
    GENERAL_TEMPORAL = "general_temporal"


@dataclass(frozen=True)
class GSMSlot:
    text: str
    positive_temporal_constraints: list[str] = field(default_factory=list)
    required_domain: str | None = None
    required_entity_terms: list[str] = field(default_factory=list)
    required_metric_terms: list[str] = field(default_factory=list)
    required_form_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GSMPlan:
    enabled: bool
    query_mode: GSMQueryMode
    positive_temporal_constraints: list[str] = field(default_factory=list)
    negative_temporal_constraints: list[str] = field(default_factory=list)
    required_domain: str | None = None
    required_entity_terms: list[str] = field(default_factory=list)
    required_metric_terms: list[str] = field(default_factory=list)
    required_form_terms: list[str] = field(default_factory=list)
    valid_time_required: bool = False
    transaction_time_allowed: bool = False
    needs_conflict_grouping: bool = False
    needs_cross_domain_slots: bool = False
    needs_source_filter: bool = False
    needs_metric_filter: bool = False
    requires_exact_evidence: bool = False
    ambiguous_time: bool = False
    suppress_confident_single_date_answer: bool = False
    answer_policy: str = "answer"
    debug_notes: list[str] = field(default_factory=list)
    slots: list[GSMSlot] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["query_mode"] = self.query_mode.value
        return payload


@dataclass(frozen=True)
class GSMScoredEvidence:
    item: AdaptedChronoEvidence
    score: float
    base_score: float
    filters_applied: tuple[str, ...] = ()


def analyze_gsm_plan(question: str, category: str | None = None, default_domain: str | None = None) -> GSMPlan:
    """Build a deterministic temporal retrieval plan before evidence selection.

    TCC already represents temporal evidence. GSM exists to decide which
    temporal role, year/date, source, metric, and slot constraints retrieval
    should honor before ChronoRAG fusion ranks rows.
    """
    lowered = question.lower()
    debug_notes: list[str] = []
    constraints = _all_temporal_strings(question)
    positive, negative = _split_positive_negative_temporal_constraints(question)
    required_domain = _extract_required_domain(lowered) or _domain_from_category(category, default_domain)
    metric_terms = _extract_metric_terms(question)
    form_terms = _extract_form_terms(question)
    entity_terms = _extract_entity_terms(question)
    slots = _extract_slots(question)

    mode = GSMQueryMode.GENERAL_TEMPORAL
    if _has_ambiguous_time(lowered) or category == "ambiguous_time_query":
        mode = GSMQueryMode.AMBIGUOUS_TIME
    elif "compare" in lowered or category == "cross_domain_temporal_comparison":
        mode = GSMQueryMode.CROSS_DOMAIN_COMPARISON
    elif "conflict" in lowered or "disagree" in lowered or category == "conflict_detection":
        mode = GSMQueryMode.CONFLICT_DETECTION
    elif "exact evidence is missing" in lowered or "do not answer confidently" in lowered or category == "partial_or_insufficient_evidence":
        mode = GSMQueryMode.PARTIAL_OR_INSUFFICIENT
    elif _asks_valid_time_over_transaction(lowered) or category == "transaction_time_vs_valid_time":
        mode = GSMQueryMode.TRANSACTION_TIME_VS_VALID_TIME
    elif _has_negative_temporal_signal(lowered) or category == "same_entity_wrong_year_trap":
        mode = GSMQueryMode.SAME_ENTITY_WRONG_YEAR_TRAP
    elif "using " in lowered and " evidence" in lowered or category == "source_specific_temporal_query":
        mode = GSMQueryMode.SOURCE_SPECIFIC
    elif "answer only" in lowered or category == "metric_specific_query":
        mode = GSMQueryMode.METRIC_SPECIFIC
    elif "broad" in lowered or category == "broad_window_distractor":
        mode = GSMQueryMode.BROAD_WINDOW_DISTRACTOR
    elif constraints and _looks_simple_exact(question):
        mode = GSMQueryMode.EXACT_VALID_TIME

    enabled = mode not in {GSMQueryMode.EXACT_VALID_TIME}
    if not enabled:
        debug_notes.append("Simple exact valid-time query stays on the existing ChronoRAG path to avoid exact-date regression.")

    if mode == GSMQueryMode.SAME_ENTITY_WRONG_YEAR_TRAP and set(positive) & set(negative):
        negative = [item for item in negative if item not in set(positive)]
        debug_notes.append("Negative temporal phrase repeated the target year; not banning the positive year.")

    valid_time_required = mode == GSMQueryMode.TRANSACTION_TIME_VS_VALID_TIME or (
        mode
        in {
            GSMQueryMode.SAME_ENTITY_WRONG_YEAR_TRAP,
            GSMQueryMode.METRIC_SPECIFIC,
            GSMQueryMode.SOURCE_SPECIFIC,
            GSMQueryMode.BROAD_WINDOW_DISTRACTOR,
            GSMQueryMode.CROSS_DOMAIN_COMPARISON,
            GSMQueryMode.PARTIAL_OR_INSUFFICIENT,
        }
        and not _asks_transaction_timing(lowered)
    )
    transaction_time_allowed = _asks_transaction_timing(lowered) and mode != GSMQueryMode.TRANSACTION_TIME_VS_VALID_TIME

    answer_policy = "answer"
    if mode == GSMQueryMode.PARTIAL_OR_INSUFFICIENT:
        answer_policy = "partial_or_refuse_if_exact_missing"
    elif mode == GSMQueryMode.AMBIGUOUS_TIME:
        answer_policy = "clarify_or_partial"
    elif mode == GSMQueryMode.CONFLICT_DETECTION:
        answer_policy = "conflict_warning_only_for_same_valid_time_disagreement"

    if not positive:
        positive = constraints

    return GSMPlan(
        enabled=enabled,
        query_mode=mode,
        positive_temporal_constraints=positive,
        negative_temporal_constraints=negative,
        required_domain=required_domain,
        required_entity_terms=entity_terms,
        required_metric_terms=metric_terms,
        required_form_terms=form_terms,
        valid_time_required=valid_time_required,
        transaction_time_allowed=transaction_time_allowed,
        needs_conflict_grouping=mode == GSMQueryMode.CONFLICT_DETECTION,
        needs_cross_domain_slots=mode == GSMQueryMode.CROSS_DOMAIN_COMPARISON,
        needs_source_filter=mode == GSMQueryMode.SOURCE_SPECIFIC and required_domain is not None,
        needs_metric_filter=mode == GSMQueryMode.METRIC_SPECIFIC or bool(form_terms),
        requires_exact_evidence=mode == GSMQueryMode.PARTIAL_OR_INSUFFICIENT,
        ambiguous_time=mode == GSMQueryMode.AMBIGUOUS_TIME,
        suppress_confident_single_date_answer=mode == GSMQueryMode.AMBIGUOUS_TIME,
        answer_policy=answer_policy,
        debug_notes=debug_notes,
        slots=slots,
    )


def retrieve_with_chronorag_gsm(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> tuple[list[CorpusRow], dict]:
    plan = analyze_gsm_plan(case.question, category=case.category, default_domain=case.domain)
    if not plan.enabled:
        rows, metadata = retrieve_with_chronorag_adapter(case, corpus, top_k)
        return rows, _gsm_metadata(metadata, plan, filters=[], slots=[])

    adapted = adapt_corpus(corpus)
    scored = _score_candidates(case, adapted, plan)
    if plan.needs_cross_domain_slots and plan.slots:
        selected, slot_debug = _select_cross_domain_slots(case, scored, plan, top_k)
    elif plan.needs_conflict_grouping:
        selected, slot_debug = _select_conflict_candidates(scored, plan, top_k)
    else:
        selected = scored[:top_k]
        slot_debug = []

    rows = [item.item.row for item in selected]
    filters = sorted({filter_name for item in selected for filter_name in item.filters_applied})
    metadata = _base_metadata(case, selected, plan)
    return rows, _gsm_metadata(metadata, plan, filters=filters, slots=slot_debug)


def _score_candidates(case: QuestionCase, adapted: list[AdaptedChronoEvidence], plan: GSMPlan) -> list[GSMScoredEvidence]:
    lexical = dict(bm25_search(case.question, [(item.row.id, item.retrieval_text) for item in adapted], top_k=len(adapted)))
    scored: list[GSMScoredEvidence] = []
    for item in adapted:
        base_score = _base_fusion_score(case, item, lexical)
        gsm_score, filters = _apply_gsm_score(item.row, base_score, plan)
        if gsm_score <= -1000.0:
            continue
        scored.append(GSMScoredEvidence(item=item, score=gsm_score, base_score=base_score, filters_applied=tuple(filters)))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored


def _apply_gsm_score(row: CorpusRow, base_score: float, plan: GSMPlan) -> tuple[float, list[str]]:
    score = base_score
    filters: list[str] = []

    if plan.needs_source_filter and plan.required_domain and row.domain != plan.required_domain:
        return -10000.0, ["domain_hard_filter"]
    if plan.required_domain and row.domain == plan.required_domain:
        score += 0.45
        filters.append("domain_boost")

    # Valid time and transaction time are separated because publication/filing
    # timestamps are provenance, not claim-valid time, unless explicitly asked.
    if plan.valid_time_required and not plan.transaction_time_allowed and row.temporal_type == "transaction_time_only":
        if plan.query_mode == GSMQueryMode.TRANSACTION_TIME_VS_VALID_TIME:
            return -10000.0, ["transaction_time_only_banned"]
        score -= 0.65
        filters.append("transaction_time_only_demoted")

    if plan.negative_temporal_constraints and _row_matches_any_temporal(row, plan.negative_temporal_constraints):
        return -10000.0, ["negative_temporal_banned"]
    if plan.positive_temporal_constraints and _row_matches_any_temporal(row, plan.positive_temporal_constraints):
        score += 0.85
        filters.append("positive_temporal_boost")

    if plan.required_entity_terms:
        entity_score = _term_overlap(plan.required_entity_terms, _row_entity_text(row))
        score += 0.50 * entity_score
        if entity_score:
            filters.append("entity_boost")

    if plan.needs_metric_filter or plan.required_metric_terms:
        metric_score = _term_overlap(plan.required_metric_terms, _row_metric_text(row)) if plan.required_metric_terms else 0.0
        if plan.required_metric_terms and metric_score == 0.0:
            score -= 0.50
            filters.append("metric_demoted")
        else:
            score += 0.65 * metric_score
            if metric_score:
                filters.append("metric_boost")

    if plan.required_form_terms:
        if _matches_form(row, plan.required_form_terms):
            score += 0.80
            filters.append("form_boost")
        else:
            return -10000.0, ["form_hard_filter"]

    if plan.query_mode == GSMQueryMode.BROAD_WINDOW_DISTRACTOR and row.temporal_type == "valid_time_exact":
        score += 0.50
        filters.append("exact_valid_time_over_broad_boost")
    if plan.ambiguous_time and row.temporal_type in {"valid_time_range", "ambiguous_time", "missing_or_unknown"}:
        score += 0.20
        filters.append("ambiguous_context_retained")
    return score, filters


def _select_cross_domain_slots(
    case: QuestionCase,
    scored: list[GSMScoredEvidence],
    plan: GSMPlan,
    top_k: int,
) -> tuple[list[GSMScoredEvidence], list[dict]]:
    # Cross-domain comparison uses slots so one semantically dominant side does
    # not consume all top-k evidence before the other side has a chance.
    selected: list[GSMScoredEvidence] = []
    slot_debug: list[dict] = []
    seen: set[str] = set()
    for slot in plan.slots:
        slot_plan = replace(
            plan,
            positive_temporal_constraints=slot.positive_temporal_constraints or plan.positive_temporal_constraints,
            required_domain=slot.required_domain or plan.required_domain,
            required_entity_terms=slot.required_entity_terms,
            required_metric_terms=slot.required_metric_terms,
            required_form_terms=slot.required_form_terms,
            needs_source_filter=False,
        )
        slot_scored = []
        for item in scored:
            slot_score, filters = _apply_gsm_score(item.item.row, item.base_score, slot_plan)
            if slot_score > -1000.0:
                slot_scored.append(
                    GSMScoredEvidence(item=item.item, score=slot_score, base_score=item.base_score, filters_applied=tuple(filters))
                )
        slot_scored.sort(key=lambda item: item.score, reverse=True)
        if slot_scored:
            best = slot_scored[0]
            if best.item.row.id not in seen:
                selected.append(best)
                seen.add(best.item.row.id)
            slot_debug.append({"slot": slot.to_dict(), "selected_evidence_ids": [best.item.row.id]})
    for item in scored:
        if len(selected) >= top_k:
            break
        if item.item.row.id not in seen:
            selected.append(item)
            seen.add(item.item.row.id)
    return selected[:top_k], slot_debug


def _select_conflict_candidates(scored: list[GSMScoredEvidence], plan: GSMPlan, top_k: int) -> tuple[list[GSMScoredEvidence], list[dict]]:
    groups: dict[tuple[str, str, str], list[GSMScoredEvidence]] = defaultdict(list)
    for item in scored:
        row = item.item.row
        valid = row.valid_from or row.valid_to or ""
        if not valid:
            continue
        groups[(_norm(row.entity), _norm(row.metric_or_claim), valid[:10])].append(item)
    conflict_groups = [
        rows
        for rows in groups.values()
        if len({str(item.item.row.value) for item in rows}) > 1 or any(item.item.row.temporal_type == "conflict_claim" for item in rows)
    ]
    if not conflict_groups:
        return scored[:top_k], [{"conflict_group_found": False, "note": "Different valid dates are not treated as conflict."}]
    conflict_groups.sort(key=lambda rows: max(item.score for item in rows), reverse=True)
    selected = sorted(conflict_groups[0], key=lambda item: item.score, reverse=True)[:top_k]
    return selected, [{"conflict_group_found": True, "selected_evidence_ids": [item.item.row.id for item in selected]}]


def _base_fusion_score(case: QuestionCase, item: AdaptedChronoEvidence, lexical: dict[str, float]) -> float:
    relevance = _normalize(lexical.get(item.row.id, 0.0), lexical.values())
    temporal = score_temporal_precision(case, item.row)
    authority = 0.70 if item.row.source_kind in {"filing", "regulation", "guideline", "changelog"} else 0.50
    return monotone_temporal_fusion(
        relevance,
        temporal,
        authority,
        0.0 if item.row.temporal_type != "transaction_time_only" else 0.60,
        0.0,
        {"alpha": 0.50, "beta_time": 0.35, "gamma_authority": 0.10, "delta_age": 0.0, "tx_gamma": 0.25},
    )


def _base_metadata(case: QuestionCase, selected: list[GSMScoredEvidence], plan: GSMPlan) -> dict:
    constraints = extract_temporal_constraints(case.question)
    return {
        "method_family": "chronorag_gsm",
        "base_method_family": "chronorag_full",
        "uses_existing_chronorag_framework": True,
        "adapter_used": True,
        "uses_tcc": True,
        "uses_monotone_temporal_fusion": True,
        "temporal_precision_applied": True,
        "extracted_temporal_constraints": [constraint.to_dict() for constraint in constraints],
        "temporal_granularity": constraints[0].granularity if constraints else "none",
        "temporal_role_detected": constraints[0].temporal_role if constraints else "unknown",
        "selected_scores": {item.item.row.id: round(item.score, 4) for item in selected},
        "selected_base_scores": {item.item.row.id: round(item.base_score, 4) for item in selected},
        "answer_policy": plan.answer_policy,
        "embedding_model": os.getenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        "embedding_dim": int(os.getenv("CHRONORAG_EMBED_DIM", "384")),
    }


def _gsm_metadata(metadata: dict, plan: GSMPlan, filters: list[str], slots: list[dict]) -> dict:
    updated = {
        **metadata,
        "method_family": "chronorag_gsm",
        "base_method_family": metadata.get("base_method_family", metadata.get("method_family", "chronorag_full")),
        "uses_gsm": True,
        "gsm_enabled": plan.enabled,
        "gsm_query_mode": plan.query_mode.value,
        "gsm_plan": plan.to_dict(),
        "gsm_debug_notes": plan.debug_notes,
        "gsm_filters_applied": filters,
        "gsm_slots": slots or [slot.to_dict() for slot in plan.slots],
        "embedding_model": os.getenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        "embedding_dim": int(os.getenv("CHRONORAG_EMBED_DIM", "384")),
    }
    if not plan.enabled:
        updated["gsm_plan"] = {"enabled": False, "query_mode": plan.query_mode.value}
    return updated


def _all_temporal_strings(question: str) -> list[str]:
    values = {match.group(0) for match in ISO_DATE_RE.finditer(question)}
    values.update(match.group(1) for match in YEAR_RE.finditer(question))
    return sorted(values)


def _split_positive_negative_temporal_constraints(question: str) -> tuple[list[str], list[str]]:
    positive: list[str] = []
    negative: list[str] = []
    for match in re.finditer(r"\b(?:not|ignore|rather than|instead of)\s+(\d{4}(?:-\d{2}-\d{2})?)\b", question, re.IGNORECASE):
        negative.append(match.group(1))
    for match in re.finditer(r"\bfor\s+(\d{4}(?:-\d{2}-\d{2})?)\b|\bon\s+(\d{4}-\d{2}-\d{2})\b", question, re.IGNORECASE):
        value = match.group(1) or match.group(2)
        if value:
            positive.append(value)
    if not positive:
        positive = [item for item in _all_temporal_strings(question) if item not in set(negative)]
    return _dedupe(positive), _dedupe(negative)


def _extract_required_domain(lowered: str) -> str | None:
    for domain in SUPPORTED_DOMAINS:
        if f"using {domain} evidence" in lowered or f"using {domain.replace('_', ' ')} evidence" in lowered:
            return domain
    for alias, domain in DOMAIN_ALIASES.items():
        if f"using {alias} evidence" in lowered:
            return domain
    return None


def _domain_from_category(category: str | None, default_domain: str | None) -> str | None:
    if category == "source_specific_temporal_query" and default_domain in SUPPORTED_DOMAINS:
        return default_domain
    return None


def _extract_metric_terms(question: str) -> list[str]:
    patterns = [
        r"answer only (?:the metric\s+)?(.+?)(?:\.|\?|$)",
        r"what valid-time evidence answers\s+(.+?)\s+for\s+\d{4}",
        r"what was .+?\s+(release\s+v[0-9][^\s?.]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            return _tokens(match.group(1))
    lowered = question.lower()
    for phrase in ("index close", "cpi index", "10-year treasury yield", "release", "filing"):
        if phrase in lowered:
            return _tokens(phrase)
    return []


def _extract_form_terms(question: str) -> list[str]:
    return _dedupe(match.group(1).upper() for match in FORM_RE.finditer(question))


def _extract_entity_terms(question: str) -> list[str]:
    cleaned = re.sub(r"\b(?:what|was|for|answer|only|metric|using|evidence|compare|with|in|on|not|should|broad|exact)\b", " ", question, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{4}(?:-\d{2}-\d{2})?\b", " ", cleaned)
    tokens = [token for token in _tokens(cleaned) if token not in {"release", "filing", "index", "close", "cpi", "yield", "period", "recent"}]
    return tokens[:8]


def _extract_slots(question: str) -> list[GSMSlot]:
    match = re.search(r"\bcompare\s+(.+?)\s+with\s+(.+?)(?:\.|\?|$)", question, flags=re.IGNORECASE)
    if not match:
        return []
    slots = []
    for raw in (match.group(1), match.group(2)):
        lowered = raw.lower()
        domain = None
        for alias, candidate in {**{d: d for d in SUPPORTED_DOMAINS}, **DOMAIN_ALIASES}.items():
            if alias in lowered:
                domain = candidate
                break
        slots.append(
            GSMSlot(
                text=raw.strip(),
                positive_temporal_constraints=_all_temporal_strings(raw),
                required_domain=domain,
                required_entity_terms=_extract_entity_terms(raw),
                required_metric_terms=_extract_metric_terms(raw),
                required_form_terms=_extract_form_terms(raw),
            )
        )
    return slots


def _looks_simple_exact(question: str) -> bool:
    lowered = question.lower()
    hard_tokens = ("not ", "ignore ", "rather than", "instead of", "published", "filing time", "publication", "compare", "conflict", "disagree", "around", "recent")
    return bool(_all_temporal_strings(question)) and not any(token in lowered for token in hard_tokens)


def _has_negative_temporal_signal(lowered: str) -> bool:
    return any(token in lowered for token in (" not ", "ignore ", "rather than", "instead of"))


def _asks_valid_time_over_transaction(lowered: str) -> bool:
    return "valid-time evidence" in lowered or "valid time" in lowered or "publication or filing record" in lowered


def _asks_transaction_timing(lowered: str) -> bool:
    return any(token in lowered for token in ("publication year", "published in", "filing time", "release time", "transaction time"))


def _has_ambiguous_time(lowered: str) -> bool:
    return any(token in lowered for token in ("around", "recent period", "industrial era", "broad period"))


def _row_matches_any_temporal(row: CorpusRow, constraints: Iterable[str]) -> bool:
    values = [row.valid_from, row.valid_to, row.transaction_time]
    for constraint in constraints:
        if any(value and str(value).startswith(constraint) for value in values):
            return True
        if len(constraint) == 4 and any(value and str(value).startswith(constraint) for value in values):
            return True
    return False


def _row_entity_text(row: CorpusRow) -> str:
    return " ".join([row.entity, *row.related_entities, row.raw_text])


def _row_metric_text(row: CorpusRow) -> str:
    return " ".join([row.metric_or_claim, str(row.value or ""), row.raw_text])


def _term_overlap(terms: list[str], text: str) -> float:
    if not terms:
        return 0.0
    text_tokens = set(_tokens(text))
    return sum(1 for term in terms if term.lower() in text_tokens or term.lower() in text.lower()) / len(terms)


def _matches_form(row: CorpusRow, forms: list[str]) -> bool:
    text = f"{row.metric_or_claim} {row.value} {row.raw_text}".upper()
    return any(re.search(rf"\b{re.escape(form)}\b", text) for form in forms)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = str(value)
        if key and key not in seen:
            output.append(key)
            seen.add(key)
    return output


def _norm(value: str | None) -> str:
    return " ".join(_tokens(value or ""))


def _normalize(value: float, values) -> float:
    values = list(values)
    if not values:
        return 0.0
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return 1.0 if value else 0.0
    return (value - lo) / (hi - lo)
