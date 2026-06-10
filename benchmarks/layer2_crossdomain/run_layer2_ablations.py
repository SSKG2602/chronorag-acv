from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.evaluate_retrieval_only import evaluate_result_file
from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import (
    ChronoRAGPreparedContext,
    prepare_chronorag_context,
    retrieve_with_chronorag_prepared,
)
from benchmarks.layer2_crossdomain.methods.chronorag_full.finalization import AblationConfig
from benchmarks.layer2_crossdomain.methods.metadata_temporal_rag.retrieval import retrieve as metadata_retrieve
from benchmarks.layer2_crossdomain.reporting import write_method_results
from benchmarks.layer2_crossdomain.run_layer2_comparison import (
    _build_payload,
    _dry_run_answer,
    _retrieval_validation_result,
    _sanitize_suffix,
    _select_questions,
)
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase, load_corpus, load_questions

DEFAULT_VARIANTS = (
    "metadata_temporal_rag",
    "chronorag_score_only",
    "chronorag_no_tcc",
    "chronorag_no_temporal_precision",
    "chronorag_no_transaction_role",
    "chronorag_no_source_metric",
    "chronorag_no_slot_assembler",
    "chronorag_full",
)
DEFAULT_CORPUS = "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
DEFAULT_QUESTIONS = "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl"
RESULTS_ROOT = Path("benchmarks/layer2_crossdomain/results")

VARIANT_CONFIGS: dict[str, AblationConfig | None] = {
    # Variants are expressed as finalization/retrieval toggles so the ablation
    # runner changes component availability, not benchmark data or scoring.
    "metadata_temporal_rag": None,
    "chronorag_score_only": AblationConfig(score_only=True),
    "chronorag_no_tcc": AblationConfig(disable_tcc=True),
    "chronorag_no_temporal_precision": AblationConfig(disable_temporal_precision=True),
    "chronorag_no_transaction_role": AblationConfig(disable_transaction_role=True),
    "chronorag_no_source_metric": AblationConfig(disable_source_metric=True),
    "chronorag_full": AblationConfig(),
    "chronorag_no_slot_assembler": AblationConfig(disable_slot_assembler=True),
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Layer 2A v3 retrieval-only ablations.")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS)
    parser.add_argument("--questions", default=DEFAULT_QUESTIONS)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--mode", choices=["dry_run"], default="dry_run")
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    parser.add_argument("--result-suffix", default="v3_ablation")
    return parser


def parse_variants(value: str) -> list[str]:
    variants = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in variants if item not in VARIANT_CONFIGS]
    if unknown:
        raise SystemExit(f"Unknown ablation variants: {', '.join(unknown)}")
    if "chronorag_full" not in variants:
        variants = [*variants, "chronorag_full"]
    return variants


def result_paths(method: str, suffix: str) -> tuple[Path, Path]:
    base = RESULTS_ROOT / f"layer2_{method}_{suffix}_results"
    return base.with_suffix(".json"), base.with_suffix(".md")


def ablation_report_paths(suffix: str) -> tuple[Path, Path]:
    base = RESULTS_ROOT / f"layer2_ablation_{suffix}"
    return base.with_suffix(".json"), base.with_suffix(".md")


def prepare_contexts(
    variants: list[str],
    corpus: list[CorpusRow],
) -> dict[bool, ChronoRAGPreparedContext]:
    contexts: dict[bool, ChronoRAGPreparedContext] = {}
    for disable_tcc in required_context_modes(variants):
        contexts[disable_tcc] = prepare_chronorag_context(corpus, disable_tcc=disable_tcc)
    return contexts


def required_context_modes(variants: list[str]) -> list[bool]:
    modes: set[bool] = set()
    for variant in variants:
        config = VARIANT_CONFIGS[variant]
        if config is not None:
            modes.add(config.effective().disable_tcc)
    return sorted(modes)


def select_evidence(
    variant: str,
    case: QuestionCase,
    corpus: list[CorpusRow],
    top_k: int,
    prepared_contexts: dict[bool, ChronoRAGPreparedContext] | None = None,
) -> tuple[list[CorpusRow], dict[str, Any]]:
    if variant == "metadata_temporal_rag":
        rows = metadata_retrieve(case, corpus, top_k=top_k)
        return rows, {
            "method_family": "metadata_temporal_rag",
            "ablation_variant": variant,
            "ablation_config": None,
        }
    config = VARIANT_CONFIGS[variant] or AblationConfig()
    if prepared_contexts is None:
        prepared_contexts = prepare_contexts([variant], corpus)
    prepared_context = prepared_contexts[config.disable_tcc]
    rows, metadata = retrieve_with_chronorag_prepared(case, prepared_context, top_k=top_k, ablation_config=config)
    metadata["ablation_variant"] = variant
    metadata["requested_ablation_config"] = asdict(config)
    metadata["effective_ablation_config"] = asdict(config.effective())
    return rows, metadata


