from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from app.deps import get_app_state, get_policy_cfg
from app.services.retrieve_service import retrieve as full_retrieve
from app.utils.fusion import monotone_temporal_fusion
from app.utils.time_windows import TimeWindow, tx_mismatch_penalty
from core.retrieval.lexical_bm25 import bm25_search


METHODS = [
    "BM25 only",
    "Vector only",
    "Hybrid without temporal filter",
    "Hybrid with temporal filter",
    "Hybrid + temporal fusion",
    "Hybrid + temporal fusion + rerank",
]


def parse_date(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def load_cases(path: Path) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def query_text(case: Dict[str, Any]) -> str:
    return str(case.get("query") or case.get("question"))


def query_window(case: Dict[str, Any]) -> TimeWindow:
    expected = case.get("expected_valid_window") or {}
    start = case.get("window_start") or expected.get("from") or expected.get("start")
    end = case.get("window_end") or expected.get("to") or expected.get("end")
    if not start or not end:
        raise ValueError(f"Case {case.get('id')} is missing window_start/window_end or expected_valid_window")
    return TimeWindow(start=parse_date(start), end=parse_date(end))


def normalize_scores(items: Iterable[Tuple[str, float]]) -> Dict[str, float]:
    pairs = list(items)
    if not pairs:
        return {}
    values = [score for _, score in pairs]
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return {chunk_id: 1.0 for chunk_id, _ in pairs}
    return {chunk_id: (score - lo) / (hi - lo) for chunk_id, score in pairs}


def age_penalty(query_window_: TimeWindow, candidate_window: TimeWindow) -> float:
    if candidate_window.intersects(query_window_):
        return 0.0
    gap = min(
        abs((candidate_window.start - query_window_.end).total_seconds()),
        abs((query_window_.start - candidate_window.end).total_seconds()),
    )
    return min(1.0, (gap / 86400.0) / 3650.0)


def units_bias(units: List[str]) -> float:
    bias = 0.0
    if "intl_1990_usd" in units:
        bias += 0.05
    if "percent" in units:
        bias += 0.02
    if "ratio" in units:
        bias += 0.01
    return bias


def candidate_maps(query: str, candidate_k: int) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, float]]:
    state = get_app_state()
    chunks = state.pvdb.list_chunks()
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    docs = [(chunk.chunk_id, chunk.retrieval_text or chunk.text) for chunk in chunks]

    bm25_raw = bm25_search(query, docs, top_k=candidate_k)
    vector_raw = [(chunk.chunk_id, score) for chunk, score in state.pvdb.ann_search(query, top_k=candidate_k)]

    return by_id, normalize_scores(bm25_raw), normalize_scores(vector_raw)


