"""CLI entry point for the Layer 2B semantic judge.

The judge maps generated Layer 2B answers into an independent
semantic-evaluation pass while preserving deterministic hard-contract results.
It is a secondary evaluation layer, not a replacement for strict contract
scoring.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.layer2b_qa import (
    DEFAULT_CORPUS_PATH,
    DEFAULT_QA_PATH,
    RESULTS_ROOT,
    append_jsonl_row,
    build_evidence_lookup,
    load_existing_results,
    load_layer2b_cases,
    load_selected_corpus,
    sleep_between_vertex_requests,
)
from benchmarks.layer2_crossdomain.llm_judge import evidence_cards_from_rows, run_layer2b_judge


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Layer 2B LLM judge over existing answer JSONL results.")
    parser.add_argument("--mode", choices=["dry_run", "vertex"], default="dry_run")
    parser.add_argument("--input-results", required=True)
    parser.add_argument("--qa", default=str(DEFAULT_QA_PATH))
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS_PATH))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--result-suffix", default="default")
    parser.add_argument("--judge-runs", type=int, default=1)
    parser.add_argument("--judge-temperature", type=float, default=0.0)
    parser.add_argument("--judge-max-output-tokens", type=int, default=5000)
    parser.add_argument("--judge-request-sleep-seconds", type=float, default=10.0)
    parser.add_argument("--judge-retry-max-attempts", type=int, default=4)
    parser.add_argument("--judge-retry-base-sleep-seconds", type=float, default=8.0)
    parser.add_argument("--judge-retry-max-sleep-seconds", type=float, default=90.0)
    parser.add_argument("--judge-json-retry-max-attempts", type=int, default=3)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    _validate_args(args)

    jsonl_path, md_path = result_paths(args.result_suffix)
    existing_judge_rows = load_existing_results(jsonl_path) if args.resume else []
    completed_ids = _completed_judge_question_ids(existing_judge_rows)

    answer_rows = load_existing_results(Path(args.input_results))
    cases = {case.question_id: case for case in load_layer2b_cases(args.qa)}
    corpus_lookup = build_evidence_lookup(load_selected_corpus(args.corpus))

    selected_rows = answer_rows[args.start_index :]
    if args.resume:
        selected_rows = [row for row in selected_rows if str(row.get("question_id")) not in completed_ids]
    if args.limit is not None:
        selected_rows = selected_rows[: args.limit]

    print(f"Mode: {args.mode}")
    print(f"Input results: {args.input_results}")
    print(f"Cases selected: {len(selected_rows)}")
    print(f"Output JSONL: {jsonl_path}")
    print(f"Output Markdown: {md_path}")
    if args.mode == "vertex":
        print(f"Judge runs per case: {args.judge_runs}")
        print(f"Judge sleep seconds: {args.judge_request_sleep_seconds}")

    provider = _build_vertex_provider() if args.mode == "vertex" else None
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    output_mode = "a" if args.resume else "w"
    all_rows = list(existing_judge_rows)
    with jsonl_path.open(output_mode, encoding="utf-8") as handle:
        for index, answer_row in enumerate(selected_rows, start=1):
            question_id = str(answer_row.get("question_id") or "")
            print(f"[{index}/{len(selected_rows)}] {question_id}", flush=True)
            row = _build_mapped_result(
                answer_row=answer_row,
                cases=cases,
                corpus_lookup=corpus_lookup,
                mode=args.mode,
                input_results=args.input_results,
                result_suffix=args.result_suffix,
            )
            if row["status"] == "mapping_error" or args.mode == "dry_run":
                output_row = _strip_internal_fields(row)
                append_jsonl_row(handle, output_row)
                all_rows.append(output_row)
                if args.fail_fast and row["status"] == "mapping_error":
                    raise SystemExit(f"Layer 2B judge mapping failed for {question_id}: {row['failure_reasons']}")
                continue

            started = time.perf_counter()
            try:
                judge = run_layer2b_judge(
                    row["case"],
                    row["answer"],
                    row["evidence_cards"],
                    provider,
                    deterministic_validation=row["deterministic_validation"],
                    runs=args.judge_runs,
                    temperature=args.judge_temperature,
                    max_output_tokens=args.judge_max_output_tokens,
                    request_sleep_seconds=args.judge_request_sleep_seconds,
                    retry_max_attempts=args.judge_retry_max_attempts,
                    retry_base_sleep_seconds=args.judge_retry_base_sleep_seconds,
                    retry_max_sleep_seconds=args.judge_retry_max_sleep_seconds,
                    json_retry_max_attempts=args.judge_json_retry_max_attempts,
                )
                row = _finalize_vertex_result(row, judge, (time.perf_counter() - started) * 1000.0)
            except Exception as exc:
                row = _judge_exception_result(row, exc, (time.perf_counter() - started) * 1000.0)

            append_jsonl_row(handle, _strip_internal_fields(row))
            all_rows.append(_strip_internal_fields(row))
            if args.fail_fast and row["status"] != "completed":
                raise SystemExit(f"Layer 2B judge failed for {question_id}: {row['failure_reasons']}")
            if index < len(selected_rows):
                sleep_between_vertex_requests(args.judge_request_sleep_seconds)

    write_markdown_summary(all_rows, md_path, mode=args.mode, result_suffix=args.result_suffix, input_results=args.input_results)
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {md_path}")


def result_paths(result_suffix: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", result_suffix):
        raise ValueError("--result-suffix may contain only letters, numbers, underscore, and hyphen")
    base = RESULTS_ROOT / f"layer2b_judge_{result_suffix}_results"
    return base.with_suffix(".jsonl"), base.with_suffix(".md")


def write_markdown_summary(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    mode: str,
    result_suffix: str,
    input_results: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_markdown_summary(rows, mode=mode, result_suffix=result_suffix, input_results=input_results),
        encoding="utf-8",
    )


def render_markdown_summary(rows: list[dict[str, Any]], *, mode: str, result_suffix: str, input_results: str) -> str:
    """Render judge metrics while keeping hard-contract and semantic scores separate."""
    deterministic_pass = sum(1 for row in rows if row.get("deterministic_overall_contract_pass") is True)
    judge_pass = sum(1 for row in rows if (row.get("judge_validation") or {}).get("overall_judge_pass") is True)
    combined_pass = sum(1 for row in rows if row.get("combined_pass") is True)
    mapping_errors = sum(1 for row in rows if row.get("status") == "mapping_error")
    judge_errors = sum(1 for row in rows if row.get("status") == "judge_error")
    judge_parse_failures = sum(int((row.get("judge_validation") or {}).get("judge_parse_failures", 0)) for row in rows)
    judge_provider_failures = sum(int((row.get("judge_validation") or {}).get("judge_provider_failures", 0)) for row in rows)
    judge_retry_attempts = sum(int((row.get("judge_validation") or {}).get("judge_retry_attempts", 0)) for row in rows)

    lines = [
        "# Layer 2B LLM Judge Results",
        "",
        "This is a strict-but-fair Layer 2B answer-quality judge report, not a SOTA or publication-grade claim.",
        "",
        f"- Mode: `{mode}`",
        f"- Input answer results: `{input_results}`",
        f"- Cases: {len(rows)}",
        f"- Result suffix: `{result_suffix}`",
        f"- Mapping errors: {mapping_errors}",
        f"- Judge errors: {judge_errors}",
        f"- Judge parse failures: {judge_parse_failures}",
        f"- Judge provider failures: {judge_provider_failures}",
        f"- Judge retry attempts: {judge_retry_attempts}",
        f"- Deterministic hard-contract pass: {deterministic_pass} / {len(rows)}",
        f"- LLM judge pass: {'n/a' if mode == 'dry_run' else f'{judge_pass} / {len(rows)}'}",
        f"- Combined pass: {'n/a' if mode == 'dry_run' else f'{combined_pass} / {len(rows)}'}",
        "",
    ]
    if mode == "dry_run":
        lines.extend(
            [
                "Dry run validates result, case, and evidence mapping only. It does not call Vertex and does not evaluate generated answer quality.",
                "",
            ]
        )
    lines.extend(
        [
            "| Question ID | Type | Expected Behavior | Status | Deterministic Pass | Judge Pass | Combined Pass | Severity | Failure Reasons |",
            "|---|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        judge = row.get("judge_validation") or {}
        lines.append(
            "| {qid} | {qtype} | {behavior} | {status} | {det} | {judge_pass} | {combined} | {severity} | {failures} |".format(
                qid=row.get("question_id", ""),
                qtype=row.get("question_type", ""),
                behavior=row.get("expected_answer_behavior", ""),
                status=row.get("status", ""),
                det=_format_bool(row.get("deterministic_overall_contract_pass")),
                judge_pass=_format_bool(judge.get("overall_judge_pass")),
                combined=_format_bool(row.get("combined_pass")),
                severity=judge.get("severity", "n/a"),
                failures=", ".join(str(item) for item in row.get("failure_reasons") or judge.get("failure_reasons") or []),
            )
        )
    return "\n".join(lines) + "\n"


def _build_mapped_result(
    *,
    answer_row: dict[str, Any],
    cases: dict[str, Any],
    corpus_lookup: dict[str, Any],
    mode: str,
    input_results: str,
    result_suffix: str,
) -> dict[str, Any]:
    """Map one answer-result row to the case, evidence, and judge input shape."""
    question_id = str(answer_row.get("question_id") or "")
    case = cases.get(question_id)
    evidence_rows, missing_evidence_ids = _evidence_rows_for_result(answer_row, corpus_lookup)
    answer = answer_row.get("answer")
    deterministic_validation = dict(answer_row.get("validation") or {})
    deterministic_pass = deterministic_validation.get("overall_contract_pass") is True
    failure_reasons: list[str] = []
    if case is None:
        failure_reasons.append("missing_layer2b_case")
    if not isinstance(answer, dict):
        failure_reasons.append("missing_answer_payload")
    if missing_evidence_ids:
        failure_reasons.append("missing_evidence_rows: " + ", ".join(missing_evidence_ids))

    base = {
        "benchmark": "layer2b_manual_qa_judge",
        "mode": mode,
        "input_results": input_results,
        "result_suffix": result_suffix,
        "question_id": question_id,
        "question": answer_row.get("question", ""),
        "question_type": answer_row.get("question_type", ""),
        "expected_answer_behavior": answer_row.get("expected_answer_behavior", ""),
        "expected_evidence_ids": answer_row.get("expected_evidence_ids", []),
        "selected_evidence_ids": answer_row.get("selected_evidence_ids", []),
        "answer": answer if isinstance(answer, dict) else {},
        "deterministic_validation": deterministic_validation,
        "deterministic_overall_contract_pass": deterministic_pass,
        "judge_validation": _dry_run_judge_validation() if mode == "dry_run" else {},
        "combined_pass": None,
        "failure_reasons": failure_reasons,
    }
    if case is not None:
        base.update(
            {
                "question": case.question,
                "question_type": case.question_type,
                "expected_answer_behavior": case.answer_behavior,
                "expected_evidence_ids": case.expected_evidence_ids,
                "expected_valid_time": case.expected_valid_time,
                "reference_answer": case.reference_answer,
                "source_family": case.source_family,
                "case": case,
            }
        )
    base["evidence_cards"] = evidence_cards_from_rows(evidence_rows)
    if failure_reasons:
        base["status"] = "mapping_error"
        return _strip_internal_fields(base)
    base["status"] = "completed" if mode == "dry_run" else "pending"
    return base


def _finalize_vertex_result(row: dict[str, Any], judge: dict[str, Any], latency_ms: float) -> dict[str, Any]:
    """Attach Vertex judge output without replacing deterministic validation."""
    deterministic_pass = row.get("deterministic_overall_contract_pass") is True
    judge_pass = judge.get("overall_judge_pass") is True
    row["judge_validation"] = judge
    row["combined_pass"] = deterministic_pass and judge_pass
    row["latency_ms"] = round(latency_ms, 2)
    row["status"] = "judge_error" if judge.get("judge_infrastructure_failure") else "completed"
    row["failure_reasons"] = list(judge.get("failure_reasons") or [])
    return row


def _judge_exception_result(row: dict[str, Any], error: Exception, latency_ms: float) -> dict[str, Any]:
    row["judge_validation"] = {
        "overall_judge_pass": False,
        "severity": "critical",
        "failure_reasons": ["judge_exception"],
        "brief_rationale": str(error)[:160],
        "judge_infrastructure_failure": True,
        "judge_parse_failures": 0,
        "judge_provider_failures": 1,
        "judge_retry_attempts": 0,
        "judge_runs": 0,
        "judge_scored_runs": 0,
        "judge_unscored_runs": 0,
        "judge_recovered_partial_json_count": 0,
    }
    row["combined_pass"] = False
    row["latency_ms"] = round(latency_ms, 2)
    row["status"] = "judge_error"
    row["failure_reasons"] = ["judge_exception"]
    return row


def _evidence_rows_for_result(answer_row: dict[str, Any], corpus_lookup: dict[str, Any]) -> tuple[list[Any], list[str]]:
    rows: list[Any] = []
    missing: list[str] = []
    seen: set[str] = set()
    for evidence_id in answer_row.get("selected_evidence_ids") or []:
        evidence_id = str(evidence_id)
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        row = corpus_lookup.get(evidence_id)
        if row is None:
            missing.append(evidence_id)
        else:
            rows.append(row)
    return rows, missing


def _strip_internal_fields(row: dict[str, Any]) -> dict[str, Any]:
    stripped = dict(row)
    stripped.pop("case", None)
    stripped.pop("evidence_cards", None)
    return stripped


def _dry_run_judge_validation() -> dict[str, Any]:
    """Return the explicit non-scoring judge payload used for dry runs."""
    return {
        "overall_judge_pass": None,
        "severity": "not_applicable",
        "failure_reasons": ["judge_not_called_in_dry_run"],
        "brief_rationale": "Judge was not called in dry run.",
        "judge_infrastructure_failure": False,
        "judge_parse_failures": 0,
        "judge_provider_failures": 0,
        "judge_retry_attempts": 0,
        "judge_runs": 0,
        "judge_scored_runs": 0,
        "judge_unscored_runs": 0,
        "judge_recovered_partial_json_count": 0,
    }


def _completed_judge_question_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("question_id"))
        for row in rows
        if row.get("question_id") and row.get("status") == "completed"
    }


def _validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit < 0:
        raise SystemExit("--limit must be non-negative.")
    if args.start_index < 0:
        raise SystemExit("--start-index must be non-negative.")
    if args.judge_runs <= 0:
        raise SystemExit("--judge-runs must be positive.")
    if not Path(args.input_results).exists():
        raise SystemExit(f"--input-results does not exist: {args.input_results}")


def _build_vertex_provider() -> Any:
    from core.generator.vertex_provider import VertexGeminiProvider

    return VertexGeminiProvider()


def _format_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"


if __name__ == "__main__":
    main()
