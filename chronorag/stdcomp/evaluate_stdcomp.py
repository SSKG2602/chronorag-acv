from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.evaluate_retrieval_only import score_case
from benchmarks.layer2_crossdomain.schemas import QuestionCase, load_corpus, load_questions
from chronorag.stdcomp.bm25_baseline import run_bm25_baseline
from chronorag.stdcomp.date_filter_baseline import run_date_filter_baseline
from chronorag.stdcomp.dense_baseline import DEFAULT_MODEL, run_dense_baseline


DEFAULT_CORPUS = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
DEFAULT_QUERIES = Path("benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")
DEFAULT_EXISTING = Path("benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json")
DEFAULT_OUT_DIR = Path("chronorag/stdcomp/results")
DEFAULT_PAPER_DIR = Path("docs/paper_assets")
METHOD_ORDER = ["bm25", "dense_only", "date_filter_rag", "metadata_temporal_rag", "chronorag_full"]
METHOD_LABELS = {
    "bm25": "BM25",
    "dense_only": "Dense-only",
    "date_filter_rag": "Date-filter RAG",
    "metadata_temporal_rag": "Metadata Temporal RAG",
    "chronorag_full": "ChronoRAG Full",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run standard retrieval baselines against the full Layer 2A 200-case benchmark."
    )
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--queries", default=str(DEFAULT_QUERIES))
    parser.add_argument("--existing-results", default=str(DEFAULT_EXISTING))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--paper-assets-dir", default=str(DEFAULT_PAPER_DIR))
    parser.add_argument("--dense-model", default=DEFAULT_MODEL)
    parser.add_argument("--dense-batch-size", type=int, default=64)
    parser.add_argument("--skip-dense", action="store_true", help="Skip dense-only baseline for diagnostics only.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    corpus_path = Path(args.corpus)
    queries_path = Path(args.queries)
    existing_path = Path(args.existing_results)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus, questions = _load_and_validate_inputs(corpus_path, queries_path)
    corpus_hash = _sha256(corpus_path)
    query_hash = _sha256(queries_path)
    questions_by_id = {case.id: case for case in questions}

    payloads: list[dict[str, Any]] = []
    payloads.append(run_bm25_baseline(corpus, questions, top_k=args.top_k))
    if not args.skip_dense:
        payloads.append(
            run_dense_baseline(
                corpus,
                questions,
                top_k=args.top_k,
                model_name=args.dense_model,
                batch_size=args.dense_batch_size,
                cache_dir=out_dir / "cache",
                corpus_fingerprint=corpus_hash,
            )
        )
    payloads.append(run_date_filter_baseline(corpus, questions, top_k=args.top_k))

    reports = []
    for payload in payloads:
        _write_json(out_dir / f"{payload['method']}_ranked_outputs.json", payload)
        report = score_payload(payload, questions_by_id, top_k=args.top_k)
        _write_json(out_dir / f"{payload['method']}_metrics.json", report)
        reports.append(report)

    existing_reports = load_existing_reports(existing_path, questions_by_id, top_k=args.top_k)
    reports.extend(existing_reports)
    reports = sorted(reports, key=lambda report: METHOD_ORDER.index(report["method"]))

    combined = {
        "corpus": {
            "path": str(corpus_path),
            "rows": len(corpus),
            "sha256": corpus_hash,
        },
        "queries": {
            "path": str(queries_path),
            "rows": len(questions),
            "sha256": query_hash,
        },
        "existing_results": str(existing_path),
        "top_k": args.top_k,
        "summary": [summary_row(report) for report in reports],
        "reports": reports,
    }
    _write_json(out_dir / "stdcomp_layer2a_comparison.json", combined)
    _write_summary_csv(out_dir / "stdcomp_layer2a_comparison.csv", combined["summary"])
    _write_markdown(out_dir / "stdcomp_layer2a_summary.md", combined)

    paper_dir = Path(args.paper_assets_dir)
    if paper_dir.exists():
        _write_summary_csv(paper_dir / "stdcomp_layer2a_summary.csv", combined["summary"])
        _write_markdown(paper_dir / "stdcomp_layer2a_summary.md", combined)

    print(render_summary_table(combined["summary"]))
    print(f"Wrote outputs under {out_dir}")
    if paper_dir.exists():
        print(f"Wrote paper summary tables under {paper_dir}")


def _load_and_validate_inputs(corpus_path: Path, queries_path: Path) -> tuple[list[Any], list[QuestionCase]]:
    if not corpus_path.exists():
        raise SystemExit(
            "Cannot run valid standard comparison because the exact full Layer 2A corpus used to generate the 200 cases is missing."
        )
    if not queries_path.exists():
        raise SystemExit(f"Layer 2A query file is missing: {queries_path}")
    corpus = load_corpus(corpus_path)
    questions = load_questions(queries_path)
    if len(corpus) != 5000:
        raise SystemExit(f"Expected full Layer 2A corpus to contain 5000 rows, found {len(corpus)} at {corpus_path}")
    if len(questions) != 200:
        raise SystemExit(f"Expected Layer 2A retrieval benchmark to contain 200 cases, found {len(questions)} at {queries_path}")
    return corpus, questions


def score_payload(payload: dict[str, Any], questions_by_id: dict[str, QuestionCase], top_k: int) -> dict[str, Any]:
    rows = payload.get("results") or []
    case_reports = []
    skipped = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        case = questions_by_id.get(case_id)
        if case is None:
            skipped.append({"case_id": case_id or "(missing)", "reason": "case_id not found in questions"})
            continue
        selected = [str(item) for item in row.get("selected_evidence_ids") or []]
        case_report = score_case(case, selected)
        case_report["mrr@5"] = reciprocal_rank_at_k(case, selected, top_k)
        case_reports.append(case_report)
    metrics, category_metrics = aggregate_case_reports(case_reports)
    return {
        "method": payload["method"],
        "method_label": METHOD_LABELS.get(payload["method"], payload["method"]),
        "source": "standard_baseline_run",
        "top_k": top_k,
        "candidate_unit": payload.get("candidate_unit"),
        "evaluated_cases": len(case_reports),
        "skipped_cases": len(skipped),
        "skipped_case_details": skipped,
        "metrics": metrics,
        "category_metrics": category_metrics,
        "case_reports": case_reports,
        "notes": payload.get("notes", []),
    }


def load_existing_reports(
    existing_path: Path,
    questions_by_id: dict[str, QuestionCase],
    top_k: int,
) -> list[dict[str, Any]]:
    if not existing_path.exists():
        raise SystemExit(f"Existing ChronoRAG/metadata result artifact is missing: {existing_path}")
    payload = json.loads(existing_path.read_text(encoding="utf-8"))
    reports = []
    expected_case_ids = set(questions_by_id)
    for source_report in payload.get("reports", []):
        method = source_report.get("method")
        if method not in {"chronorag_full", "metadata_temporal_rag"}:
            continue
        case_reports = source_report.get("case_reports") or []
        case_ids = {row.get("case_id") for row in case_reports}
        if case_ids != expected_case_ids:
            raise SystemExit(
                f"Existing artifact {existing_path} for {method} does not match the current 200-case benchmark."
            )
        enriched_cases = []
        for row in case_reports:
            case = questions_by_id[row["case_id"]]
            selected = [str(item) for item in row.get("selected_evidence_ids") or []]
            enriched = dict(row)
            enriched["mrr@5"] = reciprocal_rank_at_k(case, selected, top_k)
            enriched_cases.append(enriched)
        metrics = dict(source_report.get("metrics") or {})
        metrics["mrr@5"] = sum(row["mrr@5"] for row in enriched_cases) / max(1, len(enriched_cases))
        metrics["mrr@5_count"] = sum(row["mrr@5"] for row in enriched_cases)
        metrics["mrr@5_denominator"] = len(enriched_cases)
        reports.append(
            {
                "method": method,
                "method_label": METHOD_LABELS[method],
                "source": "saved_layer2a_aggregate_artifact",
                "result_file": source_report.get("result_file"),
                "top_k": top_k,
                "candidate_unit": "saved_selected_evidence_ids",
                "evaluated_cases": source_report.get("evaluated_cases"),
                "skipped_cases": source_report.get("skipped_cases"),
                "metrics": metrics,
                "category_metrics": source_report.get("category_metrics") or {},
                "case_reports": enriched_cases,
                "notes": [
                    "Custom metrics were extracted from the saved Layer 2A aggregate artifact.",
                    "MRR@5 was computed from saved top-k selected evidence IDs.",
                ],
            }
        )
    if len(reports) != 2:
        raise SystemExit(f"Expected ChronoRAG Full and Metadata Temporal RAG reports in {existing_path}")
    return reports


def reciprocal_rank_at_k(case: QuestionCase, selected: list[str], top_k: int) -> float:
    relevant = set(case.expected_evidence_ids) | set(case.acceptable_evidence_ids)
    if not relevant:
        return 0.0
    for idx, evidence_id in enumerate(selected[:top_k], start=1):
        if evidence_id in relevant:
            return 1.0 / idx
    return 0.0


def aggregate_case_reports(case_reports: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    overall = _new_acc()
    categories: dict[str, dict[str, dict[str, float]]] = defaultdict(_new_acc)
    mrr_total = 0.0
    category_mrr: dict[str, float] = defaultdict(float)
    for report in case_reports:
        _add_scores(overall, report["scores"])
        _add_scores(categories[report["category"]], report["scores"])
        mrr_total += float(report.get("mrr@5", 0.0))
        category_mrr[report["category"]] += float(report.get("mrr@5", 0.0))
    metrics = _rates(overall)
    metrics["mrr@5"] = mrr_total / max(1, len(case_reports))
    metrics["mrr@5_count"] = mrr_total
    metrics["mrr@5_denominator"] = len(case_reports)
    category_metrics = {}
    for category, acc in sorted(categories.items()):
        rates = _rates(acc)
        cases = int(rates.get("cases", 0))
        rates["mrr@5"] = category_mrr[category] / max(1, cases)
        rates["mrr@5_count"] = category_mrr[category]
        rates["mrr@5_denominator"] = cases
        category_metrics[category] = rates
    return metrics, category_metrics


def _new_acc() -> dict[str, dict[str, float]]:
    return {"cases": {"num": 0.0, "den": 0.0}}


def _add_scores(acc: dict[str, dict[str, float]], scores: dict[str, bool | None]) -> None:
    acc["cases"]["den"] += 1
    for key, value in scores.items():
        if value is None:
            continue
        if key not in acc:
            acc[key] = {"num": 0.0, "den": 0.0}
        acc[key]["den"] += 1
        acc[key]["num"] += float(bool(value))


def _rates(acc: dict[str, dict[str, float]]) -> dict[str, Any]:
    output: dict[str, Any] = {"cases": int(acc["cases"]["den"])}
    for key in sorted(k for k in acc if k != "cases"):
        num = acc[key]["num"]
        den = acc[key]["den"]
        output[key] = num / den if den else None
        output[f"{key}_count"] = num
        output[f"{key}_denominator"] = den
    return output


def summary_row(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report["metrics"]
    return {
        "method": report["method"],
        "method_label": report["method_label"],
        "source": report["source"],
        "cases": report["evaluated_cases"],
        "hit@1": metrics.get("generic_hit@1"),
        "hit@5": metrics.get("generic_hit@5"),
        "mrr@5": metrics.get("mrr@5"),
        "forbidden_absent@5": metrics.get("generic_forbidden_absent@5"),
        "category_primary_pass": metrics.get("category_primary_pass"),
    }


def render_summary_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method_label']} | {row['cases']} | {_fmt(row['hit@1'])} | {_fmt(row['hit@5'])} | "
            f"{_fmt(row['mrr@5'])} | {_fmt(row['forbidden_absent@5'])} | {_fmt(row['category_primary_pass'])} |"
        )
    return "\n".join(lines)


def _write_markdown(path: Path, combined: dict[str, Any]) -> None:
    lines = [
        "# Layer 2A Standard Retrieval Comparison",
        "",
        f"Corpus: `{combined['corpus']['path']}` ({combined['corpus']['rows']} rows)",
        f"Queries: `{combined['queries']['path']}` ({combined['queries']['rows']} cases)",
        f"Top-k: {combined['top_k']}",
        "",
        render_summary_table(combined["summary"]),
        "",
        "Notes:",
        "- BM25, Dense-only, and Date-filter RAG are standard comparison baselines over raw evidence-row text.",
        "- Standard baselines do not use TCC, valid-time/transaction-time separation, temporal fusion, or forbidden-time suppression.",
        "- Metadata Temporal RAG and ChronoRAG Full values are extracted from the saved Layer 2A retrieval-only artifact.",
        "- MRR@5 for saved methods is computed from saved top-k selected evidence IDs.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "method",
        "method_label",
        "cases",
        "hit@1",
        "hit@5",
        "mrr@5",
        "forbidden_absent@5",
        "category_primary_pass",
        "source",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
