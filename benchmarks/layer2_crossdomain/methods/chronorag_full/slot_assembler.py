from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9]+")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?(?:rc\d+)?\b", re.IGNORECASE)
COMPARISON_RE = re.compile(r"\b(compare|versus|vs|with|between)\b", re.IGNORECASE)
CONFLICT_RE = re.compile(r"\b(conflict|disagree|disagreement|two\s+sources|contradict|conflicting)\b", re.IGNORECASE)
TRANSACTION_VALID_RE = re.compile(
    r"\b(valid[-\s]?time|valid\s+time|report\s+date|fact\s+time|event\s+date)\b",
    re.IGNORECASE,
)
TRANSACTION_WORD_RE = re.compile(r"\b(filing|publication|transaction|published|filed|release|released)\b", re.IGNORECASE)
SOURCE_FAMILIES = {"macro_fred", "market_index", "sec_submissions", "github_releases", "federal_register"}
METRIC_TERMS = {
    "cpi",
    "index",
    "close",
    "yield",
    "unemployment",
    "filing",
    "release",
    "treasury",
    "rate",
    "4",
    "10",
    "k",
    "q",
    "8",
}


@dataclass(frozen=True)
class QueryIntent:
    query_text: str
    years: set[str] = field(default_factory=set)
    dates: set[str] = field(default_factory=set)
    source_tokens: set[str] = field(default_factory=set)
    metric_tokens: set[str] = field(default_factory=set)
    version_tokens: set[str] = field(default_factory=set)
    is_comparison: bool = False
    is_conflict: bool = False
    is_transaction_valid_time: bool = False
    comparison_slots: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateClass:
    evidence_id: str
    temporal_fit: str = "unknown"
    source_fit: str = "unknown"
    metric_fit: str = "unknown"
    version_fit: str = "unknown"
    comparison_slot: int | None = None
    is_transaction_only: bool = False
    is_exact_target: bool = False
    is_same_neighborhood_wrong_time: bool = False
    is_sibling_version: bool = False


def normalize_text(value: Any) -> str:
    return " ".join(TOKEN_RE.findall(str(value or "").lower().replace("_", " ").replace("-", " ")))


def tokenize(value: Any) -> set[str]:
    return set(TOKEN_RE.findall(str(value or "").lower().replace("_", " ").replace("-", " ")))


def extract_dates(text: str) -> set[str]:
    return set(DATE_RE.findall(text or ""))


def extract_years(text: str) -> set[str]:
    return set(YEAR_RE.findall(text or ""))


def extract_versions(text: str) -> set[str]:
    return {item.lower() for item in VERSION_RE.findall(text or "")}


def row_text(row_or_candidate: Any) -> str:
    row = _row(row_or_candidate)
    return str(_get(row, "raw_text", "retrieval_text", "text", default="") or "")


def row_metadata(row_or_candidate: Any) -> dict:
    row = _row(row_or_candidate)
    metadata = _get(row, "metadata", default={})
    return dict(metadata or {}) if isinstance(metadata, dict) else {}


def row_evidence_id(row_or_candidate: Any) -> str:
    row = _row(row_or_candidate)
    return str(_get(row, "id", "evidence_id", "external_id", default="") or "")


def row_entity(row_or_candidate: Any) -> str:
    return str(_get(_row(row_or_candidate), "entity", default="") or "")


def row_source_family(row_or_candidate: Any) -> str:
    return str(_get(_row(row_or_candidate), "source_family", "domain", default="") or "")


def row_source_file(row_or_candidate: Any) -> str:
    return str(_get(_row(row_or_candidate), "source_file", "document_title", default="") or "")


def row_metric(row_or_candidate: Any) -> str:
    return str(_get(_row(row_or_candidate), "metric_or_claim", "metric", "claim", default="") or "")


def row_valid_from(row_or_candidate: Any) -> str | None:
    value = _get(_row(row_or_candidate), "valid_from", default=None)
    return str(value) if value else None


def row_valid_to(row_or_candidate: Any) -> str | None:
    value = _get(_row(row_or_candidate), "valid_to", default=None)
    return str(value) if value else None


def row_temporal_type(row_or_candidate: Any) -> str:
    return str(_get(_row(row_or_candidate), "temporal_type", default="") or "")


