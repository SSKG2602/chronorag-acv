from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
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
    Layer2BQACase,
    append_jsonl_row,
    build_evidence_lookup,
    load_existing_results,
    load_layer2b_cases,
    load_selected_corpus,
    parse_answer_json,
    sleep_between_vertex_requests,
    validate_answer_contract,
)
from benchmarks.layer2_crossdomain.llm_judge import evidence_cards_from_rows, run_layer2b_judge
from benchmarks.layer2_crossdomain.vertex_retry import call_with_backoff
from chronorag.stdcomp.bm25_baseline import run_bm25_baseline
from chronorag.stdcomp.date_filter_baseline import run_date_filter_baseline
from chronorag.stdcomp.dense_baseline import DEFAULT_MODEL as DEFAULT_DENSE_MODEL
from chronorag.stdcomp.dense_baseline import run_dense_baseline
from core.generator.vertex_provider import VertexGeminiProvider


DEFAULT_OUT_DIR = Path("chronorag/stdcomp/results/qa50_llm_baselines")
DEFAULT_PAPER_DIR = Path("docs/paper_assets")
DEFAULT_VERTEX_MODEL = os.getenv("VERTEX_MODEL_ID", "gemini-2.5-flash")
METHOD_ORDER = ["bm25", "dense", "date_filter"]
METHOD_LABELS = {
    "bm25": "BM25 + LLM",
    "dense": "Dense-only + LLM",
    "date_filter": "Date-filter RAG + LLM",
}
OUTPUT_PREFIX = {
    "bm25": "bm25",
    "dense": "dense",
    "date_filter": "date_filter",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run QA50 LLM answer generation for standard retrieval baselines only."
    )
    parser.add_argument("--qa", default=str(DEFAULT_QA_PATH))
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS_PATH))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--methods", default="bm25,dense,date_filter")
    parser.add_argument("--sleep-seconds", type=float, default=5.0)
    parser.add_argument("--max-cases", type=int, default=50)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--paper-assets-dir", default=str(DEFAULT_PAPER_DIR))
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    parser.add_argument("--model", default=DEFAULT_VERTEX_MODEL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=5000)
    parser.add_argument("--retry-max-attempts", type=int, default=5)
    parser.add_argument("--retry-base-sleep-seconds", type=float, default=5.0)
    parser.add_argument("--retry-max-sleep-seconds", type=float, default=90.0)
    parser.add_argument("--dense-model", default=DEFAULT_DENSE_MODEL)
    parser.add_argument("--dense-batch-size", type=int, default=64)
    parser.add_argument("--skip-judge", action="store_true", help="Skip the Layer 2B LLM judge; deterministic validator still runs.")
    parser.add_argument("--judge-runs", type=int, default=1)
    parser.add_argument("--judge-temperature", type=float, default=0.0)
    parser.add_argument("--judge-max-output-tokens", type=int, default=5000)
    parser.add_argument("--judge-retry-max-attempts", type=int, default=4)
    parser.add_argument("--judge-retry-base-sleep-seconds", type=float, default=8.0)
    parser.add_argument("--judge-retry-max-sleep-seconds", type=float, default=90.0)
    parser.add_argument("--judge-json-retry-max-attempts", type=int, default=3)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    selected_methods = parse_methods(args.methods)
    validate_args(args, selected_methods)
    preflight_vertex(args)

    qa_path = Path(args.qa)
    corpus_path = Path(args.corpus)
    out_dir = Path(args.out_dir)
    paper_dir = Path(args.paper_assets_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = load_layer2b_cases(qa_path)
    cases = cases[args.start_index :]
    cases = cases[: args.max_cases]
    corpus = load_selected_corpus(corpus_path)
    if len(corpus) != 5000:
        raise SystemExit(f"Expected full Layer 2 corpus to contain 5000 rows, found {len(corpus)} at {corpus_path}")
    if len(load_layer2b_cases(qa_path)) != 50:
        raise SystemExit(f"Expected QA file to contain 50 cases: {qa_path}")

    corpus_lookup = build_evidence_lookup(corpus)
    question_cases = [case.to_question_case() for case in cases]
    retrieval_payloads = build_retrieval_payloads(
        selected_methods,
        corpus,
        question_cases,
        top_k=args.top_k,
        dense_model=args.dense_model,
        dense_batch_size=args.dense_batch_size,
        cache_dir=out_dir / "cache",
        corpus_fingerprint=sha256(corpus_path),
    )

    manifest = build_manifest(args, selected_methods, qa_path, corpus_path, cases, corpus)
    write_json(out_dir / "qa50_llm_run_manifest.json", manifest)

    answer_provider = VertexGeminiProvider(project=args.project, location=args.location, model_id=args.model)
    judge_provider = None if args.skip_judge else VertexGeminiProvider(project=args.project, location=args.location, model_id=args.model)
    all_method_rows: dict[str, list[dict[str, Any]]] = {}

    for method in selected_methods:
        rows = run_method(
            method=method,
            cases=cases,
            retrieval_payload=retrieval_payloads[method],
            corpus_lookup=corpus_lookup,
            answer_provider=answer_provider,
            judge_provider=judge_provider,
            args=args,
            out_dir=out_dir,
        )
        all_method_rows[method] = rows
        metrics = compute_method_metrics(method, rows)
        write_json(out_dir / f"{OUTPUT_PREFIX[method]}_llm_qa50_metrics.json", metrics)

    comparison_rows = [comparison_row(method, compute_method_metrics(method, all_method_rows[method])) for method in selected_methods]
    write_comparison_csv(out_dir / "qa50_llm_baseline_comparison.csv", comparison_rows)
    write_comparison_md(out_dir / "qa50_llm_baseline_comparison.md", comparison_rows, manifest)
    if paper_dir.exists():
        write_comparison_csv(paper_dir / "qa50_llm_baseline_comparison.csv", comparison_rows)
        write_comparison_md(paper_dir / "qa50_llm_baseline_comparison.md", comparison_rows, manifest)

    print(render_comparison_table(comparison_rows))
    print(f"Wrote QA50 LLM baseline outputs under {out_dir}")
    if paper_dir.exists():
        print(f"Wrote paper assets under {paper_dir}")


def run_method(
    *,
    method: str,
    cases: list[Layer2BQACase],
    retrieval_payload: dict[str, Any],
    corpus_lookup: dict[str, Any],
    answer_provider: VertexGeminiProvider,
    judge_provider: VertexGeminiProvider | None,
    args: argparse.Namespace,
    out_dir: Path,
) -> list[dict[str, Any]]:
    output_path = out_dir / f"{OUTPUT_PREFIX[method]}_llm_qa50_outputs.jsonl"
    existing_rows = load_existing_results(output_path) if args.resume and output_path.exists() else []
    completed_ids = {str(row.get("question_id")) for row in existing_rows if row.get("question_id")}
    if output_path.exists() and not args.resume and not args.force:
        raise SystemExit(f"Output already exists; use --resume or --force: {output_path}")
    output_mode = "a" if args.resume and not args.force else "w"
    all_rows = [] if args.force else list(existing_rows)
    retrieval_by_case = {str(row.get("case_id")): row for row in retrieval_payload.get("results") or []}
    ordered = [case for case in cases if case.question_id not in completed_ids]

    print(f"Method: {METHOD_LABELS[method]}")
    print(f"Cases selected: {len(ordered)}")
    print(f"Output JSONL: {output_path}")
    with output_path.open(output_mode, encoding="utf-8") as handle:
        for index, case in enumerate(ordered, start=1):
            print(f"[{method} {index}/{len(ordered)}] {case.question_id}", flush=True)
            retrieval_row = retrieval_by_case.get(case.question_id)
            if retrieval_row is None:
                row = build_missing_retrieval_result(method, case, args)
                append_jsonl_row(handle, row)
                all_rows.append(row)
                if args.fail_fast:
                    raise SystemExit(f"Missing retrieval row for {method} {case.question_id}")
                continue

            evidence_rows = rows_for_selected_evidence(retrieval_row, corpus_lookup)
            started = time.perf_counter()
            try:
                prompt = build_baseline_layer2b_prompt(case, evidence_rows)
                raw_response = run_vertex_prompt_with_provider(
                    answer_provider,
                    prompt,
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                    retry_max_attempts=args.retry_max_attempts,
                    retry_base_sleep_seconds=args.retry_base_sleep_seconds,
                    retry_max_sleep_seconds=args.retry_max_sleep_seconds,
                    label=f"{method} answer case={case.question_id}",
                )
                answer_payload, parse_diagnostics = parse_answer_json(raw_response)
                row = build_answer_result(
                    method,
                    case,
                    retrieval_row,
                    evidence_rows,
                    args,
                    raw_response=raw_response,
                    answer_payload=answer_payload,
                    parse_diagnostics=parse_diagnostics,
                    corpus_lookup=corpus_lookup,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                )
            except Exception as exc:
                row = build_provider_error_result(
                    method,
                    case,
                    retrieval_row,
                    evidence_rows,
                    args,
                    error=exc,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                )

            if judge_provider is not None and row.get("status") == "completed" and isinstance(row.get("answer"), dict):
                if args.sleep_seconds > 0:
                    sleep_between_vertex_requests(args.sleep_seconds)
                row = attach_judge_result(row, case, evidence_rows, judge_provider, args)
            else:
                row["judge_validation"] = judge_not_run_payload(args.skip_judge)
                row["combined_pass"] = None if args.skip_judge else False

            append_jsonl_row(handle, row)
            all_rows.append(row)
            if args.fail_fast and row.get("status") not in {"completed"}:
                raise SystemExit(f"{method} failed for {case.question_id}: {row.get('provider_error') or row.get('failure_reasons')}")
            if index < len(ordered):
                sleep_between_vertex_requests(args.sleep_seconds)
    return all_rows


def build_retrieval_payloads(
    methods: list[str],
    corpus: list[Any],
    question_cases: list[Any],
    *,
    top_k: int,
    dense_model: str,
    dense_batch_size: int,
    cache_dir: Path,
    corpus_fingerprint: str,
) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    if "bm25" in methods:
        payloads["bm25"] = run_bm25_baseline(corpus, question_cases, top_k=top_k)
    if "dense" in methods:
        payloads["dense"] = run_dense_baseline(
            corpus,
            question_cases,
            top_k=top_k,
            model_name=dense_model,
            batch_size=dense_batch_size,
            cache_dir=cache_dir,
            corpus_fingerprint=corpus_fingerprint,
        )
    if "date_filter" in methods:
        payloads["date_filter"] = run_date_filter_baseline(corpus, question_cases, top_k=top_k)
    return payloads


def build_baseline_layer2b_prompt(case: Layer2BQACase, evidence_rows: list[Any]) -> str:
    cards = "\n".join(
        json.dumps(evidence_card(row, index), ensure_ascii=True, sort_keys=True)
        for index, row in enumerate(evidence_rows, start=1)
    )
    schema = {
        "answer": "...",
        "cited_evidence_ids": ["..."],
        "valid_time_used": "...",
        "answer_behavior": "answer | compare | warn_conflict | partial | refuse_or_clarify",
        "conflict_warning": False,
        "partial_or_refusal": False,
        "confidence": "high | medium | low",
    }
    return f"""You are ChronoRAG's Layer 2B grounded temporal answer synthesizer. Answer only from the supplied evidence. Preserve temporal meaning. Expose uncertainty instead of guessing.

Bitemporal rule: separate valid time from transaction time. Valid time means when the fact is true, observed, effective, reported, or applies. Transaction time means when the record was filed, published, released, stored, or made available. Use the time requested by the question. If the answer depends on both, state both clearly.

Important temporal rules:
1. Distinguish valid time from transaction time.
2. Valid time means the period during which the stated fact is true or applicable.
3. Transaction time means when the evidence was filed, published, recorded, revised, released, observed, or stored in the corpus.
4. A document date, filing date, publication date, release date, observation date, or recording date is not automatically the valid time.
5. If evidence is topically relevant but valid for the wrong time window, do not use it as support.
6. If the retrieved evidence does not contain evidence valid for the query's requested time, return a partial or insufficient-evidence/refusal result.
7. Cite only evidence IDs that support the answer for the requested valid-time window.
8. Do not use outside knowledge.

Conflict rule: if supplied evidence disagrees about the same entity, time, value, status, or requested fact, surface the conflict, cite the conflicting evidence, set conflict_warning to true, and set answer_behavior to warn_conflict.

Insufficient-evidence rule: if the supplied evidence is missing the requested detail, only partially supports the answer, is ambiguous, or is not about the requested time/entity/fact, do not infer. Give a partial or clarification/refusal answer, set partial_or_refusal to true, and set answer_behavior to partial or refuse_or_clarify.

Answer-quality rule: answer directly first. Preserve exact dates, values, units, names, identifiers, agencies, companies, repositories, releases, forms, and temporal windows. Cite every evidence row used. Do not cite unused rows. Do not use outside knowledge. Do not hallucinate missing details.

Output rules: Return exactly one raw JSON object. Do not use markdown fences. Do not include prose outside JSON. Never use null; use "", [], or false. answer must be a string. cited_evidence_ids must be a list of strings; use [] if no supplied evidence supports the answer. valid_time_used must be a string; use "" if no valid time is used. answer_behavior must be one of: answer, compare, warn_conflict, partial, refuse_or_clarify. conflict_warning must be boolean. partial_or_refusal must be boolean. confidence must be one of: high, medium, low.

User question:
{case.question}

Expected answer behavior label for evaluation:
{case.answer_behavior}

Required answer JSON schema:
{json.dumps(schema, sort_keys=True)}

Retrieved evidence cards:
{cards}
"""


def run_vertex_prompt_with_provider(
    provider: VertexGeminiProvider,
    prompt: str,
    *,
    temperature: float,
    max_output_tokens: int,
    retry_max_attempts: int,
    retry_base_sleep_seconds: float,
    retry_max_sleep_seconds: float,
    label: str,
) -> str:
    def call() -> str:
        result = provider.synthesize_grounded_answer(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if not result.ok:
            detail = " ".join(item for item in (result.provider_error, result.debug) if item)
            raise RuntimeError(detail or "Vertex provider failed.")
        return result.text

    return call_with_backoff(
        call,
        max_attempts=retry_max_attempts,
        base_sleep=retry_base_sleep_seconds,
        max_sleep=retry_max_sleep_seconds,
        label=label,
    )


def build_answer_result(
    method: str,
    case: Layer2BQACase,
    retrieval_row: dict[str, Any],
    evidence_rows: list[Any],
    args: argparse.Namespace,
    *,
    raw_response: str,
    answer_payload: dict[str, Any] | None,
    parse_diagnostics: dict[str, Any],
    corpus_lookup: dict[str, Any],
    latency_ms: float,
) -> dict[str, Any]:
    selected_ids = [row.id for row in evidence_rows]
    validation = validate_answer_contract(case, answer_payload, raw_response, selected_ids, corpus_lookup)
    return {
        **base_result_fields(method, case, retrieval_row, selected_ids, args),
        "status": "completed",
        "answer": validation.pop("normalized_answer"),
        "raw_model_response": raw_response,
        "provider_error": None,
        "parse_diagnostics": parse_diagnostics,
        "latency_ms": round(latency_ms, 2),
        "validation": validation,
    }


def build_provider_error_result(
    method: str,
    case: Layer2BQACase,
    retrieval_row: dict[str, Any],
    evidence_rows: list[Any],
    args: argparse.Namespace,
    *,
    error: Exception,
    latency_ms: float,
) -> dict[str, Any]:
    selected_ids = [row.id for row in evidence_rows]
    return {
        **base_result_fields(method, case, retrieval_row, selected_ids, args),
        "status": "provider_error",
        "answer": None,
        "raw_model_response": None,
        "provider_error": preview(str(error), 1200),
        "parse_diagnostics": {"json_parse_error": None, "json_recovered": False, "json_recovery_method": None},
        "latency_ms": round(latency_ms, 2),
        "validation": {
            "schema_pass": False,
            "expected_evidence_cited": False,
            "unknown_citation_absent": True,
            "valid_time_present": False,
            "answer_behavior_correct": False,
            "partial_refusal_correct": False,
            "conflict_warning_correct": False,
            "expected_evidence_available_to_model": all(eid in set(selected_ids) for eid in case.expected_evidence_ids),
            "overall_contract_pass": False,
            "failure_reasons": ["provider_error"],
            "unknown_cited_evidence_ids": [],
        },
    }


def build_missing_retrieval_result(method: str, case: Layer2BQACase, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "benchmark": "layer2b_manual_qa_stdcomp_llm_baseline",
        "method": method,
        "method_label": METHOD_LABELS[method],
        "mode": "vertex",
        "model": args.model,
        "project": args.project,
        "location": args.location,
        "temperature": args.temperature,
        "question_id": case.question_id,
        "question": case.question,
        "question_type": case.question_type,
        "expected_answer_behavior": case.answer_behavior,
        "difficulty": case.difficulty,
        "source_family": case.source_family,
        "expected_evidence_ids": case.expected_evidence_ids,
        "expected_valid_time": case.expected_valid_time,
        "selected_evidence_ids": [],
        "retrieved_evidence_ids": [],
        "top_k": args.top_k,
        "status": "retrieval_error",
        "answer": None,
        "raw_model_response": None,
        "provider_error": "Missing retrieval row.",
        "validation": {"overall_contract_pass": False, "failure_reasons": ["missing_retrieval_row"]},
        "retrieval_metrics": retrieval_metrics(case, []),
        "retrieval_metadata": {},
        "judge_validation": judge_not_run_payload(True),
        "combined_pass": False,
    }


def base_result_fields(
    method: str,
    case: Layer2BQACase,
    retrieval_row: dict[str, Any],
    selected_ids: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    ranked = retrieval_row.get("ranked_evidence") or []
    return {
        "benchmark": "layer2b_manual_qa_stdcomp_llm_baseline",
        "method": method,
        "method_label": METHOD_LABELS[method],
        "mode": "vertex",
        "model": args.model,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "question_id": case.question_id,
        "question": case.question,
        "question_type": case.question_type,
        "expected_answer_behavior": case.answer_behavior,
        "difficulty": case.difficulty,
        "source_family": case.source_family,
        "expected_evidence_ids": case.expected_evidence_ids,
        "expected_valid_time": case.expected_valid_time,
        "selected_evidence_ids": selected_ids,
        "retrieved_evidence_ids": selected_ids,
        "top_k": args.top_k,
        "retrieval_metrics": retrieval_metrics(case, selected_ids),
        "retrieval_metadata": {
            "retrieval_method": method,
            "standard_baseline_metadata": retrieval_row.get("metadata") or {},
            "ranked_evidence": ranked,
            "uses_tcc": False,
            "uses_temporal_metadata_scoring": False,
            "uses_temporal_fusion": False,
            "uses_forbidden_time_suppression": False,
        },
    }


def attach_judge_result(
    row: dict[str, Any],
    case: Layer2BQACase,
    evidence_rows: list[Any],
    provider: VertexGeminiProvider,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        judge = run_layer2b_judge(
            case,
            row["answer"],
            evidence_cards_from_rows(evidence_rows),
            provider,
            deterministic_validation=row.get("validation") or {},
            runs=args.judge_runs,
            temperature=args.judge_temperature,
            max_output_tokens=args.judge_max_output_tokens,
            request_sleep_seconds=args.sleep_seconds,
            retry_max_attempts=args.judge_retry_max_attempts,
            retry_base_sleep_seconds=args.judge_retry_base_sleep_seconds,
            retry_max_sleep_seconds=args.judge_retry_max_sleep_seconds,
            json_retry_max_attempts=args.judge_json_retry_max_attempts,
        )
        row["judge_validation"] = judge
        row["combined_pass"] = row.get("validation", {}).get("overall_contract_pass") is True and judge.get("overall_judge_pass") is True
        row["judge_latency_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
        if judge.get("judge_infrastructure_failure"):
            row["status"] = "judge_error"
    except Exception as exc:
        row["judge_validation"] = {
            "overall_judge_pass": False,
            "severity": "critical",
            "failure_reasons": ["judge_exception"],
            "brief_rationale": preview(str(exc), 240),
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
        row["judge_latency_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
        row["status"] = "judge_error"
    return row


def compute_method_metrics(method: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    cases = len(rows)
    validation_rows = [row.get("validation") or {} for row in rows]
    judge_rows = [row.get("judge_validation") or {} for row in rows]
    retrieval_rows = [row.get("retrieval_metrics") or {} for row in rows]
    return {
        "method": method,
        "method_label": METHOD_LABELS[method],
        "cases": cases,
        "provider_errors": sum(1 for row in rows if row.get("status") == "provider_error"),
        "judge_errors": sum(1 for row in rows if row.get("status") == "judge_error"),
        "retrieval_hit@1": mean_bool_metric(retrieval_rows, "hit@1"),
        "retrieval_hit@5": mean_bool_metric(retrieval_rows, "hit@5"),
        "retrieval_mrr@5": mean_float_metric(retrieval_rows, "mrr@5"),
        "deterministic_hard_contract_pass": mean_bool_metric(validation_rows, "overall_contract_pass"),
        "strict_combined_pass": mean_bool_metric([{"combined_pass": row.get("combined_pass")} for row in rows], "combined_pass"),
        "llm_judge_semantic_pass": mean_bool_metric(judge_rows, "semantic_answer_correct"),
        "llm_judge_overall_pass": mean_bool_metric(judge_rows, "overall_judge_pass"),
        "answer_correctness": mean_bool_metric(judge_rows, "semantic_answer_correct"),
        "expected_evidence_cited": mean_bool_metric(validation_rows, "expected_evidence_cited"),
        "citation_ids_valid": mean_bool_metric(validation_rows, "unknown_citation_absent"),
        "valid_time_used_correct": mean_bool_metric(validation_rows, "valid_time_present"),
        "judge_valid_time_correct": mean_bool_metric(judge_rows, "valid_time_correct"),
        "behavior_correct": mean_bool_metric(validation_rows, "answer_behavior_correct"),
        "partial_refusal_correct": mean_bool_metric(validation_rows, "partial_refusal_correct"),
        "conflict_warning_correct": mean_bool_metric(validation_rows, "conflict_warning_correct"),
        "expected_evidence_available_to_model": mean_bool_metric(validation_rows, "expected_evidence_available_to_model"),
        "transaction_time_used_as_valid_time_violations": None,
        "transaction_time_metric_note": "The existing Layer 2B answer schema does not expose a separate transaction_time_used_as_valid_time field; valid_time correctness is reported instead.",
        "failure_reason_counts": failure_reason_counts(rows),
    }


def comparison_row(method: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": method,
        "method_label": METHOD_LABELS[method],
        "cases": metrics["cases"],
        "retrieval_hit@1": metrics["retrieval_hit@1"],
        "retrieval_hit@5": metrics["retrieval_hit@5"],
        "retrieval_mrr@5": metrics["retrieval_mrr@5"],
        "deterministic_hard_contract_pass": metrics["deterministic_hard_contract_pass"],
        "llm_judge_semantic_pass": metrics["llm_judge_semantic_pass"],
        "strict_combined_pass": metrics["strict_combined_pass"],
        "expected_evidence_cited": metrics["expected_evidence_cited"],
        "valid_time_used_correct": metrics["valid_time_used_correct"],
        "provider_errors": metrics["provider_errors"],
        "judge_errors": metrics["judge_errors"],
    }


def rows_for_selected_evidence(retrieval_row: dict[str, Any], corpus_lookup: dict[str, Any]) -> list[Any]:
    rows = []
    for evidence_id in retrieval_row.get("selected_evidence_ids") or []:
        row = corpus_lookup.get(str(evidence_id))
        if row is not None:
            rows.append(row)
    return rows


def evidence_card(row: Any, rank: int) -> dict[str, Any]:
    card = row.to_prompt_dict()
    card["rank"] = rank
    return card


def retrieval_metrics(case: Layer2BQACase, selected_ids: list[str]) -> dict[str, Any]:
    relevant = set(case.expected_evidence_ids)
    top1 = selected_ids[:1]
    top5 = selected_ids[:5]
    return {
        "hit@1": bool(top1) and top1[0] in relevant,
        "hit@5": bool(set(top5) & relevant),
        "mrr@5": reciprocal_rank(top5, relevant),
    }


def reciprocal_rank(selected_ids: list[str], relevant: set[str]) -> float:
    for index, evidence_id in enumerate(selected_ids[:5], start=1):
        if evidence_id in relevant:
            return 1.0 / index
    return 0.0


def mean_bool_metric(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row.get(key) for row in rows if isinstance(row.get(key), bool)]
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def mean_float_metric(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row.get(key) for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        return None
    return sum(float(value) for value in values) / len(values)


def failure_reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        reasons = list((row.get("validation") or {}).get("failure_reasons") or [])
        reasons.extend((row.get("judge_validation") or {}).get("failure_reasons") or [])
        for reason in reasons:
            text = str(reason)
            counts[text] = counts.get(text, 0) + 1
    return dict(sorted(counts.items()))


def judge_not_run_payload(skip_judge: bool) -> dict[str, Any]:
    reason = "judge_disabled_by_skip_judge" if skip_judge else "judge_not_run_due_to_answer_failure"
    return {
        "overall_judge_pass": None if skip_judge else False,
        "semantic_answer_correct": None if skip_judge else False,
        "severity": "not_applicable" if skip_judge else "critical",
        "failure_reasons": [reason],
        "brief_rationale": "Judge was not called.",
        "judge_infrastructure_failure": False,
        "judge_parse_failures": 0,
        "judge_provider_failures": 0,
        "judge_retry_attempts": 0,
        "judge_runs": 0,
        "judge_scored_runs": 0,
        "judge_unscored_runs": 0,
        "judge_recovered_partial_json_count": 0,
    }


def build_manifest(
    args: argparse.Namespace,
    methods: list[str],
    qa_path: Path,
    corpus_path: Path,
    cases: list[Layer2BQACase],
    corpus: list[Any],
) -> dict[str, Any]:
    return {
        "benchmark": "layer2b_manual_50_qa",
        "experiment": "qa50_llm_standard_retrieval_baselines",
        "command": " ".join(sys.argv),
        "qa": {"path": str(qa_path), "rows_selected": len(cases), "sha256": sha256(qa_path)},
        "corpus": {"path": str(corpus_path), "rows": len(corpus), "sha256": sha256(corpus_path)},
        "methods": methods,
        "top_k": args.top_k,
        "model": args.model,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "sleep_seconds": args.sleep_seconds,
        "resume": args.resume,
        "force": args.force,
        "judge_enabled": not args.skip_judge,
        "judge_runs": args.judge_runs,
        "judge_temperature": args.judge_temperature,
        "judge_max_output_tokens": args.judge_max_output_tokens,
        "dense_model": args.dense_model,
        "fairness_constraints": [
            "Same top_k for all methods.",
            "Same QA cases, corpus, LLM model, temperature, prompt template, validator, and judge settings for all methods.",
            "No ChronoRAG retrieval features, TCC, temporal fusion, or forbidden-time suppression in standard retrievers.",
            "Gold expected evidence IDs are not included in the answer prompt.",
        ],
    }


def write_comparison_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "method",
        "method_label",
        "cases",
        "retrieval_hit@1",
        "retrieval_hit@5",
        "retrieval_mrr@5",
        "deterministic_hard_contract_pass",
        "llm_judge_semantic_pass",
        "strict_combined_pass",
        "expected_evidence_cited",
        "valid_time_used_correct",
        "provider_errors",
        "judge_errors",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_comparison_md(path: Path, rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    lines = [
        "# QA50 LLM Baseline Comparison",
        "",
        "This is baseline retrieval plus Vertex/Gemini answer generation and Layer 2B validation. It is not retrieval-only.",
        "",
        f"QA: `{manifest['qa']['path']}` ({manifest['qa']['rows_selected']} cases)",
        f"Corpus: `{manifest['corpus']['path']}` ({manifest['corpus']['rows']} rows)",
        f"Top-k: {manifest['top_k']}",
        f"Model: `{manifest['model']}`",
        f"Temperature: {manifest['temperature']}",
        f"Judge enabled: {manifest['judge_enabled']}",
        "",
        render_comparison_table(rows),
        "",
        "Notes:",
        "- BM25, Dense-only, and Date-filter RAG use the same top-5 raw corpus evidence rows and the same answer prompt.",
        "- The prompt explicitly instructs the model to distinguish valid time from transaction time.",
        "- `transaction_time_used_as_valid_time` is not a separate field in the existing Layer 2B answer schema, so valid-time correctness is reported instead.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def render_comparison_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Method | Cases | Retrieval Hit@1 | Retrieval Hit@5 | Retrieval MRR@5 | Hard Contract Pass | Judge Semantic Pass | Strict Combined Pass | Evidence Cited | Valid Time Correct | Provider Errors | Judge Errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method_label']} | {row['cases']} | {_fmt(row['retrieval_hit@1'])} | "
            f"{_fmt(row['retrieval_hit@5'])} | {_fmt(row['retrieval_mrr@5'])} | "
            f"{_fmt(row['deterministic_hard_contract_pass'])} | {_fmt(row['llm_judge_semantic_pass'])} | "
            f"{_fmt(row['strict_combined_pass'])} | {_fmt(row['expected_evidence_cited'])} | "
            f"{_fmt(row['valid_time_used_correct'])} | {row['provider_errors']} | {row['judge_errors']} |"
        )
    return "\n".join(lines)


def parse_methods(raw: str) -> list[str]:
    values = []
    for item in raw.split(","):
        method = item.strip().lower()
        if method == "dense_only":
            method = "dense"
        if method == "date_filter_rag":
            method = "date_filter"
        if method:
            values.append(method)
    invalid = [method for method in values if method not in METHOD_ORDER]
    if invalid:
        raise SystemExit(f"Unknown method(s): {', '.join(invalid)}. Use bm25,dense,date_filter.")
    return [method for method in METHOD_ORDER if method in set(values)]


def validate_args(args: argparse.Namespace, methods: list[str]) -> None:
    if not methods:
        raise SystemExit("--methods must select at least one method.")
    if args.top_k != 5:
        raise SystemExit("This QA50 baseline experiment must use fixed --top-k 5.")
    if args.max_cases < 0:
        raise SystemExit("--max-cases must be non-negative.")
    if args.start_index < 0:
        raise SystemExit("--start-index must be non-negative.")
    if args.judge_runs <= 0:
        raise SystemExit("--judge-runs must be positive.")
    if args.resume and args.force:
        raise SystemExit("Use either --resume or --force, not both.")


def preflight_vertex(args: argparse.Namespace) -> None:
    if not args.project:
        raise SystemExit(
            "Vertex execution requires GOOGLE_CLOUD_PROJECT or --project. "
            "No LLM calls were made and no QA50 LLM baseline outputs were written."
        )
    try:
        import vertexai  # noqa: F401
        from vertexai.generative_models import GenerationConfig, GenerativeModel  # noqa: F401
    except Exception as exc:
        raise SystemExit(
            "Vertex execution requires the Vertex AI SDK. "
            "Install provider dependencies before running QA50 LLM baselines. "
            f"Import error: {exc}"
        ) from exc


def preview(text: str, limit: int) -> str:
    return text.replace("\n", " ").strip()[:limit]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


if __name__ == "__main__":
    main()