def run_variant(
    variant: str,
    corpus: list[CorpusRow],
    questions: list[QuestionCase],
    top_k: int,
    suffix: str,
    prepared_contexts: dict[bool, ChronoRAGPreparedContext] | None = None,
) -> dict[str, Any]:
    """Run one retrieval-only ablation variant and emit method-style results.

    The dry-run answer payload is only a shape-compatible placeholder. The
    ablation score is produced later from selected evidence IDs.
    """
    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    for case in questions:
        evidence_rows, metadata = select_evidence(variant, case, corpus, top_k, prepared_contexts)
        selected_evidence_ids = [row.id for row in evidence_rows]
        results.append(
            {
                "method": variant,
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "selected_evidence_ids": selected_evidence_ids,
                "prompt_truncated": False,
                "provider_mode": "dry_run",
                "latency_ms": 0.0,
                "prompt_preview": None,
                "answer": _dry_run_answer(""),
                "validation": _retrieval_validation_result(case, selected_evidence_ids),
                "validator": "deterministic",
                "status": "completed",
                "infrastructure_failure": False,
                "provider_output_contract_failure": False,
                "provider_error": None,
                "metadata": {
                    **metadata,
                    "dry_run_prompts": False,
                    "retrieval_only_dry_run": True,
                },
            }
        )
    return _build_payload(variant, "dry_run", suffix, corpus, questions, top_k, started, results, False, "deterministic")


def build_ablation_report(evaluation_reports: list[dict[str, Any]], suffix: str) -> dict[str, Any]:
    by_method = {report["method"]: report for report in evaluation_reports}
    full = by_method["chronorag_full"]
    overall_rows = []
    category_rows = []
    interpretations = []
    # Focus categories keep interpretation tied to component intent. Categories
    # that do not drop are reported conservatively instead of being treated as
    # broad evidence that a removed component is unnecessary.
    focus_categories = {
        "chronorag_score_only": [
            "same_entity_wrong_time_trap",
            "valid_time_vs_transaction_time",
            "cross_domain_temporal_comparison",
        ],
        "chronorag_no_tcc": [
            "exact_valid_time_retrieval",
            "exact_vs_broad_temporal_preference",
            "multi_slot_temporal_coverage",
        ],
        "chronorag_no_temporal_precision": [
            "same_entity_wrong_time_trap",
            "exact_valid_time_retrieval",
            "exact_vs_broad_temporal_preference",
        ],
        "chronorag_no_transaction_role": ["valid_time_vs_transaction_time"],
        "chronorag_no_source_metric": ["source_specific_exact_time", "metric_specific_exact_time"],
        "chronorag_no_slot_assembler": [
            "multi_slot_temporal_coverage",
            "cross_domain_temporal_comparison",
            "conflict_detection",
        ],
    }

    for method, report in by_method.items():
        metrics = report["metrics"]
        delta = metrics.get("category_primary_pass", 0.0) - full["metrics"].get("category_primary_pass", 0.0)
        overall_rows.append(
            {
                "method": method,
                "generic_hit_at_1": metrics.get("generic_hit@1"),
                "generic_hit_at_5": metrics.get("generic_hit@5"),
                "forbidden_absent_at_5": metrics.get("generic_forbidden_absent@5"),
                "category_primary_pass": metrics.get("category_primary_pass"),
                "delta_vs_chronorag_full": delta,
                "evaluated_cases": report.get("evaluated_cases"),
            }
        )
        for category, category_metrics in report["category_metrics"].items():
            category_delta = category_metrics.get("category_primary_pass", 0.0) - full["category_metrics"].get(category, {}).get(
                "category_primary_pass", 0.0
            )
            category_rows.append(
                {
                    "method": method,
                    "category": category,
                    "cases": category_metrics.get("cases", 0),
                    "primary_pass": category_metrics.get("category_primary_pass"),
                    "delta_vs_chronorag_full": category_delta,
                }
            )
        if method == "chronorag_full" or method == "metadata_temporal_rag":
            continue
        interpretations.extend(_variant_interpretations(method, report, full, focus_categories.get(method, [])))

    return {
        "suffix": suffix,
        "note": "Dry-run retrieval-only ablation report. No Vertex, no answer-quality scoring, no SOTA claim.",
        "variants": [report["method"] for report in evaluation_reports],
        "overall": overall_rows,
        "per_category": category_rows,
        "interpretation": interpretations,
        "reports": evaluation_reports,
    }


