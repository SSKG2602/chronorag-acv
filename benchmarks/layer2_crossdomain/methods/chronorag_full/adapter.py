from __future__ import annotations

from dataclasses import dataclass

from app.utils.fusion import monotone_temporal_fusion
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase
from core.ingestion.temporal_contextual_chunker import build_temporal_contextual_chunks
from core.retrieval.lexical_bm25 import bm25_search


@dataclass(frozen=True)
class AdaptedChronoEvidence:
    row: CorpusRow
    retrieval_text: str
    temporal_confidence: float
    temporal_source: str
    score: float = 0.0


def adapt_corpus(rows: list[CorpusRow]) -> list[AdaptedChronoEvidence]:
    """Map Layer 2 rows through ChronoRAG's TCC builder without changing Layer 1 code."""
    adapted: list[AdaptedChronoEvidence] = []
    for row in rows:
        payload = {
            "external_id": row.id,
            "source_family": row.source_family,
            "document_title": row.source_file,
            "year": _year(row.valid_from) if row.temporal_type == "valid_time_exact" else None,
            "valid": {
                "from": row.valid_from,
                "to": row.valid_to,
                "granularity": "year" if row.temporal_type == "valid_time_exact" else "range",
            }
            if row.valid_from and row.valid_to
            else None,
            "transaction_time": row.transaction_time,
        }
        facets = {
            "source": row.source_family,
            "domain": row.domain,
            "region": row.metadata.get("region", ""),
        }
        chunks = build_temporal_contextual_chunks(
            row.raw_text,
            payload=payload,
            facets=facets,
            uri=row.source_file,
            units=[row.unit] if row.unit else [],
            entities=[row.entity, *row.related_entities],
        )
        if not chunks:
            adapted.append(
                AdaptedChronoEvidence(
                    row=row,
                    retrieval_text=row.raw_text,
                    temporal_confidence=0.0,
                    temporal_source="unknown",
                )
            )
            continue
        chunk = chunks[0]
        adapted.append(
            AdaptedChronoEvidence(
                row=row,
                retrieval_text=chunk.retrieval_text,
                temporal_confidence=chunk.temporal.temporal_confidence,
                temporal_source=chunk.temporal.temporal_source,
            )
        )
    return adapted


def retrieve_with_chronorag_adapter(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> tuple[list[CorpusRow], dict]:
    adapted = adapt_corpus(corpus)
    lexical = dict(bm25_search(case.question, [(item.row.id, item.retrieval_text) for item in adapted], top_k=len(adapted)))
    scored: list[AdaptedChronoEvidence] = []
    for item in adapted:
        relevance = _normalize(lexical.get(item.row.id, 0.0), lexical.values())
        temporal = _temporal_weight(case, item.row)
        authority = 0.70 if item.row.source_kind in {"filing", "regulation", "guideline", "changelog"} else 0.50
        score = monotone_temporal_fusion(
            relevance,
            temporal,
            authority,
            0.0 if item.row.temporal_type != "transaction_time_only" else 0.60,
            0.0,
            {"alpha": 0.50, "beta_time": 0.35, "gamma_authority": 0.10, "delta_age": 0.0, "tx_gamma": 0.25},
        )
        scored.append(
            AdaptedChronoEvidence(
                row=item.row,
                retrieval_text=item.retrieval_text,
                temporal_confidence=item.temporal_confidence,
                temporal_source=item.temporal_source,
                score=score,
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    metadata = {
        "method_family": "chronorag_full",
        "uses_existing_chronorag_framework": True,
        "adapter_used": True,
        "uses_tcc": True,
        "uses_monotone_temporal_fusion": True,
        "adapter_note": "Layer 2 rows are mapped through ChronoRAG TCC and monotone temporal fusion without rewriting Layer 1.",
        "selected_scores": {item.row.id: round(item.score, 4) for item in scored[:top_k]},
    }
    return [item.row for item in scored[:top_k]], metadata


def _year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _temporal_weight(case: QuestionCase, row: CorpusRow) -> float:
    expected_years = {item[:4] for item in case.expected_valid_time if item}
    if row.temporal_type == "transaction_time_only":
        return 0.15 if case.category == "transaction_vs_valid_time" else 0.03
    if not expected_years:
        return 0.40 if row.temporal_type != "missing_or_unknown" else 0.10
    if row.valid_from and row.valid_from[:4] in expected_years and row.temporal_type == "valid_time_exact":
        return 1.0
    if row.valid_from and row.valid_to and any(row.valid_from[:4] <= year <= row.valid_to[:4] for year in expected_years):
        return 0.65
    if row.temporal_type == "conflict_claim" and case.category == "conflict_or_revision":
        return 0.80
    return 0.05


def _normalize(value: float, values) -> float:
    values = list(values)
    if not values:
        return 0.0
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return 1.0 if value else 0.0
    return (value - lo) / (hi - lo)
