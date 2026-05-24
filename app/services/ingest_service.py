"""Ingestion pipeline for loading historical documents into the persistent PVDB store.

ChronoRAG ingests both structured Maddison/OECD JSONL rows and ad hoc text blobs.
The helpers below normalise facets, derive entities/units, coerce yearly windows,
and ensure bi-temporal discipline when updating existing records.  The goal is to
make ingestion idempotent and additive: we never mutate existing chunks in place,
instead closing tx windows and writing fresh rows.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:  # pragma: no cover - optional dependency
    import torch
except Exception:  # pragma: no cover
    torch = None

from app.deps import get_cache, get_policy_cfg, get_pvdb
from app.utils.time_windows import TimeWindow, make_window, parse_date
from core.ingestion.temporal_contextual_chunker import (
    build_temporal_contextual_chunks,
    temporal_metadata_to_windows,
)
from core.gsm.source_risk import score_source

# Canonical Maddison doc identifier used for all world-economy re-ingests.
WORLD_ECONOMY_DOC_ID = "oecd-maddison:world_economy:v2006"
# When we ingest world-economy content we ensure these facets are present, so every
# chunk is tagged consistently even if an upstream extractor omitted them.
WORLD_FACET_DEFAULTS: Dict[str, str] = {
    "tenant": "lab",
    "domain": "world-economy",
    "source": "oecd-maddison",
    "license": "© OECD 2006 (short summaries only)",
    "locale": "en",
    "fiscal_year_start": "JAN",
}

# Simple keyword heuristics used to stamp entity strings (Country:ISO3).
COUNTRY_KEYWORDS: Dict[str, str] = {
    "united states": "USA",
    "usa": "USA",
    "u.s.": "USA",
    "united kingdom": "GBR",
    "uk": "GBR",
    "great britain": "GBR",
    "england": "GBR",
    "france": "FRA",
    "germany": "DEU",
    "italy": "ITA",
    "spain": "ESP",
    "japan": "JPN",
    "china": "CHN",
    "india": "IND",
    "brazil": "BRA",
    "mexico": "MEX",
    "canada": "CAN",
    "russia": "RUS",
}

# Region keywords allow the reranker to enforce geographic diversity.
REGION_KEYWORDS: Dict[str, str] = {
    "world": "World",
    "europe": "Europe",
    "western europe": "Western Europe",
    "european": "Europe",
    "asia": "Asia",
    "africa": "Africa",
    "americas": "Americas",
    "north america": "North America",
    "latin america": "Latin America",
    "south america": "South America",
    "oceania": "Oceania",
    "post-war": "Post-war",
}

# Unit detection helps nudge the reranker toward numeric passages.
UNIT_PATTERNS: Dict[str, Tuple[re.Pattern, ...]] = {
    "intl_1990_usd": (
        re.compile(r"1990\\s+international\\s+dollars", re.IGNORECASE),
        re.compile(r"1990\\s+intl\\.?\\s*usd", re.IGNORECASE),
    ),
    "percent": (
        re.compile(r"%"),
        re.compile(r"percent", re.IGNORECASE),
    ),
    "ratio": (
        re.compile(r"ratio", re.IGNORECASE),
        re.compile(r"per\\s+capita", re.IGNORECASE),
    ),
}

GPU_BATCHING_ENABLED = bool(torch and torch.cuda.is_available())
if os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", "/kaggle/working/.cache")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if torch and torch.cuda.is_available():
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")


def _iter_batches(items: List[str]) -> Iterable[List[str]]:
    """Yield items in up to four batches when CUDA is available; otherwise a single batch."""
    if not GPU_BATCHING_ENABLED or len(items) <= 1:
        if items:
            yield items
        return
    desired_batches = min(4, len(items))
    chunk_size = max(1, math.ceil(len(items) / desired_batches))
    for idx in range(0, len(items), chunk_size):
        yield items[idx : idx + chunk_size]


def ingest(paths: List[str], text_blobs: List[str], provenance: str | None = None) -> List[str]:
    """Entry-point for CLI/API ingestion commands."""
    pvdb = get_pvdb()
    policy = get_policy_cfg()
    ingested_ids: List[str] = []

    # Ingest every file path.  Non-existent files are silently skipped so that
    # bulk commands remain resilient to missing resources.
    for batch in _iter_batches(paths):
        for item in batch:
            path = Path(item)
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            uri = provenance or path.name
            ingested_ids.extend(_process_payload(text, uri, pvdb, policy))

    # Inline text blobs (e.g., pasted snippets) are treated like individual documents.
    offset = 0
    for batch in _iter_batches(text_blobs):
        for text in batch:
            uri = provenance or f"inline:{offset}"
            ingested_ids.extend(_process_payload(text, uri, pvdb, policy))
            offset += 1

    # Flush disk persistence once per ingest batch to amortise I/O.
    pvdb.flush()
    return ingested_ids


def _process_payload(text: str, default_uri: str, pvdb, policy: Dict) -> List[str]:
    """Attempt to parse structured JSON lines, falling back to unstructured text."""
    structured = _try_parse_structured(text)
    if structured is not None:
        return _ingest_structured(structured, default_uri, pvdb, policy)
    return _ingest_unstructured(text, default_uri, pvdb, policy)


def _try_parse_structured(text: str) -> Optional[List[Dict]]:
    """Return a list of parsed JSON objects when every line is valid JSON."""
    records: List[Dict] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            return None
    return records


def _ingest_structured(records: List[Dict], default_uri: str, pvdb, policy: Dict) -> List[str]:
    """Ingest Maddison-format structured rows."""
    ingested: List[str] = []
    for payload in records:
        text = payload.get("text")
        facets = _merge_facets(payload.get("facets"), WORLD_FACET_DEFAULTS if _is_world_economy(payload) else {})
        doc_id = payload.get("doc_id")
        if not doc_id and facets.get("domain") == "world-economy":
            doc_id = WORLD_ECONOMY_DOC_ID
        if isinstance(text, str):
            external_id = payload.get("external_id")
            entities = _derive_entities(payload, facets)
            units = _detect_units(text, facets)
            raw_uri = (
                payload.get("provenance", {}).get("uri")
                or payload.get("uri")
                or default_uri
            )
            source = score_source(raw_uri)
            contextual_chunks = build_temporal_contextual_chunks(
                text,
                payload=payload,
                facets=facets,
                uri=raw_uri,
                units=units,
                entities=entities,
            )
            for idx, contextual in enumerate(contextual_chunks):
                valid_window, tx_window = temporal_metadata_to_windows(contextual.temporal)
                metadata = {
                    "uri": raw_uri,
                    "external_id": external_id,
                    "status": payload.get("status"),
                    "provenance": payload.get("provenance"),
                    "raw_text": contextual.raw_text,
                    "retrieval_text": contextual.retrieval_text,
                    "global_context": contextual.global_context.to_dict(),
                    "temporal_metadata": contextual.temporal.to_dict(),
                }
                # Split chunks inherit the upstream external id with a suffix so
                # bitemporal lineage remains stable without collapsing claims.
                chunk_external_id = f"{external_id}:{idx}" if external_id and len(contextual_chunks) > 1 else external_id
                record = pvdb.ingest_document(
                    text=contextual.raw_text,
                    uri=raw_uri,
                    valid_window=valid_window,
                    tx_window=tx_window,
                    authority=source["authority"],
                    metadata=metadata,
                    doc_id=doc_id,
                    external_id=chunk_external_id,
                    version_id=_extract_version_id(payload),
                    facets=facets,
                    entities=entities,
                    tags=payload.get("tags"),
                    units=units,
                    time_granularity=contextual.temporal.granularity,
                    time_sigma_days=_time_sigma_days(contextual.temporal.granularity, facets),
                    raw_text=contextual.raw_text,
                    retrieval_text=contextual.retrieval_text,
                    global_context=contextual.global_context.to_dict(),
                    temporal_metadata=contextual.temporal.to_dict(),
                )
                ingested.append(record.chunk_id)
                _apply_freshness_policy(policy, entities, raw_uri)
        else:
            _handle_ledger(payload, pvdb, doc_id or WORLD_ECONOMY_DOC_ID)
    return ingested


def _ingest_unstructured(text: str, uri: str, pvdb, policy: Dict) -> List[str]:
    """Fallback for arbitrary text, preserving unknown time instead of inventing it."""
    source = score_source(uri)
    entities: List[str] = []
    units = _detect_units(text, {})
    contextual_chunks = build_temporal_contextual_chunks(
        text,
        payload={},
        facets={},
        uri=uri,
        units=units,
        entities=entities,
    )
    ingested = []
    for contextual in contextual_chunks:
        valid_window, tx_window = temporal_metadata_to_windows(contextual.temporal)
        record = pvdb.ingest_document(
            text=contextual.raw_text,
            uri=uri,
            valid_window=valid_window,
            tx_window=tx_window,
            authority=source["authority"],
            metadata={
                "uri": uri,
                "raw_text": contextual.raw_text,
                "retrieval_text": contextual.retrieval_text,
                "global_context": contextual.global_context.to_dict(),
                "temporal_metadata": contextual.temporal.to_dict(),
            },
            facets={},
            entities=entities,
            tags=None,
            units=units,
            time_granularity=contextual.temporal.granularity,
            time_sigma_days=None,
            raw_text=contextual.raw_text,
            retrieval_text=contextual.retrieval_text,
            global_context=contextual.global_context.to_dict(),
            temporal_metadata=contextual.temporal.to_dict(),
        )
        ingested.append(record.chunk_id)
        _apply_freshness_policy(policy, entities, uri)
    return ingested


def _is_world_economy(payload: Dict) -> bool:
    """Return True when a record is part of the Maddison world-economy dataset."""
    tags = payload.get("tags") or []
    facets = payload.get("facets") or {}
    return "world-economy" in tags or facets.get("domain") == "world-economy"


def _merge_facets(facets: Optional[Dict[str, str]], defaults: Dict[str, str]) -> Dict[str, str]:
    """Merge user-supplied facets with defaults without overwriting existing keys."""
    merged = dict(facets or {})
    for key, value in defaults.items():
        merged.setdefault(key, value)
    return merged


def _resolve_valid_window(payload: Dict, facets: Dict[str, str]) -> Tuple[TimeWindow, Optional[str], Optional[int]]:
    """Coerce yearly ranges into precise valid windows and apply domain defaults."""
    valid = payload.get("valid") or {}
    start_raw = valid.get("from")
    end_raw = valid.get("to")
    if start_raw is None and isinstance(payload.get("year"), int):
        start_raw = f"{payload['year']}-01-01"
    start = parse_date(str(start_raw or "1970-01-01"))
    if end_raw:
        end = parse_date(str(end_raw))
    else:
        if valid.get("granularity") == "year" or facets.get("domain") == "world-economy":
            end = dt.datetime(start.year + 1, 1, 1, tzinfo=dt.timezone.utc)
        else:
            end = parse_date("9999-12-31")
    window = make_window(start, end)
    granularity = valid.get("granularity")
    sigma = valid.get("sigma_days") or valid.get("sigma")
    if granularity is None and facets.get("domain") == "world-economy":
        granularity = "year"
    if sigma is None and facets.get("domain") == "world-economy" and granularity == "year":
        sigma = 90
    return window, granularity, sigma


def _resolve_tx_window(tx_payload: Optional[Dict], fallback: TimeWindow) -> Optional[TimeWindow]:
    """Turn tx metadata into a bi-temporal window, tolerating empty payloads."""
    if not isinstance(tx_payload, dict):
        return None
    if not tx_payload.get("start") and not tx_payload.get("end"):
        return None
    start_raw = tx_payload.get("start")
    end_raw = tx_payload.get("end")
    start = parse_date(start_raw) if start_raw else fallback.start
    end = parse_date(end_raw) if end_raw else None
    return make_window(start, end) if end else make_window(start)


def _time_sigma_days(granularity: str, facets: Dict[str, str]) -> Optional[int]:
    if facets.get("domain") == "world-economy" and granularity == "year":
        return 90
    if granularity == "range":
        return 365
    return None


def _extract_version_id(payload: Dict) -> Optional[str]:
    """Use revision identifiers from tx metadata when provided."""
    tx = payload.get("tx") or {}
    return tx.get("revision_id") or payload.get("revision_id")


def _derive_entities(payload: Dict, facets: Dict[str, str]) -> List[str]:
    """Infer entity tags (GDP, GDP_PC, Country:ISO3, Region) from text context."""
    haystacks: List[str] = []
    if isinstance(payload.get("text"), str):
        haystacks.append(payload["text"])
    if isinstance(payload.get("section"), str):
        haystacks.append(payload["section"])
    if isinstance(payload.get("sections"), list):
        haystacks.extend([str(item) for item in payload["sections"]])
    combined = " ".join(haystacks).lower()
    entities = set()
    if "gdp per capita" in combined or "per capita gdp" in combined:
        entities.add("GDP_PC")
    if "gdp" in combined:
        entities.add("GDP")
    if "population" in combined:
        entities.add("Population")
    for phrase, iso in COUNTRY_KEYWORDS.items():
        if phrase in combined:
            entities.add(f"Country:{iso}")
    for phrase, region in REGION_KEYWORDS.items():
        if phrase in combined:
            entities.add(f"Region:{region}")
    if facets.get("domain") == "world-economy":
        entities.add("Dataset:OECD_MADDISON")
    return sorted(entities)


def _detect_units(text: str, facets: Dict[str, str]) -> List[str]:
    """Return a list of detected unit tokens (e.g., intl_1990_usd, percent, ratio)."""
    units: List[str] = []
    for label, patterns in UNIT_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            units.append(label)
    lowered = text.lower()
    if facets.get("domain") == "world-economy":
        if "gdp" in lowered and "intl_1990_usd" not in units:
            units.append("intl_1990_usd")
        if ("per capita" in lowered or "per-capita" in lowered) and "ratio" not in units:
            units.append("ratio")
    if not units:
        units.append("n/a")
    return units


def _handle_ledger(payload: Dict, pvdb, doc_id: str) -> None:
    """Update document-level metadata (title, sections, revisions) without new chunks."""
    updates = {}
    if payload.get("page_title"):
        updates["page_title"] = payload["page_title"]
    if payload.get("page_url"):
        updates["page_url"] = payload["page_url"]
    if payload.get("revision_id") is not None:
        updates["revision_id"] = payload["revision_id"]
    if payload.get("revision_timestamp"):
        updates["revision_timestamp"] = payload["revision_timestamp"]
    if payload.get("sections"):
        updates["sections"] = payload["sections"]
    if updates:
        pvdb.upsert_document_metadata(doc_id, updates)


def _apply_freshness_policy(policy: Dict, entities: Iterable[str], uri: str) -> None:
    """Set freshness probes in Redis to trigger downstream monitoring signals."""
    freshness_cfg = policy.get("freshness", {})
    triggers = freshness_cfg.get("triggers", [])
    uri_lower = (uri or "").lower()
    if not any(trigger in uri_lower for trigger in triggers):
        return
    cache = get_cache()
    ttl = freshness_cfg.get("probe_interval_minutes", 60) * 60
    timestamp = time.time()
    for entity in entities:
        cache.set(
            f"freshness:{entity}",
            {"epoch": timestamp, "trigger": uri},
            ex=ttl,
        )