def row_transaction_time(row_or_candidate: Any) -> str | None:
    value = _get(_row(row_or_candidate), "transaction_time", default=None)
    return str(value) if value else None


def candidate_score(candidate: Any) -> float:
    value = _get(candidate, "score", default=0.0)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def classify_query_intent(query_text: str, constraints: Any = None, candidates: list[Any] | None = None) -> QueryIntent:
    text = query_text or ""
    years = extract_years(text)
    dates = extract_dates(text)
    versions = extract_versions(text)
    query_tokens = tokenize(text)
    source_tokens = {family for family in SOURCE_FAMILIES if set(family.split("_")).issubset(query_tokens)}
    metric_tokens = set(query_tokens & METRIC_TERMS)
    for candidate in candidates or []:
        metric_tokens.update(query_tokens & tokenize(row_metric(candidate)))

    is_conflict = bool(CONFLICT_RE.search(text))
    is_comparison = _is_comparison_query(text, years, candidates or [])
    is_transaction_valid_time = bool(TRANSACTION_VALID_RE.search(text)) or (
        bool(re.search(r"\bfor\s+(?:18|19|20)\d{2}\b", text, re.IGNORECASE)) and bool(TRANSACTION_WORD_RE.search(text))
    )
    slots = _comparison_slots(text, is_comparison, candidates or [])
    return QueryIntent(
        query_text=text,
        years=years,
        dates=dates,
        source_tokens=source_tokens,
        metric_tokens=metric_tokens,
        version_tokens=versions,
        is_comparison=is_comparison,
        is_conflict=is_conflict,
        is_transaction_valid_time=is_transaction_valid_time,
        comparison_slots=slots,
    )


def classify_candidate(candidate: Any, intent: QueryIntent) -> CandidateClass:
    evidence_id = row_evidence_id(candidate)
    temporal_type = row_temporal_type(candidate)
    valid_from = row_valid_from(candidate)
    valid_year = valid_from[:4] if valid_from else None
    is_transaction_only = temporal_type == "transaction_time_only" or (not valid_from and bool(row_transaction_time(candidate)))
    temporal_fit = "unknown"
    is_exact_target = False
    if is_transaction_only:
        temporal_fit = "transaction_only"
    elif valid_from and intent.dates:
        if valid_from in intent.dates:
            temporal_fit = "exact_target"
            is_exact_target = True
        elif valid_year and valid_year in {date[:4] for date in intent.dates}:
            temporal_fit = "same_year_wrong_date"
        elif _near_query_year(valid_year, intent.years):
            temporal_fit = "nearby"
    elif valid_year and intent.years:
        if valid_year in intent.years:
            temporal_fit = "year_match"
            is_exact_target = True
        elif _near_query_year(valid_year, intent.years):
            temporal_fit = "nearby"

    source_fit = _source_fit(candidate, intent)
    version_fit = _version_fit(candidate, intent)
    metric_fit = _metric_fit(candidate, intent, version_fit)
    comparison_slot = _best_comparison_slot(candidate, intent)
    is_same_neighborhood_wrong_time = temporal_fit == "same_year_wrong_date" and _query_mentions_candidate_neighborhood(candidate, intent)
    is_sibling_version = version_fit == "sibling"
    return CandidateClass(
        evidence_id=evidence_id,
        temporal_fit=temporal_fit,
        source_fit=source_fit,
        metric_fit=metric_fit,
        version_fit=version_fit,
        comparison_slot=comparison_slot,
        is_transaction_only=is_transaction_only,
        is_exact_target=is_exact_target,
        is_same_neighborhood_wrong_time=is_same_neighborhood_wrong_time,
        is_sibling_version=is_sibling_version,
    )


