from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.evaluate_retrieval_only import score_case
from benchmarks.layer2_crossdomain.run_layer2_ablations import prepare_contexts, select_evidence
from benchmarks.layer2_crossdomain.schemas import QuestionCase, load_corpus, load_questions
from chronorag.stdcomp.bm25_baseline import run_bm25_baseline
from chronorag.stdcomp.date_filter_baseline import run_date_filter_baseline
from chronorag.stdcomp.dense_baseline import DEFAULT_MODEL as DEFAULT_DENSE_MODEL
from chronorag.stdcomp.dense_baseline import run_dense_baseline


DEFAULT_CORPUS = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
DEFAULT_QUESTIONS = Path("benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")
OUT_DIR = Path("chronorag/stdcomp/results/sensitivity")
PAPER_DIR = Path("docs/paper_assets")
TOPK_VALUES = [1, 3, 5, 10]
METHOD_LABELS = {
    "chronorag_full": "ChronoRAG Full",
    "bm25": "BM25",
    "date_filter_rag": "Date-filter RAG",
    "dense_only": "Dense-only",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run safe retrieval-only sensitivity validations for paper defense.")
    parser.add_argument("--all-safe", action="store_true", help="Run supported safe validations and write not-run notes for unsupported ones.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--dense-model", default=DEFAULT_DENSE_MODEL)
    parser.add_argument("--dense-batch-size", type=int, default=64)
    parser.add_argument("--skip-dense", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    write_fusion_not_run()
    write_reranker_not_run()
    topk = run_topk_sensitivity(args)
    update_index(topk)
    print(f"Wrote {PAPER_DIR / 'fusion_weight_sensitivity_not_run.md'}")
    print(f"Wrote {PAPER_DIR / 'reranker_ablation_not_run.md'}")
    print(f"Wrote {PAPER_DIR / 'topk_sensitivity.md'}")
    print(f"Wrote {OUT_DIR / 'topk_sensitivity.json'}")


def run_topk_sensitivity(args: argparse.Namespace) -> dict[str, Any]:
    corpus = load_corpus(args.corpus)
    questions = load_questions(args.questions)
    if len(corpus) != 5000:
        raise SystemExit(f"Expected full Layer 2 corpus to contain 5000 rows, found {len(corpus)}.")
    if len(questions) != 200:
        raise SystemExit(f"Expected Layer 2A benchmark to contain 200 questions, found {len(questions)}.")

    max_k = max(TOPK_VALUES)
    payloads = {
        "chronorag_full": run_chronorag_topk_payload(corpus, questions, max_k),
        "bm25": run_bm25_baseline(corpus, questions, top_k=max_k),
        "date_filter_rag": run_date_filter_baseline(corpus, questions, top_k=max_k),
    }
    dense_error = None
    if not args.skip_dense:
        try:
            payloads["dense_only"] = run_dense_baseline(
                corpus,
                questions,
                top_k=max_k,
                model_name=args.dense_model,
                batch_size=args.dense_batch_size,
                cache_dir="chronorag/stdcomp/results/cache",
                corpus_fingerprint=None,
            )
        except Exception as exc:
            dense_error = str(exc)

    rows = []
    questions_by_id = {case.id: case for case in questions}
    for method in ("chronorag_full", "bm25", "date_filter_rag", "dense_only"):
        payload = payloads.get(method)
        if payload is None:
            continue
        selected_by_case = {
            str(row.get("case_id")): [str(item) for item in row.get("selected_evidence_ids") or []]
            for row in payload.get("results") or []
        }
        for k in TOPK_VALUES:
            rows.append(score_method_at_k(method, selected_by_case, questions_by_id, k))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rerun_performed": "retrieval_only_topk_sensitivity_no_llm",
        "corpus": str(args.corpus),
        "questions": str(args.questions),
        "topk_values": TOPK_VALUES,
        "rows": rows,
        "notes": [
            "Retrieval-only top-k sensitivity over existing Layer 2A 200-case setup.",
            "No LLM, Vertex/Gemini, judge, or answer validator was run.",
            "Main paper claim remains top-k=5; this is a reviewer-defense sensitivity check.",
        ],
    }
    if dense_error:
        payload["dense_only_error"] = dense_error
        payload["notes"].append(f"Dense-only sensitivity skipped: {dense_error}")
    write_json(OUT_DIR / "topk_sensitivity.json", payload)
    write_topk_csv(OUT_DIR / "topk_sensitivity.csv", rows)
    write_topk_markdown(PAPER_DIR / "topk_sensitivity.md", payload)
    write_topk_csv(PAPER_DIR / "topk_sensitivity.csv", rows)
    return payload


def run_chronorag_topk_payload(corpus: list[Any], questions: list[QuestionCase], top_k: int) -> dict[str, Any]:
    prepared_contexts = prepare_contexts(["chronorag_full"], corpus)
    results = []
    for case in questions:
        rows, metadata = select_evidence("chronorag_full", case, corpus, top_k, prepared_contexts)
        selected = [row.id for row in rows]
        results.append(
            {
                "case_id": case.id,
                "question": case.question,
                "selected_evidence_ids": selected,
                "metadata": metadata,
            }
        )
    return {"method": "chronorag_full", "top_k": top_k, "results": results}


def score_method_at_k(
    method: str,
    selected_by_case: dict[str, list[str]],
    questions_by_id: dict[str, QuestionCase],
    k: int,
) -> dict[str, Any]:
    hit_values = []
    mrr_values = []
    forbidden_values = []
    primary_values = []
    for case_id, case in questions_by_id.items():
        selected = selected_by_case.get(case_id, [])[:k]
        report = score_case(case, selected)
        scores = report["scores"]
        hit_values.append(bool(scores.get("generic_hit@5")))
        forbidden_values.append(bool(scores.get("generic_forbidden_absent@5")))
        primary = scores.get("category_primary_pass")
        if primary is not None:
            primary_values.append(bool(primary))
        mrr_values.append(reciprocal_rank_at_k(case, selected, k))
    cases = len(questions_by_id)
    hit = average_bool(hit_values)
    forbidden = average_bool(forbidden_values)
    primary = average_bool(primary_values)
    hit_low, hit_high = wilson(sum(hit_values), len(hit_values))
    forbidden_low, forbidden_high = wilson(sum(forbidden_values), len(forbidden_values))
    primary_low, primary_high = wilson(sum(primary_values), len(primary_values)) if primary_values else (None, None)
    return {
        "method": method,
        "method_label": METHOD_LABELS[method],
        "k": k,
        "cases": cases,
        "hit_at_k": hit,
        "hit_at_k_count": sum(hit_values),
        "hit_at_k_denominator": len(hit_values),
        "hit_at_k_ci95_low": hit_low,
        "hit_at_k_ci95_high": hit_high,
        "mrr_at_k": sum(mrr_values) / len(mrr_values),
        "forbidden_absent_at_k": forbidden,
        "forbidden_absent_at_k_count": sum(forbidden_values),
        "forbidden_absent_at_k_denominator": len(forbidden_values),
        "forbidden_absent_at_k_ci95_low": forbidden_low,
        "forbidden_absent_at_k_ci95_high": forbidden_high,
        "category_primary_pass": primary,
        "category_primary_pass_count": sum(primary_values) if primary_values else None,
        "category_primary_pass_denominator": len(primary_values),
        "category_primary_pass_ci95_low": primary_low,
        "category_primary_pass_ci95_high": primary_high,
    }


def reciprocal_rank_at_k(case: QuestionCase, selected: list[str], k: int) -> float:
    relevant = set(case.expected_evidence_ids) | set(case.acceptable_evidence_ids)
    if not relevant:
        return 0.0
    for idx, evidence_id in enumerate(selected[:k], start=1):
        if evidence_id in relevant:
            return 1.0 / idx
    return 0.0


def write_fusion_not_run() -> None:
    payload = {
        "status": "not_run",
        "reason": "No safe existing CLI/config switch exposes semantic/temporal fusion weights.",
        "evidence": [
            "benchmarks/layer2_crossdomain/methods/chronorag_full/adapter.py calls monotone_temporal_fusion with hardcoded weights.",
            "Changing those weights would require code surgery in core retrieval-path code, which is outside this validation scope.",
        ],
        "future_work": "Expose fusion weights through a documented retrieval-only experiment flag.",
    }
    write_json(OUT_DIR / "fusion_weight_sensitivity_not_run.json", payload)
    write_not_run_md(
        PAPER_DIR / "fusion_weight_sensitivity_not_run.md",
        "Fusion-Weight Sensitivity Not Run",
        payload,
    )


def write_reranker_not_run() -> None:
    payload = {
        "status": "not_run",
        "reason": "No safe existing flag was found to disable a reranker/cross-encoder in the Layer 2A ChronoRAG retrieval path.",
        "evidence": [
            "The Layer 2A adapter uses BM25, monotone temporal fusion, and finalization/slot assembly.",
            "Existing safe ablation flags cover score-only, TCC, temporal precision, transaction role, source/metric adjustment, and slot assembler, but not a reranker toggle.",
        ],
        "future_work": "Add an explicit reranker/cross-encoder toggle if a reranker is introduced into this path.",
    }
    write_json(OUT_DIR / "reranker_ablation_not_run.json", payload)
    write_not_run_md(
        PAPER_DIR / "reranker_ablation_not_run.md",
        "Reranker Ablation Not Run",
        payload,
    )


def write_not_run_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [
        f"# {title}",
        "",
        f"Status: `{payload['status']}`",
        "",
        f"Reason: {payload['reason']}",
        "",
        "Evidence:",
    ]
    lines.extend(f"- {item}" for item in payload["evidence"])
    lines.extend(["", f"Future work: {payload['future_work']}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_topk_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Top-k Retrieval-Only Sensitivity",
        "",
        "| Method | k | Cases | Hit@k | MRR@k | Forbidden Absent@k | Category Primary Pass |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['method_label']} | {row['k']} | {row['cases']} | {fmt_ci(row, 'hit_at_k')} | "
            f"{row['mrr_at_k']:.4f} | {fmt_ci(row, 'forbidden_absent_at_k')} | {fmt_ci(row, 'category_primary_pass')} |"
        )
    lines.extend(["", "Notes:"])
    lines.extend(f"- {note}" for note in payload["notes"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_topk_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "method",
        "method_label",
        "k",
        "cases",
        "hit_at_k",
        "hit_at_k_count",
        "hit_at_k_denominator",
        "hit_at_k_ci95_low",
        "hit_at_k_ci95_high",
        "mrr_at_k",
        "forbidden_absent_at_k",
        "forbidden_absent_at_k_count",
        "forbidden_absent_at_k_denominator",
        "forbidden_absent_at_k_ci95_low",
        "forbidden_absent_at_k_ci95_high",
        "category_primary_pass",
        "category_primary_pass_count",
        "category_primary_pass_denominator",
        "category_primary_pass_ci95_low",
        "category_primary_pass_ci95_high",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_index(topk_payload: dict[str, Any]) -> None:
    index_path = PAPER_DIR / "chrono_tables_index.md"
    existing = index_path.read_text(encoding="utf-8") if index_path.exists() else "# ChronoRAG Paper Tables Index\n"
    marker = "## Reviewer-Defense Validations"
    base = existing.split(marker, 1)[0].rstrip()
    lines = [
        base,
        "",
        marker,
        "",
        "- [ChronoRAG QA50 extracted values](chronorag_qa50_extracted_values.md)",
        "- [Fixed QA50 answer-level comparison](table4_qa50_answer_level_comparison.md)",
        "- [Fusion-weight sensitivity not run](fusion_weight_sensitivity_not_run.md)",
        "- [Top-k retrieval-only sensitivity](topk_sensitivity.md)",
        "- [Reranker ablation not run](reranker_ablation_not_run.md)",
    ]
    for path in sorted(PAPER_DIR.glob("*_with_ci.md")):
        lines.append(f"- [Wilson CI variant: {path.stem}]({path.name})")
    lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8")


def average_bool(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def wilson(count: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    phat = count / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2.0 * n)) / denom
    margin = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def fmt_ci(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        return "n/a"
    low = row.get(f"{key}_ci95_low")
    high = row.get(f"{key}_ci95_high")
    count = row.get(f"{key}_count")
    den = row.get(f"{key}_denominator")
    if isinstance(low, float) and isinstance(high, float):
        return f"{value:.4f} ({count}/{den}; 95% CI {low:.4f}-{high:.4f})"
    return f"{value:.4f}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
