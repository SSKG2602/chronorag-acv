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

JUDGE_METRICS = [
    ("judge_overall_pass", "Judge Overall Pass"),
    ("strict_overall_pass", "Strict Overall Pass"),
    ("temporal_scope_correct", "Temporal Scope Correct"),
    ("factual_grounding", "Factual Grounding"),
    ("behavior_justified", "Behavior Justified"),
    ("transaction_time_clean", "Transaction-Time Clean"),
    ("no_overconfidence", "No Overconfidence"),
    ("behavior_label_accuracy", "Behavior Label Accuracy"),
    ("citation_grounding_accuracy", "Citation Grounding Accuracy"),
    ("schema_field_presence", "Schema Field Presence"),
    ("judge_infrastructure_failure_count", "Judge Infrastructure Failure Count"),
    ("judge_scored_runs", "Judge Scored Runs"),
    ("judge_unscored_runs", "Judge Unscored Runs"),
    ("judge_recovered_partial_json_count", "Judge Recovered Partial JSON Count"),
]


def metric_summary(results: list[dict[str, Any]], validator: str = "deterministic") -> dict[str, float]:
    scorable = [row for row in results if not row.get("infrastructure_failure")]
    if validator == "llm_judge":
        return _judge_metric_summary(scorable)
    if not scorable:
        return {key: 0.0 for key, _ in METRICS}
    return {
        key: float(mean(1.0 if row["validation"].get(key) else 0.0 for row in scorable))
        for key, _ in METRICS
    }


