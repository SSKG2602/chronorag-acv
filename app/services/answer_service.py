"""Answer service that orchestrates retrieval, conflict checks, and LLM generation."""

from __future__ import annotations

import datetime as dt
import time
from typing import Dict, List, Tuple

from app.deps import (
    get_controller,
    get_models_cfg,
    get_policy_cfg,
    get_router,
)
from app.services.retrieve_service import retrieve
from app.utils.cards import build_attribution_card
from app.utils.chrono_reducer import (
    ChronoConflict,
    ChronoPassage,
    build_dual_timelines,
    detect_conflicts,
    reduce_passages,
)
from app.utils.time_windows import TimeWindow, window_iou
from core.dhqc.signals import RetrievalSignals
from core.generator.generate import generate_answer


def _dict_to_window(payload: Dict[str, str]) -> TimeWindow:
    """Convert a serialized window dictionary back into a TimeWindow instance."""
    return TimeWindow(
        start=dt.datetime.fromisoformat(payload["from"]),
        end=dt.datetime.fromisoformat(payload["to"]),
    )


def answer(query: str, time_hint: Dict | None, requested_mode: str, requested_axis: str) -> Dict:
    """Main entry point used by CLI/API to produce a final answer payload."""
    router = get_router()
    controller = get_controller()
    models_cfg = get_models_cfg()
    policy_cfg = get_policy_cfg()

    decision = router.route(query, time_hint, signals=None)
    mode = requested_mode or decision.mode
    axis = requested_axis or decision.axis
    window: TimeWindow = decision.window
    domain = decision.domain
    window_kind = decision.window_kind
    retrieval_top_k = 60 if domain == "world-economy" else 6

    start = time.time()
    retrieval = retrieve(query, window, mode, top_k=retrieval_top_k, axis=axis, domain=domain)
    retrieval_time = int((time.time() - start) * 1000)

    metadata = retrieval.get("metadata", {})
    results = retrieval["results"]
    coverage = metadata.get("coverage_fraction")
    if coverage is None:
        coverage = min(1.0, len(results) / max(1.0, float(retrieval_top_k)))
    signals = RetrievalSignals(
        coverage=coverage,
        authority=max((item["authority"] for item in results), default=0.0),
    )
    plan = controller.plan(mode, signals)
    hops_used = metadata.get("hops_executed", 1)
    hop_shortfall = plan.hops > hops_used

    passages: List[ChronoPassage] = [
        ChronoPassage(
            chunk_id=item["chunk_id"],
            doc_id=item["doc_id"],
            text=item["text"],
            uri=item["uri"],
            valid_window=_dict_to_window(item["valid_window"]),
            authority=item["authority"],
            score=item["final_score"],
            facets=item.get("facets", {}),
            entities=item.get("entities", []),
            units=item.get("units_detected", []),
            region=item.get("region"),
            global_context=item.get("global_context", {}),
            temporal_metadata=item.get("temporal_metadata", {}),
        )
        for item in results
    ]

    reduced = reduce_passages(passages)
    chronosanity_cfg = policy_cfg.get("chronosanity", {})
    chrono_threshold = chronosanity_cfg.get("overlap_threshold", 0.6)
    conflicts = detect_conflicts(reduced, threshold=chrono_threshold)
    counterfactuals = None
    audit_trail = []
    chronosanity_warn = False
    if conflicts:
        counterfactuals = _conflict_counterfactuals(conflicts)
        conflict_event = {
            "event": "chronosanity_block",
            "overlap_threshold": chrono_threshold,
            "conflicts": [
                {
                    "first": conflict.first.uri,
                    "second": conflict.second.uri,
                    "overlap": round(conflict.overlap, 3),
                }
                for conflict in conflicts
            ],
        }
        if domain != "world-economy":
            confidence = {
                "level": "LOW",
                "reasons": [chronosanity_cfg.get("evidence_only_reason", "CHRONO_SANITY")],
                "alternative_windows": _alternative_windows(results, window),
            }
            card = build_attribution_card(reduced, mode, axis, window, confidence, counterfactuals=counterfactuals)
            degraded_flag = "CHRONO_SANITY"
            if hop_shortfall:
                degraded_flag = f"{degraded_flag}|HOP_SHORTFALL"
            controller_stats = {
                "hops_used": hops_used,
                "hop_plan": {"planned": plan.hops, "executed": hops_used, "reason": plan.reason},
                "hop_shortfall": hop_shortfall,
                "signals": signals.to_dict(),
                "latency_ms": retrieval_time,
                "time_window_kind": window_kind,
                "cost_usd": 0.0,
                "tokens_in": len(query.split()),
                "tokens_out": 0,
                "degraded": degraded_flag,
                "rerank_method": "ce",
                "retrieval_weights": retrieval.get("weights_used"),
                "router_metrics": getattr(router, "observability", {}),
            }
            return {
                "answer": "",
                "attribution_card": card,
                "controller_stats": controller_stats,
                "audit_trail": [conflict_event],
                "evidence_only": True,
                "reason": chronosanity_cfg.get("evidence_only_reason", "CHRONO_SANITY"),
            }
        chronosanity_warn = True
        audit_trail.append(conflict_event)

    generated_text, tokens_out = generate_answer(query, mode, axis, window, reduced, models_cfg, domain, window_kind)
    generated_is_fallback = (
        generated_text.startswith("ChronoGuard fallback mode")
        or generated_text.startswith("No direct in-window evidence found")
        or "Provider debug:" in generated_text
    )

    confidence = {
        "level": "HIGH" if reduced else "LOW",
        "reasons": ["single_authoritative_source" if reduced else "insufficient_evidence"],
        "alternative_windows": _alternative_windows(results, window),
    }
    if chronosanity_warn:
        confidence["level"] = "MEDIUM" if confidence["level"] == "HIGH" else confidence["level"]
        confidence["reasons"].append("chronosanity_overlap")
    card = build_attribution_card(reduced, mode, axis, window, confidence)
    if counterfactuals:
        card = build_attribution_card(reduced, mode, axis, window, confidence, counterfactuals=counterfactuals)

    degraded_flag = "CHRONO_SANITY_WARN" if chronosanity_warn else None
    if hop_shortfall:
        degraded_flag = f"{degraded_flag}|HOP_SHORTFALL" if degraded_flag else "HOP_SHORTFALL"
    controller_stats = {
        "hops_used": hops_used,
        "hop_plan": {"planned": plan.hops, "executed": hops_used, "reason": plan.reason},
        "hop_shortfall": hop_shortfall,
        "signals": signals.to_dict(),
        "latency_ms": retrieval_time,
        "time_window_kind": window_kind,
        "cost_usd": 0.0,
        "tokens_in": len(query.split()),
        "tokens_out": tokens_out,
        "degraded": degraded_flag,
        "rerank_method": "ce",
        "retrieval_weights": retrieval.get("weights_used"),
        "router_metrics": getattr(router, "observability", {}),
    }

    return {
        "answer": generated_text,
        "attribution_card": card,
        "controller_stats": controller_stats,
        "audit_trail": audit_trail,
        "evidence_only": generated_is_fallback,
        "reason": "PROVIDER_OR_LLM_FALLBACK" if generated_is_fallback else None,
    }


def _alternative_windows(results: List[Dict], query_window: TimeWindow) -> List[str]:
    """Suggest alternative windows when supporting evidence falls outside the query."""
    alternatives: List[str] = []
    for item in results:
        interval = item.get("valid_window", {})
        if not interval:
            continue
        candidate = TimeWindow(
            start=dt.datetime.fromisoformat(interval["from"]),
            end=dt.datetime.fromisoformat(interval["to"]),
        )
        if window_iou(candidate, query_window) > 0:
            continue
        label = f"{candidate.start.date()} → {candidate.end.date()}"
        if label not in alternatives:
            alternatives.append(label)
    return alternatives[:3]


def _conflict_counterfactuals(conflicts: List[ChronoConflict]) -> List[str]:
    """Turn overlapping passages into short counterfactual timeline strings."""
    timelines = []
    for conflict in conflicts:
        dual = build_dual_timelines([conflict.first, conflict.second])
        text = "; ".join(f"{ts}: {snippet}" for ts, snippet in dual)
        timelines.append(text)
    return timelines[:3]