def as_result(chunk: Any, score: float, method: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {
        "method": method,
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "text": chunk.text,
        "retrieval_text": chunk.retrieval_text or chunk.text,
        "uri": chunk.uri,
        "score": float(score),
        "valid_window": {
            "from": chunk.valid_window.start.isoformat(),
            "to": chunk.valid_window.end.isoformat(),
        },
        "authority": float(chunk.authority),
        "units_detected": list(chunk.units or []),
        "facets": dict(chunk.facets or {}),
        "entities": list(chunk.entities or []),
        "temporal_metadata": dict(chunk.temporal_metadata or {}),
        "global_context": dict(chunk.global_context or {}),
    }
    if extra:
        payload.update(extra)
    return payload


def run_bm25_only(query: str, top_k: int, candidate_k: int) -> List[Dict[str, Any]]:
    by_id, lexical_scores, _ = candidate_maps(query, candidate_k)
    ranked = sorted(lexical_scores.items(), key=lambda item: item[1], reverse=True)
    return [as_result(by_id[chunk_id], score, "BM25 only") for chunk_id, score in ranked[:top_k] if chunk_id in by_id]


def run_vector_only(query: str, top_k: int, candidate_k: int) -> List[Dict[str, Any]]:
    by_id, _, vector_scores = candidate_maps(query, candidate_k)
    ranked = sorted(vector_scores.items(), key=lambda item: item[1], reverse=True)
    return [as_result(by_id[chunk_id], score, "Vector only") for chunk_id, score in ranked[:top_k] if chunk_id in by_id]


def run_hybrid_no_temporal(query: str, top_k: int, candidate_k: int) -> List[Dict[str, Any]]:
    by_id, lexical_scores, vector_scores = candidate_maps(query, candidate_k)
    ranked = []
    for chunk_id in set(lexical_scores) | set(vector_scores):
        score = 0.5 * lexical_scores.get(chunk_id, 0.0) + 0.5 * vector_scores.get(chunk_id, 0.0)
        ranked.append((chunk_id, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return [
        as_result(by_id[chunk_id], score, "Hybrid without temporal filter")
        for chunk_id, score in ranked[:top_k]
        if chunk_id in by_id
    ]


def run_hybrid_temporal_filter(query: str, window: TimeWindow, top_k: int, candidate_k: int) -> List[Dict[str, Any]]:
    state = get_app_state()
    by_id, lexical_scores, vector_scores = candidate_maps(query, candidate_k)
    candidates = [by_id[chunk_id] for chunk_id in set(lexical_scores) | set(vector_scores) if chunk_id in by_id]
    temporal_hits = state.pvdb.temporal_filter(candidates, window, mode="HARD")
    allowed = {chunk.chunk_id for chunk, _ in temporal_hits}

    ranked = []
    for chunk_id in allowed:
        score = 0.5 * lexical_scores.get(chunk_id, 0.0) + 0.5 * vector_scores.get(chunk_id, 0.0)
        ranked.append((chunk_id, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return [
        as_result(by_id[chunk_id], score, "Hybrid with temporal filter")
        for chunk_id, score in ranked[:top_k]
        if chunk_id in by_id
    ]


def run_hybrid_temporal_fusion(query: str, window: TimeWindow, top_k: int, candidate_k: int) -> List[Dict[str, Any]]:
    state = get_app_state()
    policy_cfg = get_policy_cfg()
    weights = policy_cfg.get("policy_sets", {}).get("generic", {}).get("retrieval_weights", {})
    by_id, lexical_scores, vector_scores = candidate_maps(query, candidate_k)
    candidates = [by_id[chunk_id] for chunk_id in set(lexical_scores) | set(vector_scores) if chunk_id in by_id]
    temporal_hits = state.pvdb.temporal_filter(candidates, window, mode="INTELLIGENT")
    time_weights = {chunk.chunk_id: weight for chunk, weight in temporal_hits}

    ranked = []
    for chunk_id, time_weight in time_weights.items():
        chunk = by_id[chunk_id]
        rank_score = 0.5 * lexical_scores.get(chunk_id, 0.0) + 0.5 * vector_scores.get(chunk_id, 0.0)
        rank_score = min(1.0, rank_score + units_bias(chunk.units or []))
        final_score = monotone_temporal_fusion(
            r=rank_score,
            t=time_weight,
            a=chunk.authority,
            tx_mismatch=tx_mismatch_penalty(chunk.valid_window, chunk.tx_window),
            age_penalty=age_penalty(window, chunk.valid_window),
            weights=weights,
        )
        ranked.append((chunk_id, final_score, time_weight, rank_score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return [
        as_result(
            by_id[chunk_id],
            final_score,
            "Hybrid + temporal fusion",
            {"time_weight": time_weight, "rank_score": rank_score},
        )
        for chunk_id, final_score, time_weight, rank_score in ranked[:top_k]
        if chunk_id in by_id
    ]


def run_full_chronorag(query: str, axis: str, window: TimeWindow, top_k: int) -> List[Dict[str, Any]]:
    payload = full_retrieve(query=query, window=window, mode="INTELLIGENT", top_k=top_k, axis=axis)
    output = []
    for item in payload.get("results", []):
        output.append(
            {
                "method": "Hybrid + temporal fusion + rerank",
                "chunk_id": item.get("chunk_id"),
                "doc_id": item.get("doc_id"),
                "text": item.get("text", ""),
                "uri": item.get("uri", ""),
                "score": float(item.get("final_score", 0.0)),
                "valid_window": item.get("valid_window", {}),
                "authority": float(item.get("authority", 0.0)),
                "units_detected": item.get("units_detected", []),
                "facets": item.get("facets", {}),
                "entities": item.get("entities", []),
                "temporal_metadata": item.get("temporal_metadata", {}),
                "global_context": item.get("global_context", {}),
                "rerank": item.get("rerank"),
                "time_weight": item.get("time_weight"),
            }
        )
    return output[:top_k]


def result_window(result: Dict[str, Any]) -> TimeWindow | None:
    window = result.get("valid_window") or {}
    start = window.get("from") or window.get("start")
    end = window.get("to") or window.get("end")
    if not start or not end:
        return None
    return TimeWindow(start=parse_date(start), end=parse_date(end))


def contains_any(text: str, needles: List[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def score_case(case: Dict[str, Any], results: List[Dict[str, Any]], latency_ms: float) -> Dict[str, Any]:
    expected_window = query_window(case)
    window_hit = False
    top1_window_hit = False
    source_hit = False
    unit_hit = False
    text_hit = False

    for idx, result in enumerate(results):
        candidate_window = result_window(result)
        if candidate_window and candidate_window.intersects(expected_window):
            window_hit = True
            if idx == 0:
                top1_window_hit = True

        expected_source = str(case.get("expected_source") or case.get("expected_source_contains") or "").lower()
        if expected_source and expected_source in result.get("uri", "").lower():
            source_hit = True
        text = result.get("text", "")
        units = " ".join(result.get("units_detected", []) or [])
        expected_units = case.get("expected_unit_signal") or case.get("expected_unit_any", [])
        if isinstance(expected_units, str):
            expected_units = [expected_units]
        if contains_any(f"{units} {text}", expected_units):
            unit_hit = True
        expected_text = case.get("expected_text_signals") or case.get("expected_text_any", [])
        if contains_any(text, expected_text):
            text_hit = True

    expected_behavior = case.get("expected_behavior", "success")
    retrieval_evaluable = expected_behavior != "insufficient_evidence"
    return {
        "id": case["id"],
        "query": query_text(case),
        "expected_behavior": expected_behavior,
        "difficulty": case.get("difficulty", "medium"),
        "feature_tested": case.get("feature_tested", ""),
        "retrieval_evaluable": retrieval_evaluable,
        "window_hit_at_5": 1 if window_hit else 0,
        "top1_window_hit": 1 if top1_window_hit else 0,
        "source_hit_at_5": 1 if source_hit else 0,
        "unit_hit_at_5": 1 if unit_hit else 0,
        "text_hit_at_5": 1 if text_hit else 0,
        "latency_ms": round(latency_ms, 2),
        "top_results": results,
    }


def run_method(method: str, case: Dict[str, Any], top_k: int, candidate_k: int) -> Dict[str, Any]:
    query = query_text(case)
    window = query_window(case)
    started = time.perf_counter()
    if method == "BM25 only":
        results = run_bm25_only(query, top_k, candidate_k)
    elif method == "Vector only":
        results = run_vector_only(query, top_k, candidate_k)
    elif method == "Hybrid without temporal filter":
        results = run_hybrid_no_temporal(query, top_k, candidate_k)
    elif method == "Hybrid with temporal filter":
        results = run_hybrid_temporal_filter(query, window, top_k, candidate_k)
    elif method == "Hybrid + temporal fusion":
        results = run_hybrid_temporal_fusion(query, window, top_k, candidate_k)
    elif method == "Hybrid + temporal fusion + rerank":
        results = run_full_chronorag(query, case.get("axis", "valid"), window, top_k)
    else:
        raise ValueError(f"Unknown method: {method}")
    scored = score_case(case, results, (time.perf_counter() - started) * 1000.0)
    scored["method"] = method
    return scored


def mean(values: List[float]) -> float:
    return float(statistics.mean(values)) if values else 0.0


def summarize(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for method in METHODS:
        method_rows = [row for row in details if row["method"] == method]
        evaluable_rows = [row for row in method_rows if row.get("retrieval_evaluable", True)]
        rows.append(
            {
                "method": method,
                "top1_window_hit": mean([row["top1_window_hit"] for row in evaluable_rows]),
                "window_hit_at_5": mean([row["window_hit_at_5"] for row in evaluable_rows]),
                "source_hit_at_5": mean([row["source_hit_at_5"] for row in evaluable_rows]),
                "unit_hit_at_5": mean([row["unit_hit_at_5"] for row in evaluable_rows]),
                "text_hit_at_5": mean([row["text_hit_at_5"] for row in evaluable_rows]),
                "latency_ms": mean([row["latency_ms"] for row in method_rows]),
                "n": len(method_rows),
                "eval_n": len(evaluable_rows),
            }
        )
    return rows


def markdown_table(summary: List[Dict[str, Any]]) -> str:
    lines = [
        "| Method | Top1 Window | Window Hit@5 | Source Hit@5 | Unit Hit@5 | Text Hit@5 | Latency ms | Eval n |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            "| {method} | {top1:.2f} | {window:.2f} | {source:.2f} | {unit:.2f} | {text:.2f} | {latency:.1f} | {eval_n} |".format(
                method=row["method"],
                top1=row["top1_window_hit"],
                window=row["window_hit_at_5"],
                source=row["source_hit_at_5"],
                unit=row["unit_hit_at_5"],
                text=row["text_hit_at_5"],
                latency=row["latency_ms"],
                eval_n=row["eval_n"],
            )
        )
    return "\n".join(lines)


def per_case_markdown(details: List[Dict[str, Any]]) -> str:
    full_rows = [row for row in details if row["method"] == "Hybrid + temporal fusion + rerank"]
    lines = [
        "| Case | Behavior | Difficulty | Feature | Top1 Window | Window Hit@5 | Text Hit@5 |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in full_rows:
        if not row.get("retrieval_evaluable", True):
            top1 = "n/a"
            window = "n/a"
            text = row["text_hit_at_5"]
        else:
            top1 = row["top1_window_hit"]
            window = row["window_hit_at_5"]
            text = row["text_hit_at_5"]
        lines.append(
            "| {id} | {behavior} | {difficulty} | {feature} | {top1} | {window} | {text} |".format(
                id=row["id"],
                behavior=row["expected_behavior"],
                difficulty=row["difficulty"],
                feature=row["feature_tested"],
                top1=top1,
                window=window,
                text=text,
            )
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ChronoRAG retrieval ablation benchmark.")
    parser.add_argument("--cases", default="benchmarks/temporal_qa_sample.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=150)
    parser.add_argument("--out", default="benchmarks/results/ablation_results.json")
    args = parser.parse_args()

    state = get_app_state()
    if not state.pvdb.list_chunks():
        raise SystemExit(
            "PVDB is empty. Run ingest first, for example:\n"
            "CHRONORAG_LIGHT=1 python -m cli.chronorag_cli ingest "
            "data/sample/smoke/*"
        )

    cases = load_cases(Path(args.cases))
    details = [run_method(method, case, args.top_k, args.candidate_k) for case in cases for method in METHODS]
    summary = summarize(details)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark": "chronorag_temporal_retrieval_ablation",
        "top_k": args.top_k,
        "candidate_k": args.candidate_k,
        "case_count": len(cases),
        "summary": summary,
        "details": details,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path = out_path.with_suffix(".md")
    md = "\n\n".join(
        [
            "# ChronoRAG Retrieval Ablation",
            "This is a controlled temporal retrieval benchmark. It is not an external benchmark and not a SOTA claim. Expected failure and partial-answer cases are part of the design.",
            "## Method Summary",
            markdown_table(summary),
            "## Per-Case Full ChronoRAG Results",
            per_case_markdown(details),
        ]
    )
    md_path.write_text(md + "\n", encoding="utf-8")

    print(md)
    print(f"\nWrote: {out_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