def assemble_top_k(candidates: list[Any], intent: QueryIntent, top_k: int) -> tuple[list[Any], dict[str, Any]]:
    if top_k <= 0:
        return [], _report(intent, [], {}, [], {}, [], [])

    ordered = sorted(candidates, key=candidate_score, reverse=True)
    classes = {row_evidence_id(candidate): classify_candidate(candidate, intent) for candidate in ordered}
    by_id = {row_evidence_id(candidate): candidate for candidate in ordered if row_evidence_id(candidate)}
    selected: list[Any] = []
    selected_ids: set[str] = set()
    slot_filled: list[str] = []
    slot_misses: list[str] = []

    def add(candidate: Any | None, slot_name: str) -> None:
        if candidate is None or len(selected) >= top_k:
            if candidate is None:
                slot_misses.append(slot_name)
            return
        evidence_id = row_evidence_id(candidate)
        if not evidence_id or evidence_id in selected_ids:
            return
        selected.append(candidate)
        selected_ids.add(evidence_id)
        slot_filled.append(slot_name)

    if intent.is_comparison:
        for index, _slot in enumerate(intent.comparison_slots):
            add(_best_for_slot(ordered, classes, intent, index, selected_ids), f"comparison_slot_{index}")

    if intent.is_transaction_valid_time:
        add(_best_valid_time_candidate(ordered, classes, selected_ids), "transaction_valid_time")

    if intent.dates or intent.years:
        add(_best_exact_target(ordered, classes, selected_ids, intent), "exact_temporal_target")

    if intent.version_tokens:
        add(_best_version_candidate(ordered, classes, selected_ids), "exact_version")

    if intent.is_conflict:
        primary = _best_exact_target(ordered, classes, selected_ids, intent) or _best_version_candidate(ordered, classes, selected_ids)
        add(primary, "conflict_primary")
        add(_best_conflict_side(ordered, classes, selected_ids), "conflict_side")

    suppressed_ids, suppression_reasons = _suppression_map(ordered, classes, selected_ids, intent)
    for candidate in ordered:
        if len(selected) >= top_k:
            break
        evidence_id = row_evidence_id(candidate)
        if not evidence_id or evidence_id in selected_ids or evidence_id in suppressed_ids:
            continue
        add(candidate, "score_filler")

    for candidate in ordered:
        if len(selected) >= top_k:
            break
        evidence_id = row_evidence_id(candidate)
        if not evidence_id or evidence_id in selected_ids:
            continue
        if _forbidden_like(classes[evidence_id]):
            continue
        add(candidate, "suppressed_fallback")

    return selected, _report(intent, selected, classes, slot_filled, suppression_reasons, sorted(suppressed_ids), slot_misses)


def audit_conflict_data_contract(
    questions_path: str | Path,
    corpus_path: str | Path,
    output_json: str | Path,
    output_md: str | Path,
) -> dict[str, Any]:
    questions = _read_jsonl(Path(questions_path))
    corpus_ids = {row["id"] for row in _read_jsonl(Path(corpus_path))}
    cases = []
    missing_total = 0
    present_total = 0
    for question in questions:
        if question.get("category") != "conflict_detection":
            continue
        ids = list(question.get("expected_evidence_ids") or []) + list(question.get("acceptable_evidence_ids") or [])
        present = [item for item in ids if item in corpus_ids]
        missing = [item for item in ids if item not in corpus_ids]
        present_total += len(present)
        missing_total += len(missing)
        cases.append(
            {
                "case_id": question.get("id"),
                "question": question.get("question"),
                "present_ids": present,
                "missing_ids": missing,
            }
        )
    payload = {
        "questions_path": str(questions_path),
        "corpus_path": str(corpus_path),
        "conflict_case_count": len(cases),
        "present_id_count": present_total,
        "missing_id_count": missing_total,
        "cases": cases,
    }
    Path(output_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(output_md).write_text(_render_conflict_contract_md(payload), encoding="utf-8")
    return payload


def _best_for_slot(
    candidates: list[Any],
    classes: dict[str, CandidateClass],
    intent: QueryIntent,
    slot_index: int,
    selected_ids: set[str],
) -> Any | None:
    matches = [
        candidate
        for candidate in candidates
        if row_evidence_id(candidate) not in selected_ids
        and classes[row_evidence_id(candidate)].comparison_slot == slot_index
        and classes[row_evidence_id(candidate)].temporal_fit in {"exact_target", "year_match"}
    ]
    if not matches:
        return None
    slot = intent.comparison_slots[slot_index]
    return max(matches, key=lambda candidate: (_slot_match_score(candidate, slot), candidate_score(candidate)))


def _best_valid_time_candidate(candidates: list[Any], classes: dict[str, CandidateClass], selected_ids: set[str]) -> Any | None:
    matches = [
        candidate
        for candidate in candidates
        if row_evidence_id(candidate) not in selected_ids
        and not classes[row_evidence_id(candidate)].is_transaction_only
        and classes[row_evidence_id(candidate)].temporal_fit in {"exact_target", "year_match"}
    ]
    return _best_preferred(matches, classes)


def _best_exact_target(candidates: list[Any], classes: dict[str, CandidateClass], selected_ids: set[str], intent: QueryIntent) -> Any | None:
    matches = [
        candidate
        for candidate in candidates
        if row_evidence_id(candidate) not in selected_ids and classes[row_evidence_id(candidate)].is_exact_target
    ]
    if not matches and intent.dates:
        matches = [
            candidate
            for candidate in candidates
            if row_evidence_id(candidate) not in selected_ids and classes[row_evidence_id(candidate)].temporal_fit == "year_match"
        ]
    return _best_preferred(matches, classes)


def _best_version_candidate(candidates: list[Any], classes: dict[str, CandidateClass], selected_ids: set[str]) -> Any | None:
    matches = [
        candidate
        for candidate in candidates
        if row_evidence_id(candidate) not in selected_ids and classes[row_evidence_id(candidate)].version_fit == "exact"
    ]
    return _best_preferred(matches, classes)


def _best_conflict_side(candidates: list[Any], classes: dict[str, CandidateClass], selected_ids: set[str]) -> Any | None:
    matches = [
        candidate
        for candidate in candidates
        if row_evidence_id(candidate) not in selected_ids and _conflict_side_like(candidate)
    ]
    return _best_preferred(matches, classes)


def _best_preferred(candidates: list[Any], classes: dict[str, CandidateClass]) -> Any | None:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda candidate: (
            classes[row_evidence_id(candidate)].source_fit == "exact",
            classes[row_evidence_id(candidate)].metric_fit == "exact",
            classes[row_evidence_id(candidate)].version_fit == "exact",
            candidate_score(candidate),
        ),
    )