def _variant_interpretations(
    method: str,
    report: dict[str, Any],
    full: dict[str, Any],
    categories: list[str],
) -> list[str]:
    lines = []
    for category in categories:
        full_score = full["category_metrics"].get(category, {}).get("category_primary_pass")
        ablated_score = report["category_metrics"].get(category, {}).get("category_primary_pass")
        if full_score is None or ablated_score is None:
            continue
        if ablated_score < full_score:
            if method == "chronorag_no_slot_assembler":
                lines.append(f"{method}: slot assembler contributes to multi-slot evidence coverage in `{category}`.")
            elif method == "chronorag_no_temporal_precision":
                lines.append(f"{method}: temporal precision contributes to exact-time ranking and wrong-time suppression in `{category}`.")
            elif method == "chronorag_no_transaction_role":
                lines.append(f"{method}: valid/transaction split contributes in `{category}`.")
            elif method == "chronorag_no_source_metric":
                lines.append(f"{method}: source/metric normalization contributes in `{category}`.")
            elif method == "chronorag_no_tcc":
                lines.append(f"{method}: TCC-derived retrieval text and temporal metadata contribute in `{category}`.")
            elif method == "chronorag_score_only":
                lines.append(f"{method}: finalization components contribute beyond fused retrieval scoring in `{category}`.")
        else:
            lines.append(
                f"{method}: `{category}` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component."
            )
    return lines


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Layer 2A v3 Ablation Report",
        "",
        payload["note"],
        "",
        "This dry-run report scores selected evidence IDs only. It does not call Vertex and does not evaluate generated answer quality.",
        "",
        "## Overall",
        "",
        "| Variant | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Delta vs chronorag_full |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["overall"]:
        lines.append(
            f"| {row['method']} | {_fmt(row['evaluated_cases'])} | {_fmt(row['generic_hit_at_1'])} | {_fmt(row['generic_hit_at_5'])} | {_fmt(row['forbidden_absent_at_5'])} | {_fmt(row['category_primary_pass'])} | {_fmt(row['delta_vs_chronorag_full'])} |"
        )
    lines.extend(
        [
            "",
            "## Per-Category",
            "",
            "| Variant | Category | Cases | Category primary pass | Delta vs chronorag_full |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in payload["per_category"]:
        lines.append(
            f"| {row['method']} | {row['category']} | {row['cases']} | {_fmt(row['primary_pass'])} | {_fmt(row['delta_vs_chronorag_full'])} |"
        )
    lines.extend(["", "## Component Interpretation", ""])
    if payload["interpretation"]:
        for line in payload["interpretation"]:
            lines.append(f"- {line}")
    else:
        lines.append("- No component-specific drop was detected against the selected focus categories.")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is a controlled Layer 2A retrieval-only ablation, not a SOTA or publication-grade claim.",
            "- Dry-run answer placeholders are not answer-quality results.",
            "- Layer 2B, active embeddings, and Vertex execution are intentionally out of scope for this run.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_ablation_report(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> None:
    args = build_arg_parser().parse_args()
    suffix = _sanitize_suffix(args.result_suffix)
    variants = parse_variants(args.variants)
    total_started = time.perf_counter()
    corpus = load_corpus(args.corpus)
    print(f"Loaded corpus: {len(corpus)} rows from {args.corpus}")
    questions = _select_questions(load_questions(args.questions), args.limit, None)
    print(f"Loaded questions: {len(questions)} cases from {args.questions}")

    context_started = time.perf_counter()
    modes = required_context_modes(variants)
    mode_labels = [("raw/no-TCC" if mode else "TCC") for mode in modes]
    print(f"Building ChronoRAG prepared contexts: {', '.join(mode_labels) if mode_labels else 'none'}")
    prepared_contexts = prepare_contexts(variants, corpus)
    print(f"Prepared contexts built in {time.perf_counter() - context_started:.2f}s")

    evaluation_reports = []
    for variant in variants:
        variant_started = time.perf_counter()
        print(f"Running variant: {variant}")
        payload = run_variant(variant, corpus, questions, args.top_k, suffix, prepared_contexts)
        json_path, md_path = result_paths(variant, suffix)
        write_method_results(payload, json_path, md_path)
        evaluation_reports.append(evaluate_result_file(json_path, {case.id: case for case in questions}))
        print(f"Wrote: {json_path}")
        print(f"Wrote: {md_path}")
        print(f"Finished variant: {variant} in {time.perf_counter() - variant_started:.2f}s")

    ablation_payload = build_ablation_report(evaluation_reports, suffix)
    report_json, report_md = ablation_report_paths(suffix)
    write_ablation_report(ablation_payload, report_json, report_md)
    print(f"Wrote: {report_json}")
    print(f"Wrote: {report_md}")
    print(f"Layer 2A ablation run completed in {time.perf_counter() - total_started:.2f}s")


if __name__ == "__main__":
    main()
