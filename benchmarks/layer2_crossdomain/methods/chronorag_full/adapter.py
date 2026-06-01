from __future__ import annotations

import os
from dataclasses import dataclass

from app.utils.fusion import monotone_temporal_fusion
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase
from benchmarks.layer2_crossdomain.temporal_precision import (
    extract_temporal_constraints,
    has_exact_date_query,
    has_exact_timestamp_query,
    has_negative_exact_temporal_match,
    score_temporal_precision,
)
from benchmarks.layer2_crossdomain.methods.chronorag_full.finalization import AblationConfig, finalize_chronorag_evidence
from core.ingestion.temporal_contextual_chunker import build_temporal_contextual_chunks
from core.retrieval.lexical_bm25 import bm25_search


@dataclass(frozen=True)
class AdaptedChronoEvidence:
    row: CorpusRow
    retrieval_text: str
    temporal_confidence: float
    temporal_source: str
    temporal_metadata: dict
    score: float = 0.0


@dataclass(frozen=True)
class ChronoRAGPreparedContext:
    corpus: list[CorpusRow]
    adapted_chunks: list[AdaptedChronoEvidence]
    tcc_disabled: bool = False


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
                "granularity": _granularity_from_row(row),
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
                    temporal_metadata={},
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
                temporal_metadata=chunk.temporal.to_dict(),
            )
        )
    return adapted


def adapt_corpus_without_tcc(rows: list[CorpusRow]) -> list[AdaptedChronoEvidence]:
    """Use raw row text for retrieval while preserving row-level temporal metadata."""
    return [
        AdaptedChronoEvidence(
            row=row,
            retrieval_text=row.raw_text,
            temporal_confidence=0.0,
            temporal_source="row_metadata",
            temporal_metadata={
                "tcc_disabled": True,
                "valid_from": row.valid_from,
                "valid_to": row.valid_to,
                "transaction_time": row.transaction_time,
                "temporal_type": row.temporal_type,
                "source_family": row.source_family,
            },
        )
        for row in rows
    ]


def prepare_chronorag_context(corpus: list[CorpusRow], *, disable_tcc: bool = False) -> ChronoRAGPreparedContext:
    adapted = adapt_corpus_without_tcc(corpus) if disable_tcc else adapt_corpus(corpus)
    return ChronoRAGPreparedContext(corpus=corpus, adapted_chunks=adapted, tcc_disabled=disable_tcc)


def retrieve_with_chronorag_adapter(
    case: QuestionCase,
    corpus: list[CorpusRow],
    top_k: int,
    ablation_config: AblationConfig | None = None,
) -> tuple[list[CorpusRow], dict]:
    config = ablation_config or AblationConfig()
    prepared = prepare_chronorag_context(corpus, disable_tcc=config.disable_tcc)
    return retrieve_with_chronorag_prepared(case, prepared, top_k, ablation_config=config)


def retrieve_with_chronorag_prepared(
    case: QuestionCase,
    prepared_context: ChronoRAGPreparedContext,
    top_k: int,
    ablation_config: AblationConfig | None = None,
) -> tuple[list[CorpusRow], dict]:
    config = ablation_config or AblationConfig()
    adapted = prepared_context.adapted_chunks
    temporal_constraints = extract_temporal_constraints(case.question)
    lexical = dict(bm25_search(case.question, [(item.row.id, item.retrieval_text) for item in adapted], top_k=len(adapted)))
    scored: list[AdaptedChronoEvidence] = []
    for item in adapted:
        relevance = _normalize(lexical.get(item.row.id, 0.0), lexical.values())
        temporal = 0.0 if config.disable_temporal_precision else _temporal_weight(case, item.row)
        authority = 0.70 if item.row.source_kind in {"filing", "regulation", "guideline", "changelog"} else 0.50
        score = monotone_temporal_fusion(
            relevance,
            temporal,
            authority,
            0.0 if item.row.temporal_type != "transaction_time_only" else 0.60,
            0.0,
            {"alpha": 0.50, "beta_time": 0.35, "gamma_authority": 0.10, "delta_age": 0.0, "tx_gamma": 0.25},
        )
        if not config.disable_temporal_precision and has_negative_exact_temporal_match(case, item.row, temporal_constraints):
            score = 0.0
        scored.append(
            AdaptedChronoEvidence(
                row=item.row,
                retrieval_text=item.retrieval_text,
                temporal_confidence=item.temporal_confidence,
                temporal_source=item.temporal_source,
                temporal_metadata=item.temporal_metadata,
                score=score,
            )
        )
    selected, finalization_metadata = finalize_chronorag_evidence(
        scored,
        temporal_constraints,
        case.question,
        top_k,
        ablation_config=ablation_config,
    )
    metadata = {
        "method_family": "chronorag_full",
        "uses_existing_chronorag_framework": True,
        "adapter_used": True,
        "uses_tcc": not prepared_context.tcc_disabled,
        "tcc_disabled": prepared_context.tcc_disabled,
        "uses_tcc_precision_metadata": any(item.temporal_metadata.get("normalized_start") for item in selected),
        "uses_monotone_temporal_fusion": True,
        "temporal_precision_applied": not config.disable_temporal_precision,
        "requested_ablation_config": {
            "disable_tcc": config.disable_tcc,
            "disable_temporal_precision": config.disable_temporal_precision,
            "disable_transaction_role": config.disable_transaction_role,
            "disable_source_metric": config.disable_source_metric,
            "disable_slot_assembler": config.disable_slot_assembler,
            "score_only": config.score_only,
        },
        "extracted_temporal_constraints": [constraint.to_dict() for constraint in temporal_constraints],
        "exact_date_query": has_exact_date_query(temporal_constraints),
        "exact_timestamp_query": has_exact_timestamp_query(temporal_constraints),
        "temporal_granularity": temporal_constraints[0].granularity if temporal_constraints else "none",
        "temporal_role_detected": temporal_constraints[0].temporal_role if temporal_constraints else "unknown",
        "embedding_model": os.getenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        "embedding_dim": int(os.getenv("CHRONORAG_EMBED_DIM", "384")),
        "adapter_note": "Layer 2 rows are mapped through ChronoRAG TCC and monotone temporal fusion without rewriting Layer 1.",
        **finalization_metadata,
        "selected_scores": {item.row.id: round(item.score, 4) for item in selected},
        "selected_tcc_precision": {
            item.row.id: {
                "normalized_start": item.temporal_metadata.get("normalized_start"),
                "normalized_end": item.temporal_metadata.get("normalized_end"),
                "precision": item.temporal_metadata.get("precision"),
                "temporal_role": item.temporal_metadata.get("temporal_role"),
            }
            for item in selected
        },
    }
    return [item.row for item in selected], metadata


def _year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _granularity_from_row(row: CorpusRow) -> str:
    if not row.valid_from or row.temporal_type != "valid_time_exact":
        return "range"
    if row.valid_from == row.valid_to and len(row.valid_from) >= 10:
        return "day"
    return "year"


def _temporal_weight(case: QuestionCase, row: CorpusRow) -> float:
    if row.temporal_type == "conflict_claim" and case.category in {"conflict_or_revision", "conflict_detection"}:
        return 0.80
    return score_temporal_precision(case, row)


def _normalize(value: float, values) -> float:
    values = list(values)
    if not values:
        return 0.0
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return 1.0 if value else 0.0
    return (value - lo) / (hi - lo)
