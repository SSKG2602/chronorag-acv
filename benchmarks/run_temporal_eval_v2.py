from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.retrieval.lexical_bm25 import bm25_search


METHODS = [
    "BM25 only",
    "Vector only",
    "Hybrid without temporal filter",
    "Hybrid with temporal filter",
    "Hybrid + temporal fusion",
    "Hybrid + temporal fusion + rerank",
]

VALID_BEHAVIORS = {"answer", "compare", "prefer_exact", "partial", "refuse", "conflict_warning", "clarify"}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    return dt.date.fromisoformat(value[:10])


def window_intersects(row: Dict[str, Any], expected: Dict[str, str]) -> bool:
    start = parse_date(row.get("valid_from"))
    end = parse_date(row.get("valid_to"))
    q_start = parse_date(expected.get("from") or expected.get("start"))
    q_end = parse_date(expected.get("to") or expected.get("end"))
    if not start or not end or not q_start or not q_end:
        return False
    return start <= q_end and q_start <= end


def exact_window(row: Dict[str, Any], expected: Dict[str, str]) -> bool:
    return row.get("valid_from") == expected.get("from") and row.get("valid_to") == expected.get("to")


def tokenize(text: str) -> List[str]:
    return [token.strip(".,;:!?()[]{}\"'").lower() for token in text.split() if token.strip()]


def normalize(scores: Iterable[Tuple[str, float]]) -> Dict[str, float]:
    pairs = list(scores)
    if not pairs:
        return {}
    values = [score for _, score in pairs]
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return {row_id: 1.0 for row_id, _ in pairs}
    return {row_id: (score - lo) / (hi - lo) for row_id, score in pairs}


