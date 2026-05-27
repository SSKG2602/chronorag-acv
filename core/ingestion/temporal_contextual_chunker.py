"""Temporal Contextual Chunking for ChronoRAG ingestion.

The chunker keeps source evidence and retrieval context separate.  `raw_text`
is the truth anchor used for attribution and answer grounding.  `retrieval_text`
adds a compact context prefix so BM25/vector search can recover the chunk without
pretending that inherited context is quoted evidence.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.utils.time_windows import TimeWindow, make_window, parse_date
from core.ingestion.temporal_precision import TemporalConstraint, extract_temporal_constraints

YEAR_RE = re.compile(r"(?<![\d,])(1[0-9]{3}|20[0-9]{2})(?!\d)")
RANGE_RE = re.compile(
    r"(?<![\d,])(1[0-9]{3}|20[0-9]{2})(?!\d)\s*(-|–|—|to|and)\s*"
    r"(?<![\d,])(1[0-9]{3}|20[0-9]{2})(?!\d)",
    re.I,
)


@dataclass(frozen=True)
class TemporalMetadata:
    valid_from: Optional[str]
    valid_to: Optional[str]
    tx_start: Optional[str]
    tx_end: Optional[str]
    granularity: str
    temporal_source: str
    temporal_confidence: float
    temporal_ambiguity: bool
    normalized_start: Optional[str] = None
    normalized_end: Optional[str] = None
    precision: str = "unknown"
    temporal_role: str = "unknown"
    original_temporal_expression: Optional[str] = None
    ambiguous_parse: bool = False
    temporal_constraints: List[Dict[str, Any]] = field(default_factory=list)
    interval_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GlobalContext:
    document_title: Optional[str] = None
    source_family: Optional[str] = None
    section: Optional[str] = None
    unit: Optional[str] = None
    entity: Optional[str] = None
    region: Optional[str] = None
    source_uri: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value}


@dataclass(frozen=True)
class TemporalContextualChunk:
    stable_id: str
    raw_text: str
    retrieval_text: str
    global_context: GlobalContext
    temporal: TemporalMetadata


def build_temporal_contextual_chunks(
    raw_text: str,
    *,
    payload: Optional[Mapping[str, Any]] = None,
    facets: Optional[Mapping[str, str]] = None,
    uri: Optional[str] = None,
    units: Optional[Iterable[str]] = None,
    entities: Optional[Iterable[str]] = None,
) -> List[TemporalContextualChunk]:
    """Create ChronoRAG chunks from one structured row or unstructured text blob."""
    payload = payload or {}
    facets = facets or {}
    raw_text = raw_text.strip()
    if not raw_text:
        return []

    global_context = build_global_context(payload, facets, uri, units, entities)
    base_temporal = infer_temporal_metadata(raw_text, payload=payload, global_context=global_context)

    chunks = _split_multi_year_claims(raw_text, base_temporal)
    output: List[TemporalContextualChunk] = []
    for idx, chunk_text in enumerate(chunks):
        temporal = infer_temporal_metadata(chunk_text, payload=payload, global_context=global_context)
        retrieval_text = build_retrieval_text(chunk_text, global_context, temporal)
        stable_seed = "|".join([uri or "", payload.get("external_id", ""), str(idx), chunk_text])
        output.append(
            TemporalContextualChunk(
                stable_id=uuid.uuid5(uuid.NAMESPACE_URL, stable_seed).hex,
                raw_text=chunk_text,
                retrieval_text=retrieval_text,
                global_context=global_context,
                temporal=temporal,
            )
        )
    return output


def build_global_context(
    payload: Mapping[str, Any],
    facets: Mapping[str, str],
    uri: Optional[str],
    units: Optional[Iterable[str]],
    entities: Optional[Iterable[str]],
) -> GlobalContext:
    title = payload.get("page_title") or payload.get("document_title") or facets.get("title")
    if not title and facets.get("domain") == "world-economy":
        title = "Maddison/OECD world economy dataset"
    section = _first_string(payload.get("section"), payload.get("sections"), payload.get("page_section"))
    source_family = facets.get("source") or payload.get("source_family")
    unit = _unit_label(list(units or []), facets)
    entity = _entity_label(list(entities or []))
    region = facets.get("region") or _region_label(list(entities or []))
    return GlobalContext(
        document_title=str(title) if title else None,
        source_family=str(source_family) if source_family else None,
        section=section,
        unit=unit,
        entity=entity,
        region=region,
        source_uri=uri,
    )


def infer_temporal_metadata(
    raw_text: str,
    *,
    payload: Optional[Mapping[str, Any]] = None,
    global_context: Optional[GlobalContext] = None,
) -> TemporalMetadata:
    """Infer valid/transaction metadata without inventing unsupported valid time."""
    payload = payload or {}
    global_context = global_context or GlobalContext()

    tx_start, tx_end = _tx_from_payload(payload)
    constraints = extract_temporal_constraints(raw_text)
    row_window = _row_valid_window(payload)

    explicit_valid = _best_constraint(constraints, role="valid_time")
    explicit_tx = _best_transaction_constraint(constraints)

    if explicit_tx and not tx_start:
        tx_start = _constraint_start_date(explicit_tx)
        tx_end = _constraint_end_date(explicit_tx) if explicit_tx.normalized_end != explicit_tx.normalized_start else tx_end

    valid_constraints = [
        constraint
        for constraint in constraints
        if constraint.temporal_role == "valid_time" and not constraint.ambiguous_parse and constraint.normalized_start
    ]
    if len(valid_constraints) > 1:
        starts = sorted(_constraint_start_date(constraint) for constraint in valid_constraints if _constraint_start_date(constraint))
        ends = sorted(_constraint_end_date(constraint) for constraint in valid_constraints if _constraint_end_date(constraint))
        if starts and ends:
            return TemporalMetadata(
                valid_from=starts[0],
                valid_to=ends[-1],
                tx_start=tx_start,
                tx_end=tx_end,
                granularity="range",
                temporal_source="chunk_explicit",
                temporal_confidence=0.55,
                temporal_ambiguity=True,
                normalized_start=starts[0],
                normalized_end=ends[-1],
                precision="range",
                temporal_role="valid_time",
                temporal_constraints=_constraints_to_dicts(constraints),
                interval_confidence=0.55,
            )

    if explicit_valid:
        return _metadata_from_constraint(
            explicit_valid,
            tx_start=tx_start,
            tx_end=tx_end,
            source="chunk_explicit",
            constraints=constraints,
        )

    if row_window:
        start, end, granularity = row_window
        return TemporalMetadata(
            valid_from=start,
            valid_to=end,
            tx_start=tx_start,
            tx_end=tx_end,
            granularity=granularity,
            temporal_source="row_metadata",
            temporal_confidence=0.90 if granularity == "year" else 0.75,
            temporal_ambiguity=False,
            normalized_start=start,
            normalized_end=end,
            precision=_precision_label(granularity),
            temporal_role="valid_time",
            original_temporal_expression=None,
            ambiguous_parse=False,
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.90 if granularity == "year" else 0.75,
        )

    if explicit_tx:
        tx_start = tx_start or _constraint_start_date(explicit_tx)
        tx_end = tx_end or (_constraint_end_date(explicit_tx) if explicit_tx.normalized_end != explicit_tx.normalized_start else None)
        return TemporalMetadata(
            valid_from=None,
            valid_to=None,
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="document",
            temporal_source="document_tx_time",
            temporal_confidence=0.30,
            temporal_ambiguity=True,
            normalized_start=explicit_tx.normalized_start or tx_start,
            normalized_end=explicit_tx.normalized_end or tx_end or tx_start,
            precision=_precision_label(explicit_tx.granularity),
            temporal_role=explicit_tx.temporal_role,
            original_temporal_expression=explicit_tx.original_text,
            ambiguous_parse=explicit_tx.ambiguous_parse,
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=explicit_tx.confidence,
        )

    ambiguous = next((constraint for constraint in constraints if constraint.ambiguous_parse), None)
    if ambiguous:
        return TemporalMetadata(
            valid_from=None,
            valid_to=None,
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="unknown",
            temporal_source="ambiguous_parse",
            temporal_confidence=0.20,
            temporal_ambiguity=True,
            normalized_start=None,
            normalized_end=None,
            precision="unknown",
            temporal_role=ambiguous.temporal_role,
            original_temporal_expression=ambiguous.original_text,
            ambiguous_parse=True,
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=ambiguous.confidence,
        )

    explicit_range = _explicit_range(raw_text)
    if explicit_range:
        start_year, end_year = explicit_range
        return TemporalMetadata(
            valid_from=_iso_date(start_year, 1, 1),
            valid_to=_iso_date(end_year, 12, 31),
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="range",
            temporal_source="chunk_explicit_range",
            temporal_confidence=0.70,
            temporal_ambiguity=False,
            normalized_start=_iso_date(start_year, 1, 1),
            normalized_end=_iso_date(end_year, 12, 31),
            precision="range",
            temporal_role="valid_time",
            original_temporal_expression=f"{start_year}-{end_year}",
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.70,
        )

    explicit_years = _years(raw_text)
    if len(explicit_years) == 1 and _year_applies_to_claim(raw_text, explicit_years[0]):
        year = explicit_years[0]
        return TemporalMetadata(
            valid_from=_iso_date(year, 1, 1),
            valid_to=_iso_date(year, 12, 31),
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="year",
            temporal_source="chunk_explicit",
            temporal_confidence=0.95,
            temporal_ambiguity=False,
            normalized_start=_iso_date(year, 1, 1),
            normalized_end=_iso_date(year, 12, 31),
            precision="year",
            temporal_role="valid_time",
            original_temporal_expression=str(year),
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.95,
        )
    if len(explicit_years) == 1 and _looks_like_publication_time(raw_text):
        tx_start = tx_start or _iso_date(explicit_years[0], 1, 1)
        return TemporalMetadata(
            valid_from=None,
            valid_to=None,
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="document",
            temporal_source="document_tx_time",
            temporal_confidence=0.30,
            temporal_ambiguity=True,
            normalized_start=tx_start,
            normalized_end=tx_end or tx_start,
            precision="year",
            temporal_role="publication_time",
            original_temporal_expression=str(explicit_years[0]),
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.30,
        )
    if len(explicit_years) > 1:
        start_year, end_year = min(explicit_years), max(explicit_years)
        return TemporalMetadata(
            valid_from=_iso_date(start_year, 1, 1),
            valid_to=_iso_date(end_year, 12, 31),
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="range",
            temporal_source="chunk_explicit",
            temporal_confidence=0.55,
            temporal_ambiguity=True,
            normalized_start=_iso_date(start_year, 1, 1),
            normalized_end=_iso_date(end_year, 12, 31),
            precision="range",
            temporal_role="valid_time",
            original_temporal_expression=f"{start_year}-{end_year}",
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.55,
        )

    section_window = _section_window(payload, global_context)
    if section_window:
        start, end = section_window
        return TemporalMetadata(
            valid_from=start,
            valid_to=end,
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="range",
            temporal_source="section_range",
            temporal_confidence=0.60,
            temporal_ambiguity=False,
            normalized_start=start,
            normalized_end=end,
            precision="range",
            temporal_role="valid_time",
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.60,
        )

    if tx_start:
        # Publication/import/revision dates describe when evidence entered a
        # source or system.  They are not valid-time claims unless the text says
        # so explicitly.
        return TemporalMetadata(
            valid_from=None,
            valid_to=None,
            tx_start=tx_start,
            tx_end=tx_end,
            granularity="document",
            temporal_source="document_tx_time",
            temporal_confidence=0.30,
            temporal_ambiguity=True,
            normalized_start=tx_start,
            normalized_end=tx_end or tx_start,
            precision="unknown",
            temporal_role="transaction_time",
            temporal_constraints=_constraints_to_dicts(constraints),
            interval_confidence=0.30,
        )

    return TemporalMetadata(
        valid_from=None,
        valid_to=None,
        tx_start=None,
        tx_end=None,
        granularity="unknown",
        temporal_source="unknown",
        temporal_confidence=0.0,
        temporal_ambiguity=True,
        temporal_constraints=_constraints_to_dicts(constraints),
    )


def temporal_metadata_to_windows(temporal: TemporalMetadata) -> tuple[TimeWindow, Optional[TimeWindow]]:
    """Convert nullable temporal metadata into legacy TimeWindow fields."""
    if temporal.valid_from and temporal.valid_to:
        valid_window = make_window(parse_date(temporal.valid_from), parse_date(temporal.valid_to))
    else:
        valid_window = make_window(parse_date("0001-01-01"), parse_date("9999-12-31"))
    tx_window = None
    if temporal.tx_start:
        tx_end = temporal.tx_end or "9999-12-31"
        tx_window = make_window(parse_date(temporal.tx_start), parse_date(tx_end))
    return valid_window, tx_window


def build_retrieval_text(raw_text: str, context: GlobalContext, temporal: TemporalMetadata) -> str:
    parts = []
    if context.document_title:
        parts.append(f"Document: {_clip(context.document_title, 12)}.")
    if context.section:
        parts.append(f"Section: {_clip(context.section, 14)}.")
    entity = context.entity or context.region
    if entity:
        parts.append(f"Entity: {_clip(entity, 8)}.")
    if context.unit:
        parts.append(f"Unit: {_clip(context.unit, 8)}.")
    scope = _temporal_scope(temporal)
    if scope:
        parts.append(f"Temporal scope: {scope}.")
    hint = _temporal_hint(temporal)
    if hint:
        parts.append(f"Temporal hint: {hint}.")
    prefix = " ".join(parts)
    if prefix:
        return f"{prefix} Original chunk: {raw_text}"
    return raw_text


def _split_multi_year_claims(raw_text: str, temporal: TemporalMetadata) -> List[str]:
    years = _years(raw_text)
    if len(years) <= 1 or temporal.temporal_source.endswith("_range"):
        return [raw_text]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", raw_text) if part.strip()]
    if len(sentences) <= 1:
        return [raw_text]
    buckets = [sentence for sentence in sentences if _years(sentence)]
    return buckets if len(buckets) > 1 else [raw_text]


def _metadata_from_constraint(
    constraint: TemporalConstraint,
    *,
    tx_start: Optional[str],
    tx_end: Optional[str],
    source: str,
    constraints: List[TemporalConstraint],
) -> TemporalMetadata:
    valid_from = _constraint_start_date(constraint)
    valid_to = _constraint_end_date(constraint)
    if "T" in constraint.normalized_start:
        valid_from = constraint.normalized_start[:10]
        valid_to = constraint.normalized_end[:10]
    if _time_only(constraint.normalized_start):
        valid_from = None
        valid_to = None
    granularity = _precision_label(constraint.granularity)
    confidence = 0.95 if source == "chunk_explicit" and granularity == "year" else constraint.confidence
    return TemporalMetadata(
        valid_from=valid_from,
        valid_to=valid_to,
        tx_start=tx_start,
        tx_end=tx_end,
        granularity=granularity,
        temporal_source=source,
        temporal_confidence=confidence,
        temporal_ambiguity=constraint.ambiguous_parse,
        normalized_start=constraint.normalized_start or valid_from,
        normalized_end=constraint.normalized_end or valid_to,
        precision=granularity,
        temporal_role=constraint.temporal_role,
        original_temporal_expression=constraint.original_text,
        ambiguous_parse=constraint.ambiguous_parse,
        temporal_constraints=_constraints_to_dicts(constraints),
        interval_confidence=confidence,
    )


def _best_constraint(constraints: List[TemporalConstraint], *, role: str) -> Optional[TemporalConstraint]:
    candidates = [
        constraint
        for constraint in constraints
        if constraint.temporal_role == role and not constraint.ambiguous_parse and constraint.normalized_start
    ]
    return candidates[0] if candidates else None


def _best_transaction_constraint(constraints: List[TemporalConstraint]) -> Optional[TemporalConstraint]:
    candidates = [
        constraint
        for constraint in constraints
        if constraint.temporal_role in {"transaction_time", "publication_time", "filing_time", "release_time"}
        and not constraint.ambiguous_parse
        and constraint.normalized_start
    ]
    return candidates[0] if candidates else None


def _constraint_start_date(constraint: TemporalConstraint) -> Optional[str]:
    if not constraint.normalized_start or _time_only(constraint.normalized_start):
        return None
    return constraint.normalized_start[:10]


def _constraint_end_date(constraint: TemporalConstraint) -> Optional[str]:
    if not constraint.normalized_end or _time_only(constraint.normalized_end):
        return None
    return constraint.normalized_end[:10]


def _constraints_to_dicts(constraints: List[TemporalConstraint]) -> List[Dict[str, Any]]:
    return [constraint.to_dict() for constraint in constraints]


def _precision_label(granularity: str) -> str:
    mapping = {
        "fuzzy_interval": "fuzzy",
        "quarter": "range",
        "time": "daypart",
    }
    return mapping.get(granularity, granularity or "unknown")


def _time_only(value: Optional[str]) -> bool:
    return bool(value and re.fullmatch(r"\d{2}:\d{2}:\d{2}", value))


def _row_valid_window(payload: Mapping[str, Any]) -> Optional[tuple[str, str, str]]:
    valid = payload.get("valid") if isinstance(payload.get("valid"), Mapping) else {}
    start_raw = valid.get("from") if valid else None
    end_raw = valid.get("to") if valid else None
    granularity = str(valid.get("granularity") or "") if valid else ""
    year = payload.get("year")
    if start_raw:
        start = parse_date(str(start_raw))
        if end_raw:
            end = parse_date(str(end_raw))
            inferred_granularity = granularity or ("year" if start.month == 1 and start.day == 1 else "range")
            end_iso = _closed_end_iso(end, inferred_granularity)
            return start.date().isoformat(), end_iso, inferred_granularity
        if granularity == "year" or re.fullmatch(r"\d{4}(?:-01-01)?", str(start_raw)):
            return _iso_date(start.year, 1, 1), _iso_date(start.year, 12, 31), "year"
        return start.date().isoformat(), "9999-12-31", granularity or "range"
    if isinstance(year, int):
        return _iso_date(year, 1, 1), _iso_date(year, 12, 31), "year"
    return None


def _section_window(payload: Mapping[str, Any], context: GlobalContext) -> Optional[tuple[str, str]]:
    haystack = " ".join(
        str(item)
        for item in [
            payload.get("section"),
            " ".join(str(section) for section in payload.get("sections", []) if section),
            context.section,
        ]
        if item
    )
    match = _explicit_range(haystack)
    if not match:
        return None
    return _iso_date(match[0], 1, 1), _iso_date(match[1], 12, 31)


def _tx_from_payload(payload: Mapping[str, Any]) -> tuple[Optional[str], Optional[str]]:
    tx = payload.get("tx") if isinstance(payload.get("tx"), Mapping) else {}
    start = tx.get("start") if tx else None
    end = tx.get("end") if tx else None
    if not start:
        provenance = payload.get("provenance") if isinstance(payload.get("provenance"), Mapping) else {}
        start = (
            payload.get("revision_timestamp")
            or payload.get("transaction_time")
            or payload.get("release_time")
            or payload.get("filing_time")
            or payload.get("publication_time")
            or payload.get("published_at")
            or payload.get("publication_date")
            or provenance.get("observed_at")
        )
    return _date_or_none(start), _date_or_none(end)


def _explicit_range(text: str) -> Optional[tuple[int, int]]:
    match = RANGE_RE.search(text or "")
    if not match:
        return None
    separator = match.group(2).lower()
    prefix = (text or "")[: match.start()].lower()
    if separator == "and" and not any(cue in prefix for cue in ("between", "from", "range", "period")):
        return None
    start, end = int(match.group(1)), int(match.group(3))
    if start > end:
        start, end = end, start
    return start, end


def _years(text: str) -> List[int]:
    years: List[int] = []
    for match in YEAR_RE.finditer(text or ""):
        year = int(match.group(1))
        tail = (text or "")[match.end() : match.end() + 40].lower()
        if year == 1990 and ("international" in tail or "intl" in tail or "dollar" in tail):
            continue
        years.append(year)
    return years


def _year_applies_to_claim(text: str, year: int) -> bool:
    lowered = text.lower()
    publication_terms = ("published", "publication", "released", "printed", "observed", "imported", "revision")
    if any(term in lowered for term in publication_terms):
        evidence_terms = ("gdp", "population", "rate", "estimate", "level", "per capita")
        return any(term in lowered for term in evidence_terms) and str(year) in lowered
    return True


def _looks_like_publication_time(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ("published", "publication", "released", "printed", "observed", "imported", "revision"))


def _first_string(*values: Any) -> Optional[str]:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return None


def _unit_label(units: List[str], facets: Mapping[str, str]) -> Optional[str]:
    if "intl_1990_usd" in units:
        return "1990 international dollars"
    if units and units != ["n/a"]:
        return ", ".join(units[:2])
    return facets.get("unit")


def _entity_label(entities: List[str]) -> Optional[str]:
    preferred = [entity for entity in entities if entity.startswith("Region:")]
    if preferred:
        return preferred[0].split(":", 1)[1]
    return entities[0] if entities else None


def _region_label(entities: List[str]) -> Optional[str]:
    for entity in entities:
        if entity.startswith("Region:"):
            return entity.split(":", 1)[1]
    return None


def _temporal_scope(temporal: TemporalMetadata) -> Optional[str]:
    if temporal.valid_from and temporal.valid_to:
        start = temporal.valid_from[:4]
        end = temporal.valid_to[:4]
        return start if start == end else f"{start}-{end}"
    if temporal.tx_start and temporal.temporal_source == "document_tx_time":
        return f"transaction time {temporal.tx_start[:4]}"
    return None


def _temporal_hint(temporal: TemporalMetadata) -> Optional[str]:
    if not temporal.normalized_start:
        return None
    role = temporal.temporal_role if temporal.temporal_role != "unknown" else "valid_time"
    precision = temporal.precision or temporal.granularity
    if temporal.normalized_end and temporal.normalized_end != temporal.normalized_start:
        original = f" original='{temporal.original_temporal_expression}'" if temporal.original_temporal_expression else ""
        return f"[{role}_range={temporal.normalized_start}..{temporal.normalized_end} precision={precision}{original}]"
    return f"[{role}={temporal.normalized_start} precision={precision}]"


def _clip(value: str, max_words: int) -> str:
    words = value.strip().split()
    if len(words) <= max_words:
        return value.strip()
    return " ".join(words[:max_words])


def _date_or_none(value: Any) -> Optional[str]:
    if not value:
        return None
    return parse_date(str(value)).date().isoformat()


def _closed_end_iso(end: dt.datetime, granularity: str) -> str:
    if granularity == "year" and end.month == 1 and end.day == 1:
        return _iso_date(end.year, 12, 31)
    return end.date().isoformat()


def _iso_date(year: int, month: int, day: int) -> str:
    return dt.date(year, month, day).isoformat()
