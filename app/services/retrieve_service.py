"""Hybrid retrieval service combining lexical, ANN, temporal, and LLM reranking.

This module coordinates every step of retrieval for ChronoRAG:
    1. Fan out across lexical BM25 and ANN embeddings.
    2. Apply domain-aware temporal filtering and heuristics (world-economy, etc.).
    3. Rerank with a cross-encoder and an LLM judge.
    4. Fuse features into a single monotonic score that respects time, authority,
       and domain-specific weight presets.

Each helper is kept pure and easy to unit-test; heavier services (PVDB, reranker)
are fetched through dependency providers so that our CLI, API, and tests share the
same behaviour.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.deps import get_models_cfg, get_policy_cfg, get_pvdb, get_reranker
from app.utils.fusion import monotone_temporal_fusion
from app.utils.time_windows import TimeWindow, tx_mismatch_penalty
from core.gsm.intent import detect_intent
from core.retrieval.lexical_bm25 import bm25_search
from core.retrieval.reranker_llm import LLMJudgeReranker


def retrieve(
    query: str,
    window: TimeWindow,
    mode: str,
    top_k: int = 5,
    axis: str = "valid",
    domain: Optional[str] = None,
) -> Dict:
    """Return top-k chunks ranked by hybrid scores for the supplied query."""
    pvdb = get_pvdb()
    reranker = get_reranker()
    judge = LLMJudgeReranker(get_models_cfg())
    policy_cfg = get_policy_cfg()

    # Detect the domain (roles, finance, world-economy, etc.) so we can pull the
    # right set of weight overrides.  World-economy uses a much wider fan-out.
    inferred_domain = domain or detect_intent(query).get("domain", "generic")
    domain_policy = policy_cfg.get("policy_sets", {}).get(
        inferred_domain,
        policy_cfg.get("policy_sets", {}).get("generic", {}),
    )
    weights_cfg = domain_policy.get(
        "retrieval_weights",
        policy_cfg.get("policy_sets", {}).get("generic", {}).get("retrieval_weights", {}),
    )

    lexical_k, vector_k, rerank_limit = _hybrid_ks(inferred_domain, top_k)

    chunks = pvdb.list_chunks()
    docs = [(chunk.chunk_id, chunk.retrieval_text or chunk.text) for chunk in chunks]
    lexical = bm25_search(query, docs, top_k=lexical_k)
    vector = pvdb.ann_search(query, top_k=vector_k)

    # Merge lexical and vector candidates while retaining the highest scores seen
    # for each chunk.  We keep both scores so the downstream fusion can reward
    # chunks that shine in either space.
    candidates: Dict[str, Dict] = {}
    for chunk_id, score in lexical:
        chunk = pvdb.chunks.get(chunk_id)
        if not chunk:
            continue
        entry = candidates.setdefault(chunk_id, {"chunk": chunk, "lexical": 0.0, "vector": 0.0})
        entry["lexical"] = max(entry["lexical"], score)
    for chunk, score in vector:
        entry = candidates.setdefault(chunk.chunk_id, {"chunk": chunk, "lexical": 0.0, "vector": 0.0})
        entry["vector"] = max(entry["vector"], score)

    temporal = pvdb.temporal_filter([entry["chunk"] for entry in candidates.values()], window, mode=mode)
    time_weights = {chunk.chunk_id: weight for chunk, weight in temporal}

    ranked_candidates: List[Tuple[str, Dict]] = [
        (chunk_id, data) for chunk_id, data in candidates.items() if chunk_id in time_weights
    ]
    ranked_candidates.sort(key=lambda item: item[1]["lexical"] + item[1]["vector"], reverse=True)
    pre_limit_candidate_count = len(ranked_candidates)
    ranked_candidates = ranked_candidates[:rerank_limit]

    texts = [data["chunk"].retrieval_text or data["chunk"].text for _, data in ranked_candidates]
    rerank_scores: Dict[str, float] = {}
    if texts:
        for idx, score in reranker.rerank(query, texts):
            if 0 <= idx < len(ranked_candidates):
                chunk_id = ranked_candidates[idx][0]
                rerank_scores[chunk_id] = float(score)

    judge_features = [
        (
            chunk_id,
            data["chunk"].retrieval_text or data["chunk"].text,
            rerank_scores.get(chunk_id, float(data["lexical"] + data["vector"])),
            time_weights[chunk_id],
            data["chunk"].authority,
        )
        for chunk_id, data in ranked_candidates
    ]
    judge_scores = {
        chunk_id: score
        for chunk_id, score in judge.rerank(
            query,
            axis,
            {
                "from": window.start.isoformat(),
                "to": window.end.isoformat(),
            },
            judge_features,
        )
    }

    results: List[Dict] = []
    for chunk_id, data in ranked_candidates:
        chunk = data["chunk"]
        rank_score = rerank_scores.get(chunk_id, float(data["lexical"] + data["vector"]))
        if chunk_id in judge_scores:
            rank_score = (rank_score + judge_scores[chunk_id]) / 2.0
        bias = _units_bias(chunk.units)
        rank_score = min(1.0, rank_score + bias)
        time_weight = time_weights[chunk_id]
        authority = chunk.authority
        mismatch = tx_mismatch_penalty(chunk.valid_window, chunk.tx_window)
        age_penalty = _age_penalty(window, chunk.valid_window)
        final = monotone_temporal_fusion(
            rank_score,
            time_weight,
            authority,
            mismatch,
            age_penalty,
            weights_cfg,
        )
        # Apply the temporal quality again after fusion so unknown or
        # transaction-time-only chunks stay available but cannot dominate exact
        # valid-time evidence on temporal queries.
        final = final * max(0.05, min(1.0, time_weight))
        region = _extract_region(chunk.entities, chunk.facets)
        results.append(
            {
                "chunk_id": chunk_id,
                "doc_id": chunk.doc_id,
                "text": chunk.raw_text or chunk.text,
                "raw_text": chunk.raw_text or chunk.text,
                "retrieval_text": chunk.retrieval_text or chunk.text,
                "uri": chunk.uri,
                "valid_window": {
                    "from": chunk.valid_window.start.isoformat(),
                    "to": chunk.valid_window.end.isoformat(),
                },
                "authority": authority,
                "rerank": float(rank_score),
                "final_score": final,
                "time_weight": time_weight,
                "facets": chunk.facets,
                "entities": chunk.entities,
                "units_detected": chunk.units,
                "time_granularity": chunk.time_granularity,
                "time_sigma_days": chunk.time_sigma_days,
                "temporal_metadata": chunk.temporal_metadata,
                "global_context": chunk.global_context,
                "region": region,
            }
        )

    _apply_region_diversity(results)
    results.sort(key=lambda item: item["final_score"], reverse=True)
    final_limit = min(top_k, len(results))
    metadata = {
        "raw_candidate_count": len(candidates),
        "temporal_hits": len(time_weights),
        "rerank_pre_limit": pre_limit_candidate_count,
        "rerank_candidates": len(ranked_candidates),
        "final_results": final_limit,
        "fanout_limit": rerank_limit,
        "coverage_fraction": min(1.0, pre_limit_candidate_count / float(max(1, rerank_limit))),
        "hops_executed": 1,
    }
    return {
        "query": query,
        "domain": inferred_domain,
        "results": results[:final_limit],
        "weights_used": weights_cfg,
        "metadata": metadata,
    }


def _hybrid_ks(domain: str, requested: int) -> Tuple[int, int, int]:
    """Return (lexical_k, vector_k, rerank_limit) tuned per domain."""
    if domain == "world-economy":
        return 150, 150, 60
    base = max(requested * 2, 10)
    return base, base, min(base, 30)


def _age_penalty(query_window: TimeWindow, candidate_window: TimeWindow) -> float:
    """Return a penalty proportional to the temporal gap between candidate and query."""
    if candidate_window.intersects(query_window):
        return 0.0
    gap = min(
        abs((candidate_window.start - query_window.end).total_seconds()),
        abs((query_window.start - candidate_window.end).total_seconds()),
    )
    days = gap / 86400.0
    return min(1.0, days / 3650.0)


def _units_bias(units: List[str]) -> float:
    """Bias scores toward numeric passages that expose principled units."""
    bias = 0.0
    if "intl_1990_usd" in units:
        bias += 0.05
    if "percent" in units:
        bias += 0.02
    if "ratio" in units:
        bias += 0.01
    return bias


def _extract_region(entities: List[str], facets: Dict[str, str]) -> Optional[str]:
    """Surface a region attribute so we can enforce regional diversity later."""
    for entity in entities:
        if entity.startswith("Region:"):
            return entity.split(":", 1)[1]
    return facets.get("region")


def _apply_region_diversity(results: List[Dict]) -> None:
    """Softly penalise over-represented regions to diversify the final hit list."""
    seen_counts: Dict[str, int] = defaultdict(int)
    for item in results:
        region = item.get("region")
        if not region:
            continue
        seen_counts[region] += 1
        if seen_counts[region] > 1:
            penalty = 0.08 * (seen_counts[region] - 1)
            item["final_score"] = max(0.0, item["final_score"] * (1.0 - penalty))