def _suppression_map(
    candidates: list[Any],
    classes: dict[str, CandidateClass],
    selected_ids: set[str],
    intent: QueryIntent,
) -> tuple[set[str], dict[str, list[str]]]:
    suppressed: set[str] = set()
    reasons: dict[str, list[str]] = {}
    exact_neighborhoods = {
        _neighborhood_key(candidate)
        for candidate in candidates
        if classes[row_evidence_id(candidate)].is_exact_target
    }
    valid_time_exists = any(not classes[row_evidence_id(candidate)].is_transaction_only for candidate in candidates)
    exact_version_exists = any(classes[row_evidence_id(candidate)].version_fit == "exact" for candidate in candidates)
    for candidate in candidates:
        evidence_id = row_evidence_id(candidate)
        if not evidence_id or evidence_id in selected_ids:
            continue
        classification = classes[evidence_id]
        candidate_reasons: list[str] = []
        if _neighborhood_key(candidate) in exact_neighborhoods and classification.is_same_neighborhood_wrong_time:
            candidate_reasons.append("same_neighborhood_wrong_time")
        if exact_version_exists and classification.is_sibling_version:
            candidate_reasons.append("sibling_version")
        if intent.source_tokens and classification.source_fit == "mismatch":
            candidate_reasons.append("source_mismatch")
        if (intent.metric_tokens or intent.version_tokens) and classification.metric_fit == "mismatch":
            candidate_reasons.append("metric_mismatch")
        if intent.is_transaction_valid_time and valid_time_exists and classification.is_transaction_only:
            candidate_reasons.append("transaction_only")
        if candidate_reasons:
            suppressed.add(evidence_id)
            reasons[evidence_id] = candidate_reasons
    return suppressed, reasons


def _forbidden_like(classification: CandidateClass) -> bool:
    return (
        classification.is_transaction_only
        or classification.is_same_neighborhood_wrong_time
        or classification.is_sibling_version
        or classification.source_fit == "mismatch"
        or classification.metric_fit == "mismatch"
    )


def _is_comparison_query(query_text: str, years: set[str], candidates: list[Any]) -> bool:
    if not COMPARISON_RE.search(query_text):
        return False
    if len(years) >= 2 or len(extract_dates(query_text)) >= 2:
        return True
    entities = {normalize_text(row_entity(candidate)) for candidate in candidates if _query_overlap(query_text, row_entity(candidate))}
    sources = {row_source_family(candidate) for candidate in candidates if _query_overlap(query_text, row_source_family(candidate))}
    return len(entities | sources) >= 2


