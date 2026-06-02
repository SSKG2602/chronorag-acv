from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.schemas import QuestionCase, load_questions


CATEGORY_PRIMARY_METRICS: dict[str, tuple[str, ...]] = {
    # Categories omitted from this map, such as partial/insufficient and
    # ambiguous-time questions, remain diagnostic in retrieval-only evaluation.
    # Their answer semantics belong to the future natural-language QA layer.
    "exact_valid_time_retrieval": ("expected_hit_at_1", "expected_hit_at_k", "forbidden_absent_at_k"),
    "transaction_time_vs_valid_time": ("valid_time_hit_at_k", "transaction_time_trap_avoidance"),
    "valid_time_vs_transaction_time": ("valid_time_hit_at_k", "transaction_time_trap_avoidance"),
    "same_entity_wrong_year_trap": ("target_time_hit_at_k", "wrong_time_trap_avoidance"),
    "same_entity_wrong_time_trap": ("target_time_hit_at_k", "wrong_time_trap_avoidance"),
    "broad_window_distractor": ("narrow_or_exact_hit_at_k", "broad_window_trap_avoidance"),
    "exact_vs_broad_temporal_preference": ("narrow_or_exact_hit_at_k", "broad_window_trap_avoidance"),
    "conflict_detection": ("conflict_side_coverage_at_k",),
    "source_specific_temporal_query": ("source_temporal_hit_at_k", "source_forbidden_absent_at_k"),
    "source_specific_exact_time": ("source_temporal_hit_at_k", "source_forbidden_absent_at_k"),
    "metric_specific_query": ("metric_temporal_hit_at_k", "metric_forbidden_absent_at_k"),
    "metric_specific_exact_time": ("metric_temporal_hit_at_k", "metric_forbidden_absent_at_k"),
    "cross_domain_temporal_comparison": ("both_side_coverage_at_k",),
    "multi_slot_temporal_coverage": ("all_slot_coverage_at_k", "multi_slot_forbidden_absent_at_k"),
}