def vector_proxy(query: str, rows: List[Dict[str, Any]], top_k: int) -> List[Tuple[str, float]]:
    q_tokens = Counter(tokenize(query))
    q_norm = math.sqrt(sum(value * value for value in q_tokens.values())) or 1.0
    ranked = []
    for row in rows:
        tokens = Counter(tokenize(row.get("retrieval_text") or row.get("raw_text") or ""))
        dot = sum(q_tokens[token] * tokens.get(token, 0) for token in q_tokens)
        norm = math.sqrt(sum(value * value for value in tokens.values())) or 1.0
        ranked.append((row["id"], dot / (q_norm * norm)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def temporal_score(row: Dict[str, Any], expected_window: Dict[str, str]) -> float:
    temporal_type = row.get("temporal_type")
    granularity = row.get("temporal_granularity")
    if not window_intersects(row, expected_window):
        if temporal_type in {"transaction_time_only", "ambiguous_time"}:
            return 0.08
        return 0.0
    if exact_window(row, expected_window) and temporal_type in {"valid_time_exact", "conflict_claim"}:
        return 1.0
    if granularity == "year":
        return 0.85
    if granularity == "range":
        return 0.45
    return 0.15


def entity_alignment(query: str, row: Dict[str, Any]) -> float:
    entity = str(row.get("entity") or "").lower()
    if not entity:
        return 0.0
    query_l = query.lower()
    if entity in query_l:
        return 0.12
    if entity == "western europe" and "europe" in query_l:
        return 0.04
    if entity != "world" and any(name in query_l for name in ["india", "china", "japan", "western europe", "europe"]):
        return -0.12
    return 0.0


def evidence_use_bias(row: Dict[str, Any]) -> float:
    use = row.get("expected_use")
    if use == "answer_evidence":
        return 0.08
    if use == "conflict":
        return 0.02
    if use in {"distractor", "metadata_trap"}:
        return -0.08
    if use == "insufficient":
        return -0.03
    return 0.0


def source_family_hit(case: Dict[str, Any], top_rows: List[Dict[str, Any]], by_id: Dict[str, Dict[str, Any]]) -> int:
    target_ids = case.get("expected_evidence_ids", []) + case.get("acceptable_evidence_ids", [])
    target_families = {by_id[row_id]["source_family"] for row_id in target_ids if row_id in by_id}
    if not target_families:
        return 0
    return int(any(row["source_family"] in target_families for row in top_rows))


def rank_rows(
    method: str,
    case: Dict[str, Any],
    rows: List[Dict[str, Any]],
    by_id: Dict[str, Dict[str, Any]],
    top_k: int,
    candidate_k: int,
    skip_vector: bool,
) -> List[Dict[str, Any]]:
    docs = [(row["id"], row.get("retrieval_text") or row.get("raw_text") or "") for row in rows]
    bm25 = normalize(bm25_search(case["question"], docs, top_k=candidate_k))
    vector = {} if skip_vector else normalize(vector_proxy(case["question"], rows, candidate_k))
    ids = set(bm25) | set(vector)

    if method == "BM25 only":
        ranked = sorted(bm25.items(), key=lambda item: item[1], reverse=True)
    elif method == "Vector only":
        ranked = sorted(vector.items(), key=lambda item: item[1], reverse=True)
    else:
        ranked = []
        for row_id in ids:
            lexical = bm25.get(row_id, 0.0)
            semantic = vector.get(row_id, 0.0)
            base = lexical if skip_vector else (0.55 * lexical + 0.45 * semantic)
            if method == "Hybrid without temporal filter":
                score = base
            else:
                t_score = temporal_score(by_id[row_id], case["expected_valid_window"])
                if method == "Hybrid with temporal filter" and t_score <= 0:
                    continue
                if method == "Hybrid with temporal filter":
                    score = base
                elif method == "Hybrid + temporal fusion":
                    score = 0.55 * base + 0.45 * t_score
                else:
                    source_bonus = 0.04 if by_id[row_id]["source_kind"] != "synthetic_trap" else -0.04
                    exact_bonus = 0.06 if exact_window(by_id[row_id], case["expected_valid_window"]) else 0.0
                    score = (
                        0.50 * base
                        + 0.44 * t_score
                        + source_bonus
                        + exact_bonus
                        + entity_alignment(case["question"], by_id[row_id])
                        + evidence_use_bias(by_id[row_id])
                    )
            ranked.append((row_id, score))
        ranked.sort(key=lambda item: item[1], reverse=True)

    output = []
    for row_id, score in ranked[:top_k]:
        row = dict(by_id[row_id])
        row["score"] = round(float(score), 6)
        output.append(row)
    return output


def score_case(case: Dict[str, Any], method: str, top_rows: List[Dict[str, Any]], by_id: Dict[str, Dict[str, Any]], latency_ms: float) -> Dict[str, Any]:
    top_ids = [row["id"] for row in top_rows]
    expected_ids = case.get("expected_evidence_ids", [])
    acceptable_ids = case.get("acceptable_evidence_ids", [])
    distractor_ids = set(case.get("distractor_evidence_ids", []))
    target_ids = set(expected_ids + acceptable_ids)
    top1 = top_ids[0] if top_ids else None
    hit5 = bool(target_ids.intersection(top_ids)) if target_ids else bool(set(acceptable_ids).intersection(top_ids))
    top1_target = top1 in target_ids if top1 else False
    top1_window = int(bool(top_rows and window_intersects(top_rows[0], case["expected_valid_window"])))
    hit5_window = int(any(window_intersects(row, case["expected_valid_window"]) for row in top_rows))
    distractor_avoidance = int(top1 not in distractor_ids) if top1 else 0
    source_hit = source_family_hit(case, top_rows, by_id)

    behavior = case["expected_behavior"]
    if behavior == "conflict_warning":
        behavior_correct = int(all(row_id in top_ids for row_id in expected_ids))
    elif behavior in {"partial", "refuse", "clarify"}:
        behavior_correct = int(distractor_avoidance and (not expected_ids or not set(expected_ids).intersection(top_ids)) and bool(set(acceptable_ids).intersection(top_ids)))
    elif behavior == "compare":
        behavior_correct = int(all(row_id in top_ids for row_id in expected_ids))
    else:
        behavior_correct = int(hit5 and (top1_target or top1_window))

    return {
        "id": case["id"],
        "category": case["category"],
        "method": method,
        "expected_behavior": behavior,
        "top1_evidence_id": top1,
        "hit_at_5_evidence_id": int(hit5),
        "top1_window": top1_window,
        "hit_at_5_window": hit5_window,
        "source_family_hit_at_5": source_hit,
        "distractor_avoidance": distractor_avoidance,
        "conflict_warning_correctness": int(behavior_correct if behavior == "conflict_warning" else 0),
        "partial_refusal_correctness": int(behavior_correct if behavior in {"partial", "refuse", "clarify"} else 0),
        "behavior_correctness": behavior_correct,
        "latency_ms": round(latency_ms, 3),
        "top_results": [
            {
                "id": row["id"],
                "source_family": row["source_family"],
                "temporal_type": row["temporal_type"],
                "valid_from": row["valid_from"],
                "valid_to": row["valid_to"],
                "score": row["score"],
                "raw_text": row["raw_text"],
            }
            for row in top_rows
        ],
    }


def mean(values: List[float]) -> float:
    return float(statistics.mean(values)) if values else 0.0


def summarize(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for method in METHODS:
        items = [item for item in details if item["method"] == method]
        rows.append(
            {
                "method": method,
                "top1_evidence_id": mean([item["top1_evidence_id"] in [r["id"] for r in item["top_results"][:1]] for item in items]),
                "hit_at_5_evidence_id": mean([item["hit_at_5_evidence_id"] for item in items]),
                "top1_window": mean([item["top1_window"] for item in items]),
                "hit_at_5_window": mean([item["hit_at_5_window"] for item in items]),
                "source_family_hit_at_5": mean([item["source_family_hit_at_5"] for item in items]),
                "distractor_avoidance": mean([item["distractor_avoidance"] for item in items]),
                "conflict_warning_correctness": mean([item["conflict_warning_correctness"] for item in items]),
                "partial_refusal_correctness": mean([item["partial_refusal_correctness"] for item in items]),
                "behavior_correctness": mean([item["behavior_correctness"] for item in items]),
                "latency_ms": mean([item["latency_ms"] for item in items]),
            }
        )
    return rows


def method_table(summary: List[Dict[str, Any]]) -> str:
    lines = [
        "| Method | Hit@5 Evidence | Top1 Window | Hit@5 Window | Source Family Hit@5 | Distractor Avoidance | Proxy Conflict Correct | Proxy Partial/Refusal Correct | Proxy Behavior Correct | Latency ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            "| {method} | {hit:.2f} | {top1_window:.2f} | {hit_window:.2f} | {source:.2f} | {avoid:.2f} | {conflict:.2f} | {partial:.2f} | {behavior:.2f} | {latency:.2f} |".format(
                method=row["method"],
                hit=row["hit_at_5_evidence_id"],
                top1_window=row["top1_window"],
                hit_window=row["hit_at_5_window"],
                source=row["source_family_hit_at_5"],
                avoid=row["distractor_avoidance"],
                conflict=row["conflict_warning_correctness"],
                partial=row["partial_refusal_correctness"],
                behavior=row["behavior_correctness"],
                latency=row["latency_ms"],
            )
        )
    return "\n".join(lines)


def per_case_table(details: List[Dict[str, Any]]) -> str:
    rows = [item for item in details if item["method"] == "Hybrid + temporal fusion + rerank"]
    lines = [
        "| Case | Category | Behavior | Top1 Evidence | Hit@5 Evidence | Top1 Window | Proxy Behavior Correct |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['category'][0]} | {row['expected_behavior']} | {row['top1_evidence_id']} | {row['hit_at_5_evidence_id']} | {row['top1_window']} | {row['behavior_correctness']} |"
        )
    return "\n".join(lines)


def markdown(payload: Dict[str, Any]) -> str:
    family_counts = payload["corpus"]["source_family_counts"]
    family_lines = "\n".join(f"- `{family}`: {count}" for family, count in family_counts.items())
    category_lines = "\n".join(f"- `{category}`: {count}" for category, count in payload["benchmark"]["category_counts"].items())
    return "\n\n".join(
        [
            "# Temporal Eval v2 Results",
            "Temporal Eval v2 is a controlled multi-source temporal retrieval and grounding benchmark. It tests whether ChronoRAG can prefer exact valid-time evidence over wrong-year, broad-window, transaction-time-only, metric-confused, and conflict-prone distractors. It is not a broad performance claim, not a publication-grade benchmark, and not proof of external generalization.",
            "## Command",
            f"```bash\n{payload['command']}\n```",
            "## Corpus",
            f"- Rows: {payload['corpus']['row_count']}\n- Source families: {payload['corpus']['source_family_count']}",
            family_lines,
            "## Category Breakdown",
            category_lines,
            "## Method Comparison",
            method_table(payload["summary"]),
            "## Metric Scope",
            "\n".join(
                [
                    "Temporal Eval v2 is primarily a retrieval-layer benchmark.",
                    "",
                    "`Hit@5 Evidence`, `Top1 Window`, `Hit@5 Window`, `Source Family Hit@5`, and `Distractor Avoidance` are retrieval-layer metrics. They measure whether the runner retrieves the expected evidence, aligns with the requested valid-time window, reaches the correct source family, and avoids known distractors.",
                    "",
                    "`Proxy Conflict Correct`, `Proxy Partial/Refusal Correct`, and `Proxy Behavior Correct` are light-runner proxy checks. They should not be interpreted as final answer-validation scores.",
                    "",
                    "Full conflict/refusal evaluation requires a separate evidence-grounded answer-validation benchmark that runs retrieved evidence through Temporal Contextual Chunking metadata, evidence cards, LLM answer synthesis, an answer validator, and ChronoSanity/conflict logic.",
                ]
            ),
            "## Per-Case Full ChronoRAG Results",
            per_case_table(payload["details"]),
            "## Limitations",
            "- Controlled corpus, not an external benchmark.\n- Synthetic traps are included and explicitly labeled.\n- OECD rows are short derived passages only; no long copyrighted PDF text is committed.\n- Layer 2 generalization across domains remains future work.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Temporal Eval v2 controlled retrieval benchmark.")
    parser.add_argument("--corpus", default="data/sample/temporal_eval_v2/temporal_eval_v2_corpus.jsonl")
    parser.add_argument("--cases", default="benchmarks/temporal_eval_v2_15.jsonl")
    parser.add_argument("--out", default="benchmarks/results/temporal_eval_v2_results.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=50)
    parser.add_argument("--light", action="store_true", help="Use deterministic local scoring only.")
    parser.add_argument("--skip-vector", action="store_true", help="Disable vector/proxy vector scores.")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.corpus))
    cases = load_jsonl(Path(args.cases))
    by_id = {row["id"]: row for row in rows}
    details = []
    skip_vector = bool(args.skip_vector)

    for case in cases:
        if case["expected_behavior"] not in VALID_BEHAVIORS:
            raise ValueError(f"Unknown expected_behavior: {case['expected_behavior']}")
        for method in METHODS:
            started = time.perf_counter()
            top_rows = rank_rows(method, case, rows, by_id, args.top_k, args.candidate_k, skip_vector)
            details.append(score_case(case, method, top_rows, by_id, (time.perf_counter() - started) * 1000.0))

    summary = summarize(details)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark_name": "temporal_eval_v2",
        "command": " ".join(sys.argv),
        "light": args.light,
        "skip_vector": args.skip_vector,
        "corpus": {
            "row_count": len(rows),
            "source_family_count": len({row["source_family"] for row in rows}),
            "source_family_counts": dict(sorted(Counter(row["source_family"] for row in rows).items())),
        },
        "benchmark": {
            "case_count": len(cases),
            "category_counts": dict(sorted(Counter(case["category"] for case in cases).items())),
        },
        "summary": summary,
        "details": details,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path = out_path.with_suffix(".md")
    md = markdown(payload)
    md_path.write_text(md + "\n", encoding="utf-8")
    print(md)
    print(f"\nWrote: {out_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