def _comparison_slots(query_text: str, is_comparison: bool, candidates: list[Any]) -> list[dict[str, Any]]:
    if not is_comparison:
        return []
    side_texts = [part.strip() for part in re.split(r"\bcompare\b|\bwith\b|\bvs\b|\bversus\b|\band\b", query_text, flags=re.IGNORECASE) if part.strip()]
    slots = [_slot_from_text(text) for text in side_texts if _slot_has_signal(text)]
    if len(slots) >= 2:
        return slots[:2]
    grouped = sorted(
        _candidate_slot_groups(candidates, query_text).values(),
        key=lambda item: (-item["score"], item["side_text"]),
    )
    return grouped[:2]


def _slot_from_text(text: str) -> dict[str, Any]:
    return {
        "side_text": text,
        "years": extract_years(text),
        "dates": extract_dates(text),
        "versions": extract_versions(text),
        "tokens": tokenize(text),
    }


def _slot_has_signal(text: str) -> bool:
    return bool(extract_years(text) or extract_dates(text) or extract_versions(text) or len(tokenize(text)) >= 2)


def _candidate_slot_groups(candidates: list[Any], query_text: str) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        valid_from = row_valid_from(candidate) or ""
        year = valid_from[:4]
        key = (normalize_text(row_entity(candidate)), normalize_text(row_source_family(candidate)), normalize_text(row_metric(candidate)), year)
        score = _query_relevance(query_text, candidate) + candidate_score(candidate)
        if key not in groups or score > groups[key]["score"]:
            groups[key] = {
                "side_text": " ".join(part for part in key if part),
                "years": {year} if year else set(),
                "dates": {valid_from} if DATE_RE.fullmatch(valid_from) else set(),
                "versions": extract_versions(row_text(candidate) + " " + row_metric(candidate)),
                "tokens": tokenize(" ".join(key)),
                "score": score,
            }
    return groups


def _best_comparison_slot(candidate: Any, intent: QueryIntent) -> int | None:
    if not intent.comparison_slots:
        return None
    best_index: int | None = None
    best_score = 0.0
    for index, slot in enumerate(intent.comparison_slots):
        score = _slot_match_score(candidate, slot)
        if score > best_score:
            best_index = index
            best_score = score
    return best_index if best_score >= 2 else None


def _slot_match_score(candidate: Any, slot: dict[str, Any]) -> int:
    candidate_tokens = _candidate_tokens(candidate)
    slot_tokens = set(slot.get("tokens") or set())
    valid_from = row_valid_from(candidate) or ""
    candidate_year = valid_from[:4]
    candidate_versions = extract_versions(row_text(candidate) + " " + row_metric(candidate))
    score = len(candidate_tokens & slot_tokens)
    entity_tokens = tokenize(row_entity(candidate))
    if entity_tokens and entity_tokens <= slot_tokens:
        score += 6
    if candidate_year and candidate_year in set(slot.get("years") or set()):
        score += 4
    if valid_from and valid_from in set(slot.get("dates") or set()):
        score += 5
    if candidate_versions & set(slot.get("versions") or set()):
        score += 5
    return score


def _source_fit(candidate: Any, intent: QueryIntent) -> str:
    if not intent.source_tokens:
        return "unknown"
    fields = {row_source_family(candidate), row_source_file(candidate), str(_get(_row(candidate), "source_kind", default="")), str(_get(_row(candidate), "domain", default=""))}
    normalized_fields = {value for field in fields for value in {field, normalize_text(field).replace(" ", "_")}}
    if intent.source_tokens & normalized_fields:
        return "exact"
    return "mismatch"


def _version_fit(candidate: Any, intent: QueryIntent) -> str:
    if not intent.version_tokens:
        return "unknown"
    candidate_versions = extract_versions(row_metric(candidate) + " " + row_text(candidate) + " " + str(_get(_row(candidate), "value", default="")))
    if candidate_versions & intent.version_tokens:
        return "exact"
    if any(_sibling_version(query_version, candidate_version) for query_version in intent.version_tokens for candidate_version in candidate_versions):
        return "sibling"
    return "mismatch" if candidate_versions else "unknown"