WRONG_TIME_RE = re.compile(
    r"\b(?:for|in|on)\s+(?P<target>\d{4}(?:-\d{2}-\d{2})?)\b.*?\bnot\s+(?:for|in|on\s+)?(?P<forbidden>\d{4}(?:-\d{2}-\d{2})?)\b",
    re.IGNORECASE,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Layer 2 selected evidence without calling Vertex.")
    parser.add_argument("--results", nargs="+", required=True)
    parser.add_argument("--questions", default="benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")
    parser.add_argument("--save-json")
    parser.add_argument("--save-md")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    questions = {case.id: case for case in load_questions(args.questions)}
    reports = [evaluate_result_file(Path(path), questions) for path in args.results]
    comparison = compare_reports(reports, questions) if len(reports) >= 2 else None
    markdown = render_markdown(reports, comparison)
    print(markdown)
    if args.save_json:
        payload: dict[str, Any] = {"reports": reports}
        if comparison is not None:
            payload["pairwise_comparison"] = comparison
        Path(args.save_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.save_md:
        Path(args.save_md).write_text(markdown, encoding="utf-8")


def evaluate_result_file(path: Path, questions: dict[str, QuestionCase]) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results") or []
    by_case: dict[str, dict[str, Any]] = {}
    duplicate_case_ids: list[str] = []
    skipped: list[dict[str, str]] = []

    # Result files can come from resumable runs. Keep the first completed row
    # for a case and make every omission explicit in the evaluation report.
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id:
            skipped.append({"case_id": "(missing)", "reason": "result row has no case_id"})
            continue
        if case_id not in questions:
            skipped.append({"case_id": case_id, "reason": "case_id not found in benchmark questions"})
            continue
        if case_id in by_case:
            duplicate_case_ids.append(case_id)
            skipped.append({"case_id": case_id, "reason": "duplicate result row; first row kept"})
            continue
        by_case[case_id] = row

    case_reports: list[dict[str, Any]] = []
    for case_id, row in sorted(by_case.items()):
        case = questions[case_id]
        selected = [str(item) for item in row.get("selected_evidence_ids") or []]
        case_reports.append(score_case(case, selected))

    category_acc: dict[str, dict[str, dict[str, int]]] = defaultdict(_new_accumulator)
    overall_acc = _new_accumulator()
    warning_counts: dict[str, int] = defaultdict(int)

    for case_report in case_reports:
        _add_score_dict(overall_acc, case_report["scores"])
        _add_score_dict(category_acc[case_report["category"]], case_report["scores"])
        for warning in case_report["warnings"]:
            warning_counts[warning] += 1

    missing_result_case_ids = sorted(set(questions) - set(by_case))
    for case_id in missing_result_case_ids:
        skipped.append({"case_id": case_id, "reason": "benchmark case missing from result file"})

    return {
        "result_file": str(path),
        "method": payload.get("method"),
        "embedding_model": payload.get("embedding_model"),
        "embedding_dim": payload.get("embedding_dim"),
        "benchmark_cases_total": len(questions),
        "result_rows_total": len(rows),
        "evaluated_cases": len(case_reports),
        "skipped_cases": len(skipped),
        "skip_reasons": _summarize_skip_reasons(skipped),
        "skipped_case_details": skipped,
        "duplicate_case_ids": duplicate_case_ids,
        "missing_result_case_ids": missing_result_case_ids,
        "warning_counts": dict(sorted(warning_counts.items())),
        "metrics": _rates(overall_acc),
        "category_metrics": {category: _rates(stats) for category, stats in sorted(category_acc.items())},
        "case_reports": case_reports,
    }


def score_case(case: QuestionCase, selected: list[str]) -> dict[str, Any]:
    """Score one retrieval result.

    Layer 2 deterministic validation reads only selected evidence IDs. A single
    generic Hit@k score is misleading because categories test different
    retrieval failure modes: wrong-time avoidance, transaction-time avoidance,
    broad-window demotion, conflict coverage, and source/metric constraints.
    Generated answer wording and behavior labels are intentionally ignored.
    """
    expected = set(case.expected_evidence_ids)
    acceptable = set(case.acceptable_evidence_ids)
    expected_or_acceptable = expected | acceptable
    forbidden = set(case.forbidden_evidence_ids)
    synthetic = set(case.synthetic_evidence_ids)
    top1 = selected[:1]
    top5 = selected[:5]
    top5_set = set(top5)

    expected_hit_at_1 = bool(top1) and top1[0] in expected
    expected_hit_at_k = bool(expected) and bool(top5_set & expected)
    acceptable_hit_at_k = bool(top5_set & acceptable) if acceptable else None
    forbidden_absent_at_k = not bool(top5_set & forbidden)

    scores: dict[str, bool | None] = {
        "expected_hit_at_1": expected_hit_at_1,
        "expected_hit_at_k": expected_hit_at_k,
        "acceptable_hit_at_k": acceptable_hit_at_k,
        "forbidden_absent_at_k": forbidden_absent_at_k,
        "generic_hit@1": bool(top1) and top1[0] in expected_or_acceptable,
        "generic_hit@5": bool(expected_or_acceptable) and bool(top5_set & expected_or_acceptable),
        "generic_forbidden_absent@5": forbidden_absent_at_k,
        # Backward-compatible aliases for existing artifacts/tests.
        "expected_hit@1": expected_hit_at_1,
        "expected_hit@5": expected_hit_at_k,
        "acceptable_hit@5": acceptable_hit_at_k,
        "forbidden_absent@5": forbidden_absent_at_k,
    }
    warnings: list[str] = []

    if case.category == "exact_valid_time_retrieval":
        scores.update(
            {
                "expected_forbidden_absent_at_k": forbidden_absent_at_k,
                "expected_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category in {"transaction_time_vs_valid_time", "valid_time_vs_transaction_time"}:
        scores.update(
            {
                "valid_time_hit_at_k": bool(top5_set & expected_or_acceptable),
                "transaction_time_trap_avoidance": forbidden_absent_at_k,
                "valid_time_hit@5": bool(top5_set & expected_or_acceptable),
                "transaction_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category in {"same_entity_wrong_year_trap", "same_entity_wrong_time_trap"}:
        malformed = _is_malformed_wrong_year_question(case.question)
        if malformed:
            warnings.append("malformed_wrong_year_question")
        scores.update(
            {
                "target_time_hit_at_k": bool(top5_set & expected_or_acceptable),
                "wrong_time_trap_avoidance": forbidden_absent_at_k,
                "target_year_hit@5": bool(top5_set & expected_or_acceptable),
                "wrong_year_forbidden_absent@5": forbidden_absent_at_k,
                "malformed_wrong_year_question": malformed,
            }
        )
    elif case.category in {"broad_window_distractor", "exact_vs_broad_temporal_preference"}:
        scores.update(
            {
                "narrow_or_exact_hit_at_k": bool(top5_set & expected_or_acceptable),
                "broad_window_trap_avoidance": forbidden_absent_at_k,
                "narrow_or_exact_hit@5": bool(top5_set & expected_or_acceptable),
                "broad_window_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category == "conflict_detection":
        required_sides = min(2, len(expected_or_acceptable)) if expected_or_acceptable else 0
        hit_sides = len(top5_set & expected_or_acceptable)
        marker_present = bool(top5_set & synthetic)
        if synthetic:
            warnings.append("synthetic_conflict_ids_present_in_key")
        scores.update(
            {
                "conflict_side_coverage_at_k": (hit_sides >= required_sides) if required_sides else None,
                "conflict_marker_presence_at_k": marker_present if synthetic else None,
                "conflict_any_side_hit_at_k": bool(top5_set & expected_or_acceptable),
                "conflict_side_coverage@5": (hit_sides >= required_sides) if required_sides else None,
                "conflict_marker_presence@5": marker_present if synthetic else None,
                "conflict_any_side_hit@5": bool(top5_set & expected_or_acceptable),
            }
        )
    elif case.category == "partial_or_insufficient_evidence":
        warnings.append("answer_semantics_not_scored_by_retrieval_validator")
        scores.update(
            {
                "fallback_expected_hit_at_k": bool(top5_set & expected_or_acceptable) if expected_or_acceptable else None,
                "fallback_forbidden_absent_at_k": forbidden_absent_at_k,
                "fallback_expected_hit@5": bool(top5_set & expected_or_acceptable) if expected_or_acceptable else None,
                "fallback_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category == "ambiguous_time_query":
        warnings.append("answer_semantics_not_scored_by_retrieval_validator")
        scores.update(
            {
                "ambiguity_evidence_hit_at_k": bool(top5_set & expected_or_acceptable) if expected_or_acceptable else None,
                "ambiguity_forbidden_absent_at_k": forbidden_absent_at_k,
                "ambiguity_evidence_hit@5": bool(top5_set & expected_or_acceptable) if expected_or_acceptable else None,
                "ambiguity_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category in {"source_specific_temporal_query", "source_specific_exact_time"}:
        scores.update(
            {
                "source_temporal_hit_at_k": bool(top5_set & expected_or_acceptable),
                "source_forbidden_absent_at_k": forbidden_absent_at_k,
                "source_temporal_hit@5": bool(top5_set & expected_or_acceptable),
                "source_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category in {"metric_specific_query", "metric_specific_exact_time"}:
        scores.update(
            {
                "metric_temporal_hit_at_k": bool(top5_set & expected_or_acceptable),
                "metric_forbidden_absent_at_k": forbidden_absent_at_k,
                "metric_temporal_hit@5": bool(top5_set & expected_or_acceptable),
                "metric_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category == "cross_domain_temporal_comparison":
        required_sides = min(2, len(expected_or_acceptable)) if expected_or_acceptable else 0
        scores.update(
            {
                "both_side_coverage_at_k": (len(top5_set & expected_or_acceptable) >= required_sides) if required_sides else None,
                "comparison_forbidden_absent_at_k": forbidden_absent_at_k,
                "both_side_coverage@5": (len(top5_set & expected_or_acceptable) >= required_sides) if required_sides else None,
                "comparison_forbidden_absent@5": forbidden_absent_at_k,
            }
        )
    elif case.category == "multi_slot_temporal_coverage":
        required_slots = len(expected_or_acceptable)
        covered_slots = len(top5_set & expected_or_acceptable)
        scores.update(
            {
                "all_slot_coverage_at_k": (covered_slots >= required_slots) if required_slots else None,
                "multi_slot_forbidden_absent_at_k": forbidden_absent_at_k,
                "all_slot_coverage@5": (covered_slots >= required_slots) if required_slots else None,
                "multi_slot_forbidden_absent@5": forbidden_absent_at_k,
            }
        )

    primary_metrics = CATEGORY_PRIMARY_METRICS.get(case.category, ())
    primary_values = [scores.get(metric) for metric in primary_metrics]
    category_primary_pass = all(value is True for value in primary_values) if primary_values else None
    scores["category_primary_pass"] = category_primary_pass
    retrieval_reason = _retrieval_reason(category_primary_pass, primary_metrics, scores)

    return {
        "case_id": case.id,
        "category": case.category,
        "selected_evidence_ids": selected,
        "top_selected_evidence_id": selected[0] if selected else None,
        "expected_evidence_ids": list(case.expected_evidence_ids),
        "acceptable_evidence_ids": list(case.acceptable_evidence_ids),
        "forbidden_evidence_ids": list(case.forbidden_evidence_ids),
        "selected_expected_overlap": sorted(top5_set & expected),
        "selected_acceptable_overlap": sorted(top5_set & acceptable),
        "selected_forbidden_overlap": sorted(top5_set & forbidden),
        "retrieval_pass": category_primary_pass,
        "retrieval_pass_reason": retrieval_reason,
        "scores": scores,
        "warnings": warnings,
    }


def compare_reports(reports: list[dict[str, Any]], questions: dict[str, QuestionCase]) -> dict[str, Any]:
    left, right = reports[0], reports[1]
    left_cases = {case["case_id"]: case for case in left["case_reports"]}
    right_cases = {case["case_id"]: case for case in right["case_reports"]}
    common_ids = sorted(set(left_cases) & set(right_cases))
    all_ids = sorted(set(left_cases) | set(right_cases))
    skipped_mismatch = sorted(set(all_ids) - set(common_ids))

    pairwise = {
        "methods": [left.get("method"), right.get("method")],
        "benchmark_cases_total": len(questions),
        "common_evaluated_cases": len(common_ids),
        "left_only_evaluated_cases": sorted(set(left_cases) - set(right_cases)),
        "right_only_evaluated_cases": sorted(set(right_cases) - set(left_cases)),
        "skipped_mismatch_case_ids": skipped_mismatch,
        "generic_hit@5": _pairwise_counts(common_ids, left_cases, right_cases, "generic_hit@5"),
        "category_primary_pass": _pairwise_counts(common_ids, left_cases, right_cases, "category_primary_pass"),
        "forbidden_absent@5": _pairwise_counts(common_ids, left_cases, right_cases, "generic_forbidden_absent@5"),
        "per_category": {},
        "warnings": _pairwise_warnings(left, right),
    }

    for category in sorted({questions[case_id].category for case_id in common_ids}):
        ids = [case_id for case_id in common_ids if questions[case_id].category == category]
        pairwise["per_category"][category] = {
            "cases": len(ids),
            "generic_hit@5": _pairwise_counts(ids, left_cases, right_cases, "generic_hit@5"),
            "category_primary_pass": _pairwise_counts(ids, left_cases, right_cases, "category_primary_pass"),
            "forbidden_absent@5": _pairwise_counts(ids, left_cases, right_cases, "generic_forbidden_absent@5"),
        }
    return pairwise


def render_markdown(reports: list[dict[str, Any]], comparison: dict[str, Any] | None = None) -> str:
    """Render the public retrieval-only comparison report.

    This report intentionally explains category-primary scoring because generic
    Hit@k alone cannot represent forbidden-evidence or slot-coverage checks.
    """
    lines = [
        "# Layer 2 Retrieval-Only Evaluation",
        "",
        "Retrieval-only scoring is diagnostic. Generic Hit@k is retained for visibility, but category-specific metrics are the meaningful checks for Layer 2 temporal behavior. This is not a SOTA or publication-grade proof metric.",
        "",
        "| Method | Benchmark cases | Result rows | Evaluated | Skipped | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Embedding |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for report in reports:
        metrics = report["metrics"]
        embedding = f"{report.get('embedding_model') or '(unset)'} / {report.get('embedding_dim') or '(unset)'}"
        lines.append(
            f"| {report.get('method')} | {report['benchmark_cases_total']} | {report['result_rows_total']} | "
            f"{report['evaluated_cases']} | {report['skipped_cases']} | "
            f"{_fmt(metrics, 'generic_hit@1')} | {_fmt(metrics, 'generic_hit@5')} | "
            f"{_fmt(metrics, 'generic_forbidden_absent@5')} | {_fmt(metrics, 'category_primary_pass')} | {embedding} |"
        )

    for report in reports:
        lines.extend(
            [
                "",
                f"## {report.get('method')} Category Breakdown",
                "",
                "| Category | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Main diagnostics |",
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for category, metrics in report["category_metrics"].items():
            diagnostics = _render_category_diagnostics(category, metrics)
            lines.append(
                f"| {category} | {metrics.get('cases', 0)} | {_fmt(metrics, 'generic_hit@1')} | "
                f"{_fmt(metrics, 'generic_hit@5')} | {_fmt(metrics, 'generic_forbidden_absent@5')} | "
                f"{_fmt(metrics, 'category_primary_pass')} | {diagnostics} |"
            )
        if report["skip_reasons"]:
            lines.extend(["", "### Skipped cases", "", "| Reason | Count |", "|---|---:|"])
            for reason, count in report["skip_reasons"].items():
                lines.append(f"| {reason} | {count} |")
        if report["warning_counts"]:
            lines.extend(["", "### Warnings", "", "| Warning | Count |", "|---|---:|"])
            for warning, count in report["warning_counts"].items():
                lines.append(f"| {warning} | {count} |")
        lines.extend(_render_validation_cards(report))

    if comparison is not None:
        lines.extend(_render_pairwise_markdown(comparison))
    return "\n".join(lines)



def _render_validation_cards(report: dict[str, Any]) -> list[str]:
    # These cards use scored evaluator rows, not raw method rows.
    # Raw result rows only tell what the method selected; scoring lives here.
    lines = [
        "",
        "### Retrieval validation cards",
        "",
        "Each card reads `selected_evidence_ids` from the method result and then attaches the evaluator's expected/acceptable/forbidden overlaps. Answer text is not scored here.",
        "",
        "| Question ID | Category | Method | Selected evidence | Expected evidence | Acceptable evidence | Forbidden evidence | Expected overlap | Acceptable overlap | Forbidden overlap | Retrieval pass/fail reason | Top selected evidence |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for case in report.get("case_reports", []):
        lines.append(
            f"| {case['case_id']} | {case['category']} | {report.get('method')} | "
            f"{_join(case.get('selected_evidence_ids'))} | {_join(case.get('expected_evidence_ids'))} | "
            f"{_join(case.get('acceptable_evidence_ids'))} | {_join(case.get('forbidden_evidence_ids'))} | "
            f"{_join(case.get('selected_expected_overlap'))} | {_join(case.get('selected_acceptable_overlap'))} | "
            f"{_join(case.get('selected_forbidden_overlap'))} | {case.get('retrieval_pass_reason')} | "
            f"{case.get('top_selected_evidence_id') or '—'} |"
        )
    return lines


def _join(values: Any) -> str:
    # Keep markdown compact and deterministic.
    if not values:
        return "—"
    if isinstance(values, str):
        return values
    return ", ".join(str(item) for item in values)

def _render_pairwise_markdown(comparison: dict[str, Any]) -> list[str]:
    left, right = comparison["methods"]
    lines = [
        "",
        f"## Pairwise Same-Case Comparison: {left} vs {right}",
        "",
        f"Common evaluated cases: {comparison['common_evaluated_cases']} / {comparison['benchmark_cases_total']}",
        "",
        "| Metric | both_hit | left_only | right_only | neither | not_applicable | skipped/missing |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, key in (
        ("Generic Hit@5", "generic_hit@5"),
        ("Category primary pass", "category_primary_pass"),
        ("Forbidden absent@5", "forbidden_absent@5"),
    ):
        counts = comparison[key]
        lines.append(
            f"| {label} | {counts['both_hit']} | {counts['left_only']} | {counts['right_only']} | "
            f"{counts['neither']} | {counts['not_applicable']} | {len(comparison['skipped_mismatch_case_ids'])} |"
        )
    lines.extend(
        [
            "",
            "### Per-category pairwise deltas",
            "",
            "| Category | Cases | Generic Hit@5 left_only/right_only | Primary pass left_only/right_only | Forbidden left_only/right_only |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for category, stats in comparison["per_category"].items():
        gh = stats["generic_hit@5"]
        cp = stats["category_primary_pass"]
        fa = stats["forbidden_absent@5"]
        lines.append(
            f"| {category} | {stats['cases']} | {gh['left_only']}/{gh['right_only']} | "
            f"{cp['left_only']}/{cp['right_only']} | {fa['left_only']}/{fa['right_only']} |"
        )
    if comparison["warnings"]:
        lines.extend(["", "### Pairwise warnings", ""])
        for warning in comparison["warnings"]:
            lines.append(f"- {warning}")
    return lines


def _render_category_diagnostics(category: str, metrics: dict[str, Any]) -> str:
    wanted = CATEGORY_PRIMARY_METRICS.get(category, ())
    if category in {"partial_or_insufficient_evidence", "ambiguous_time_query"}:
        wanted = tuple(
            key
            for key in metrics
            if (key.startswith("fallback_") or key.startswith("ambiguity_"))
            and not key.endswith("_count")
            and not key.endswith("_denominator")
        )
    if not wanted:
        wanted = tuple(key for key in metrics if key not in {"cases", "generic_hit@1", "generic_hit@5", "generic_forbidden_absent@5"})[:3]
    rendered = [f"{key}={_fmt(metrics, key)}" for key in wanted if key in metrics]
    return "; ".join(rendered) if rendered else "—"


def _pairwise_counts(
    ids: list[str],
    left_cases: dict[str, dict[str, Any]],
    right_cases: dict[str, dict[str, Any]],
    metric: str,
) -> dict[str, int]:
    counts = {"both_hit": 0, "left_only": 0, "right_only": 0, "neither": 0, "not_applicable": 0}
    for case_id in ids:
        left_value = left_cases[case_id]["scores"].get(metric)
        right_value = right_cases[case_id]["scores"].get(metric)
        if left_value is None or right_value is None:
            counts["not_applicable"] += 1
        elif left_value and right_value:
            counts["both_hit"] += 1
        elif left_value:
            counts["left_only"] += 1
        elif right_value:
            counts["right_only"] += 1
        else:
            counts["neither"] += 1
    return counts


def _pairwise_warnings(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if left.get("evaluated_cases") != right.get("evaluated_cases"):
        warnings.append("methods evaluated different case counts; pairwise metrics use only common case IDs")
    for report in (left, right):
        for warning, count in report.get("warning_counts", {}).items():
            warnings.append(f"{report.get('method')}: {warning}={count}")
    return warnings


def _rates(acc: dict[str, dict[str, int]]) -> dict[str, Any]:
    output: dict[str, Any] = {"cases": acc.get("cases", {"num": 0, "den": 0})["den"]}
    for key in sorted(k for k in acc if k != "cases"):
        num = acc[key]["num"]
        den = acc[key]["den"]
        output[key] = num / den if den else None
        output[f"{key}_count"] = num
        output[f"{key}_denominator"] = den
    return output


def _fmt(metrics: dict[str, Any], key: str) -> str:
    value = metrics.get(key)
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _new_accumulator() -> dict[str, dict[str, int]]:
    return {"cases": {"num": 0, "den": 0}}


def _add_score_dict(acc: dict[str, dict[str, int]], scores: dict[str, bool | None]) -> None:
    acc["cases"]["den"] += 1
    for key, value in scores.items():
        if value is None:
            continue
        if key not in acc:
            acc[key] = {"num": 0, "den": 0}
        acc[key]["den"] += 1
        acc[key]["num"] += int(bool(value))


def _summarize_skip_reasons(skipped: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in skipped:
        counts[item["reason"]] += 1
    return dict(sorted(counts.items()))


def _is_malformed_wrong_year_question(question: str) -> bool:
    match = WRONG_TIME_RE.search(question)
    if not match:
        return False
    target = match.group("target")
    forbidden = match.group("forbidden")
    return target == forbidden


def _retrieval_reason(
    category_primary_pass: bool | None,
    primary_metrics: tuple[str, ...],
    scores: dict[str, bool | None],
) -> str:
    if category_primary_pass is True:
        return "pass: selected evidence satisfies category retrieval checks"
    if category_primary_pass is None:
        return "not_applicable: category is diagnostic-only for deterministic retrieval"
    failed = [metric for metric in primary_metrics if scores.get(metric) is not True]
    return "fail: " + ", ".join(failed)


if __name__ == "__main__":
    main()
