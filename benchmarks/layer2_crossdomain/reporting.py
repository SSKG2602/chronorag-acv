from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


METRICS = [
    ("overall_pass", "Overall Pass"),
    ("behavior_correct", "Behavior Correct"),
    ("evidence_correct", "Evidence Correct"),
    ("valid_time_correct", "Valid-Time Correct"),
    ("transaction_time_not_misused", "Transaction-Time Trap Avoided"),
    ("conflict_warning_correct", "Conflict Warning Correct"),
    ("partial_refusal_correct", "Partial/Refusal Correct"),
    ("clarification_correct", "Clarification Correct"),
    ("cross_domain_dependency_correct", "Cross-Domain Dependency Correct"),
]


def metric_summary(results: list[dict[str, Any]]) -> dict[str, float]:
    scorable = [row for row in results if not row.get("infrastructure_failure")]
    if not scorable:
        return {key: 0.0 for key, _ in METRICS}
    return {
        key: float(mean(1.0 if row["validation"].get(key) else 0.0 for row in scorable))
        for key, _ in METRICS
    }


def write_method_results(
    payload: dict[str, Any],
    json_path: Path,
    md_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_method_markdown(payload), encoding="utf-8")


def write_comparison_report(method_payloads: list[dict[str, Any]], md_path: Path) -> None:
    lines = [
        "# Layer 2 Cross-Domain Comparison",
        "",
        "This is a framework smoke report, not a superiority claim.",
        "",
        "| Method | Corpus Rows | Questions | Scored | Infra Failures | Avg Evidence | Truncated | Overall Pass | Behavior | Evidence | Valid-Time | Tx Trap | Conflict | Partial/Refusal | Clarification | Cross-Domain | Estimated Calls | Latency ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for payload in method_payloads:
        summary = payload["summary"]
        lines.append(
            "| {method} | {rows} | {questions} | {scored} | {infra} | {avg:.1f} | {truncated} | {overall:.2f} | {behavior:.2f} | {evidence:.2f} | {valid:.2f} | {tx:.2f} | {conflict:.2f} | {partial:.2f} | {clarify:.2f} | {cross:.2f} | {calls} | {latency:.1f} |".format(
                method=payload["method"],
                rows=payload["corpus_rows"],
                questions=payload["question_count"],
                scored=summary.get("scored_case_count", payload["question_count"]),
                infra=summary.get("infrastructure_failure_count", 0),
                avg=payload.get("average_selected_evidence", 0.0),
                truncated=payload.get("prompt_truncation_count", 0),
                overall=summary["overall_pass"],
                behavior=summary["behavior_correct"],
                evidence=summary["evidence_correct"],
                valid=summary["valid_time_correct"],
                tx=summary["transaction_time_not_misused"],
                conflict=summary["conflict_warning_correct"],
                partial=summary["partial_refusal_correct"],
                clarify=summary["clarification_correct"],
                cross=summary["cross_domain_dependency_correct"],
                calls=payload.get("estimated_calls", 0),
                latency=payload.get("latency_ms", 0.0),
            )
        )
    lines.append("")
    lines.append("Layer 2 is designed to compare methods under the same corpus, questions, model, and validator.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _method_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Layer 2 Results: {payload['method']}",
        "",
        "This is a controlled framework result, not a SOTA or publication-grade claim.",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Corpus rows: {payload['corpus_rows']}",
        f"- Questions: {payload['question_count']}",
        f"- Top-k: {payload.get('top_k', 'n/a')}",
        f"- Prompt truncation count: {payload.get('prompt_truncation_count', 0)}",
        f"- Estimated Vertex calls: {payload.get('estimated_calls', 0)}",
        f"- Result suffix: `{payload.get('result_suffix') or 'default'}`",
        f"- Scored cases: {payload.get('summary', {}).get('scored_case_count', len(payload.get('results', [])))}",
        f"- Provider/infrastructure failures: {payload.get('summary', {}).get('infrastructure_failure_count', 0)}",
        f"- Provider errors: {payload.get('summary', {}).get('provider_error_count', 0)}",
        f"- Retry attempts: {payload.get('summary', {}).get('retry_attempts_total', 0)}",
        "",
        "| Metric | Score |",
        "|---|---:|",
    ]
    for key, label in METRICS:
        lines.append(f"| {label} | {payload['summary'][key]:.2f} |")
    lines.extend(["", "## Failure Analysis", ""])
    failures = [row for row in payload["results"] if not row["validation"]["overall_pass"]]
    if failures:
        for row in failures:
            status = row.get("status", "completed")
            lines.append(f"- `{row['case_id']}` [{status}]: {', '.join(row['validation'].get('failure_reasons', []))}")
    else:
        lines.append("- No failures in this run.")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Fixture results only prove that the framework runs.",
            "- Full Layer 2 claims require the future 5000-row / 200-question benchmark.",
            "- No SOTA, production, or publication-grade claim is made here.",
            "",
            "| Case | Status | Behavior | Selected Evidence | Cited Evidence | Pass | Failures |",
            "|---|---|---|---|---|---:|---|",
        ]
    )
    for row in payload["results"]:
        validation = row["validation"]
        cited = ", ".join(row["answer"].get("cited_evidence_ids", []))
        selected = ", ".join(row.get("selected_evidence_ids", []))
        failures = ", ".join(validation.get("failure_reasons", []))
        lines.append(
            f"| {row['case_id']} | {row.get('status', 'completed')} | {row['answer'].get('behavior', '')} | {selected} | {cited} | {validation['overall_pass']} | {failures} |"
        )
    return "\n".join(lines) + "\n"