def _metric_fit(candidate: Any, intent: QueryIntent, version_fit: str) -> str:
    if version_fit == "exact":
        return "exact"
    if version_fit == "sibling":
        return "sibling"
    if not intent.metric_tokens:
        return "unknown"
    metric_tokens = tokenize(row_metric(candidate))
    if not metric_tokens:
        return "unknown"
    overlap = len(intent.metric_tokens & metric_tokens) / max(1, len(intent.metric_tokens))
    if overlap >= 0.5:
        return "exact"
    return "mismatch"


def _near_query_year(candidate_year: str | None, query_years: set[str]) -> bool:
    if not candidate_year or not query_years:
        return False
    try:
        year = int(candidate_year)
        return any(abs(year - int(query_year)) <= 1 for query_year in query_years)
    except ValueError:
        return False


def _query_mentions_candidate_neighborhood(candidate: Any, intent: QueryIntent) -> bool:
    query_tokens = tokenize(intent.query_text)
    neighborhood_tokens = tokenize(row_entity(candidate)) | tokenize(row_source_family(candidate)) | tokenize(row_metric(candidate))
    return bool(query_tokens & neighborhood_tokens)


def _query_overlap(query_text: str, value: str) -> bool:
    tokens = tokenize(value)
    return bool(tokens and tokens <= tokenize(query_text))


def _query_relevance(query_text: str, candidate: Any) -> float:
    query_tokens = tokenize(query_text)
    candidate_tokens = _candidate_tokens(candidate)
    return len(query_tokens & candidate_tokens) / max(1, len(query_tokens))


def _candidate_tokens(candidate: Any) -> set[str]:
    return tokenize(" ".join([row_entity(candidate), row_source_family(candidate), row_source_file(candidate), row_metric(candidate), row_text(candidate)]))


def _neighborhood_key(candidate: Any) -> tuple[str, str, str]:
    return (normalize_text(row_entity(candidate)), normalize_text(row_source_family(candidate)), normalize_text(row_metric(candidate)))


def _sibling_version(left: str, right: str) -> bool:
    left_parts = left.lower().lstrip("v").split(".")
    right_parts = right.lower().lstrip("v").split(".")
    return bool(left_parts and right_parts and left_parts[0] == right_parts[0])


def _conflict_side_like(candidate: Any) -> bool:
    text = normalize_text(" ".join([row_evidence_id(candidate), row_text(candidate), row_metric(candidate)]))
    return "synthetic conflict" in text or "conflict" in text or "disagree" in text


def _report(
    intent: QueryIntent,
    selected: list[Any],
    classes: dict[str, CandidateClass],
    slot_filled: list[str],
    suppression_reasons: dict[str, list[str]],
    suppressed_ids: list[str],
    slot_misses: list[str],
) -> dict[str, Any]:
    return {
        "intent": _intent_to_dict(intent),
        "selected_evidence_ids": [row_evidence_id(candidate) for candidate in selected],
        "slot_filled": slot_filled,
        "slot_misses": slot_misses,
        "suppressed_evidence_ids": suppressed_ids,
        "suppression_reasons": suppression_reasons,
        "classifications": {evidence_id: asdict(classification) for evidence_id, classification in classes.items()},
    }


def _intent_to_dict(intent: QueryIntent) -> dict[str, Any]:
    payload = asdict(intent)
    for key in ("years", "dates", "source_tokens", "metric_tokens", "version_tokens"):
        payload[key] = sorted(payload[key])
    for slot in payload["comparison_slots"]:
        for key in ("years", "dates", "versions", "tokens"):
            if isinstance(slot.get(key), set):
                slot[key] = sorted(slot[key])
    return payload


def _row(row_or_candidate: Any) -> Any:
    if isinstance(row_or_candidate, dict):
        return row_or_candidate.get("row", row_or_candidate)
    return getattr(row_or_candidate, "row", row_or_candidate)


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _render_conflict_contract_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Conflict Data Contract Audit",
        "",
        f"Conflict cases: {payload['conflict_case_count']}",
        f"Present IDs: {payload['present_id_count']}",
        f"Missing IDs: {payload['missing_id_count']}",
        "",
        "| Case | Present IDs | Missing IDs | Question |",
        "|---|---|---|---|",
    ]
    for case in payload["cases"]:
        lines.append(
            f"| {case['case_id']} | {_join(case['present_ids'])} | {_join(case['missing_ids'])} | {str(case['question']).replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def _join(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "-"