def _judge_metric_summary(results: list[dict[str, Any]]) -> dict[str, float]:
    if not results:
        summary = {key: 0.0 for key, _ in JUDGE_METRICS}
    else:
        summary = {
            "judge_overall_pass": float(mean(1.0 if row["validation"].get("judge_overall_pass") else 0.0 for row in results)),
            "strict_overall_pass": float(mean(1.0 if row["validation"].get("strict_overall_pass") else 0.0 for row in results)),
            "behavior_label_accuracy": float(mean(1.0 if row["validation"].get("diagnostics", {}).get("behavior_label_match") else 0.0 for row in results)),
            "citation_grounding_accuracy": float(mean(1.0 if row["validation"].get("diagnostics", {}).get("cited_ids_grounded") else 0.0 for row in results)),
            "schema_field_presence": float(mean(1.0 if row["validation"].get("diagnostics", {}).get("schema_fields_present") else 0.0 for row in results)),
        }
        for criterion in (
            "temporal_scope_correct",
            "factual_grounding",
            "behavior_justified",
            "transaction_time_clean",
            "no_overconfidence",
        ):
            summary[criterion] = float(mean(1.0 if row["validation"].get("criteria_scores", {}).get(criterion) else 0.0 for row in results))
    summary["overall_pass"] = summary.get("strict_overall_pass", 0.0)
    summary["judge_parse_failures"] = sum(int(row["validation"].get("judge_parse_failures", 0)) for row in results)
    summary["judge_provider_failures"] = sum(int(row["validation"].get("judge_provider_failures", 0)) for row in results)
    summary["judge_retry_attempts"] = sum(int(row["validation"].get("judge_retry_attempts", 0)) for row in results)
    summary["judge_infrastructure_failure_count"] = sum(
        1 for row in results if row["validation"].get("judge_infrastructure_failure")
    )
    summary["judge_scored_runs"] = sum(int(row["validation"].get("judge_scored_runs", 0)) for row in results)
    summary["judge_unscored_runs"] = sum(int(row["validation"].get("judge_unscored_runs", 0)) for row in results)
    summary["judge_recovered_partial_json_count"] = sum(
        int(row["validation"].get("judge_recovered_partial_json_count", 0)) for row in results
    )
    summary["judge_scored_case_count"] = sum(1 for row in results if int(row["validation"].get("judge_scored_runs", 0)) > 0)
    if summary["judge_scored_case_count"]:
        summary["strict_passes_per_judge_scored_case"] = float(
            mean(
                1.0 if row["validation"].get("strict_overall_pass") else 0.0
                for row in results
                if int(row["validation"].get("judge_scored_runs", 0)) > 0
            )
        )
    else:
        summary["strict_passes_per_judge_scored_case"] = 0.0
    return summary


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
                overall=summary.get("overall_pass", 0.0),
                behavior=summary.get("behavior_correct", summary.get("behavior_label_accuracy", 0.0)),
                evidence=summary.get("evidence_correct", summary.get("citation_grounding_accuracy", 0.0)),
                valid=summary.get("valid_time_correct", summary.get("temporal_scope_correct", 0.0)),
                tx=summary.get("transaction_time_not_misused", summary.get("transaction_time_clean", 0.0)),
                conflict=summary.get("conflict_warning_correct", 0.0),
                partial=summary.get("partial_refusal_correct", 0.0),
                clarify=summary.get("clarification_correct", 0.0),
                cross=summary.get("cross_domain_dependency_correct", 0.0),
                calls=payload.get("estimated_calls", 0),
                latency=payload.get("latency_ms", 0.0),
            )
        )
    lines.append("")
    lines.append("Layer 2 is designed to compare methods under the same corpus, questions, model, and validator.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _method_markdown(payload: dict[str, Any]) -> str:
    if payload.get("validator") == "llm_judge":
        return _judge_method_markdown(payload)
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
        f"- Provider output-contract failures: {payload.get('summary', {}).get('provider_output_contract_failure_count', 0)}",
        f"- Answer JSON recovered count: {payload.get('summary', {}).get('answer_json_recovered_count', 0)}",
        f"- Retry attempts: {payload.get('summary', {}).get('retry_attempts_total', 0)}",
        "",
        "Provider output-contract failures are reported separately from retrieval or reasoning failures.",
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


def _judge_method_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# Layer 2 Results: {payload['method']}",
        "",
        "This is an optional LLM-judge validation report, not a SOTA or publication-grade claim.",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Validator: `llm_judge`",
        f"- Corpus rows: {payload['corpus_rows']}",
        f"- Questions: {payload['question_count']}",
        f"- Top-k: {payload.get('top_k', 'n/a')}",
        f"- Scored cases: {summary.get('scored_case_count', len(payload.get('results', [])))}",
        f"- Provider/infrastructure failures: {summary.get('infrastructure_failure_count', 0)}",
        f"- Judge parse failures: {summary.get('judge_parse_failures', 0)}",
        f"- Judge provider failures: {summary.get('judge_provider_failures', 0)}",
        f"- Judge retry attempts: {summary.get('judge_retry_attempts', 0)}",
        f"- Judge infrastructure failure count: {summary.get('judge_infrastructure_failure_count', 0)}",
        f"- Judge scored runs: {summary.get('judge_scored_runs', 0)}",
        f"- Judge unscored runs: {summary.get('judge_unscored_runs', 0)}",
        f"- Judge recovered partial JSON count: {summary.get('judge_recovered_partial_json_count', 0)}",
        f"- Judge-scored cases / total cases: {summary.get('judge_scored_case_count', 0)} / {payload['question_count']}",
        f"- Strict passes / total cases: {summary.get('strict_overall_pass', 0.0):.2f}",
        f"- Strict passes / judge-scored cases: {summary.get('strict_passes_per_judge_scored_case', 0.0):.2f}",
        f"- Provider output-contract failures: {summary.get('provider_output_contract_failure_count', 0)}",
        f"- Answer JSON recovered count: {summary.get('answer_json_recovered_count', 0)}",
        "",
        "Unscored judge-infrastructure cases are not semantic failures.",
        "Provider output-contract failures are reported separately from retrieval or reasoning failures.",
        "ChronoRAG-vs-metadata comparison is valid only when both methods use the same corpus, question set, model, and judge settings.",
        "",
        "| Metric | Score |",
        "|---|---:|",
    ]
    if summary.get("judge_unscored_runs", 0) > summary.get("judge_scored_runs", 0):
        lines.extend(
            [
                "",
                "**LLM judge result is not valid because judge infrastructure failures dominate.**",
                "",
            ]
        )
    for key, label in JUDGE_METRICS:
        lines.append(f"| {label} | {summary.get(key, 0.0):.2f} |")
    lines.extend(
        [
            f"| Judge Parse Failures | {summary.get('judge_parse_failures', 0)} |",
            f"| Judge Provider Failures | {summary.get('judge_provider_failures', 0)} |",
            f"| Judge Retry Attempts | {summary.get('judge_retry_attempts', 0)} |",
            "",
            "## Failure Analysis",
            "",
        ]
    )
    failures = [row for row in payload["results"] if not row["validation"].get("strict_overall_pass")]
    if failures:
        for row in failures:
            validation = row["validation"]
            failed_criteria = [
                key for key, value in validation.get("criteria_scores", {}).items() if not value
            ]
            failed_diagnostics = [
                key for key, value in validation.get("diagnostics", {}).items() if not value
            ]
            infra = bool(validation.get("judge_infrastructure_failure"))
            if infra:
                reason = "judge infrastructure failure"
            elif failed_criteria:
                reason = "semantic criteria failure"
            else:
                reason = "strict diagnostic failure"
            lines.append(
                "- `{case}`: judge_overall={judge}; strict={strict}; "
                "reason={reason}; criteria_failed={criteria}; diagnostics_failed={diagnostics}; "
                "judge_parse_failures={parse}; judge_provider_failures={provider}; "
                "judge_scored_runs={scored}; judge_unscored_runs={unscored}".format(
                    case=row["case_id"],
                    judge=validation.get("judge_overall_pass"),
                    strict=validation.get("strict_overall_pass"),
                    reason=reason,
                    criteria=", ".join(failed_criteria) or "none",
                    diagnostics=", ".join(failed_diagnostics) or "none",
                    parse=validation.get("judge_parse_failures", 0),
                    provider=validation.get("judge_provider_failures", 0),
                    scored=validation.get("judge_scored_runs", 0),
                    unscored=validation.get("judge_unscored_runs", 0),
                )
            )
    else:
        lines.append("- No strict failures in this run.")
    lines.extend(
        [
            "",
            "| Case | Status | Judge Pass | Strict Pass | Criteria Passed | Diagnostics Failed |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in payload["results"]:
        validation = row["validation"]
        failed_diagnostics = [
            key for key, value in validation.get("diagnostics", {}).items() if not value
        ]
        lines.append(
            f"| {row['case_id']} | {row.get('status', 'completed')} | {validation.get('judge_overall_pass')} | {validation.get('strict_overall_pass')} | {validation.get('criteria_passed', 0)} | {', '.join(failed_diagnostics)} |"
        )
    return "\n".join(lines) + "\n"
