from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.layer2b_qa import (
    DEFAULT_CORPUS_PATH,
    DEFAULT_QA_PATH,
    METHOD_NAME,
    append_jsonl_row,
    build_dry_run_result,
    build_evidence_lookup,
    build_layer2b_prompt,
    build_provider_error_result,
    build_vertex_result,
    completed_successful_case_ids,
    load_existing_results,
    load_layer2b_cases,
    load_selected_corpus,
    parse_answer_json,
    prepare_retrieval_context,
    result_paths,
    retrieve_chronorag_full,
    run_vertex_prompt,
    sleep_between_vertex_requests,
    write_markdown_summary,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Layer 2B manual QA answer synthesis.")
    parser.add_argument("--mode", choices=["dry_run", "vertex"], default="dry_run")
    parser.add_argument("--method", choices=[METHOD_NAME], default=METHOD_NAME)
    parser.add_argument("--qa", default=str(DEFAULT_QA_PATH))
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS_PATH))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--result-suffix", default="default")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--request-sleep-seconds", type=float, default=10.0)
    parser.add_argument("--retry-max-attempts", type=int, default=5)
    parser.add_argument("--retry-base-sleep-seconds", type=float, default=5.0)
    parser.add_argument("--retry-max-sleep-seconds", type=float, default=90.0)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.top_k <= 0:
        raise SystemExit("--top-k must be positive.")
    if args.limit is not None and args.limit < 0:
        raise SystemExit("--limit must be non-negative.")
    if args.start_index < 0:
        raise SystemExit("--start-index must be non-negative.")

    jsonl_path, md_path = result_paths(args.result_suffix)
    existing_results = load_existing_results(jsonl_path) if args.resume else []
    completed_ids = completed_successful_case_ids(existing_results)

    cases = load_layer2b_cases(args.qa)
    ordered = cases[args.start_index :]
    if args.resume:
        ordered = [case for case in ordered if case.question_id not in completed_ids]
    if args.limit is not None:
        ordered = ordered[: args.limit]

    print(f"Mode: {args.mode}")
    print(f"Method: {args.method}")
    print(f"Cases selected: {len(ordered)}")
    print(f"Corpus: {args.corpus}")
    print(f"QA: {args.qa}")
    print(f"Output JSONL: {jsonl_path}")
    print(f"Output Markdown: {md_path}")
    if args.mode == "vertex":
        print(f"Vertex sleep seconds: {args.request_sleep_seconds}")

    corpus = load_selected_corpus(args.corpus)
    corpus_lookup = build_evidence_lookup(corpus)
    try:
        prepared_context = prepare_retrieval_context(corpus)
    except Exception as exc:
        raise SystemExit(f"ChronoRAG retrieval context preparation failed: {exc}") from exc

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"
    all_results = list(existing_results)
    with jsonl_path.open(mode, encoding="utf-8") as handle:
        for index, case in enumerate(ordered, start=1):
            print(f"[{index}/{len(ordered)}] {case.question_id}", flush=True)
            try:
                evidence_rows, retrieval_metadata = retrieve_chronorag_full(case, prepared_context, args.top_k)
            except Exception as exc:
                raise SystemExit(f"ChronoRAG retrieval failed for {case.question_id}: {exc}") from exc

            if args.mode == "dry_run":
                row = build_dry_run_result(
                    case,
                    evidence_rows,
                    retrieval_metadata,
                    top_k=args.top_k,
                    suffix=args.result_suffix,
                )
                append_jsonl_row(handle, row)
                all_results.append(row)
                continue

            prompt = build_layer2b_prompt(case, evidence_rows)
            started = time.perf_counter()
            try:
                raw_response = run_vertex_prompt(
                    prompt,
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                    retry_max_attempts=args.retry_max_attempts,
                    retry_base_sleep_seconds=args.retry_base_sleep_seconds,
                    retry_max_sleep_seconds=args.retry_max_sleep_seconds,
                    label=f"layer2b case={case.question_id}",
                )
                answer_payload, parse_diagnostics = parse_answer_json(raw_response)
                row = build_vertex_result(
                    case,
                    evidence_rows,
                    retrieval_metadata,
                    top_k=args.top_k,
                    suffix=args.result_suffix,
                    raw_response=raw_response,
                    answer_payload=answer_payload,
                    parse_diagnostics=parse_diagnostics,
                    corpus_lookup=corpus_lookup,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                )
            except Exception as exc:
                row = build_provider_error_result(
                    case,
                    evidence_rows,
                    retrieval_metadata,
                    top_k=args.top_k,
                    suffix=args.result_suffix,
                    error=exc,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                )
                append_jsonl_row(handle, row)
                all_results.append(row)
                write_markdown_summary(all_results, md_path, mode=args.mode, top_k=args.top_k, result_suffix=args.result_suffix)
                if args.fail_fast:
                    raise SystemExit(f"Provider failed for {case.question_id}: {exc}") from exc
                if index < len(ordered):
                    sleep_between_vertex_requests(args.request_sleep_seconds)
                continue

            append_jsonl_row(handle, row)
            all_results.append(row)
            if index < len(ordered):
                sleep_between_vertex_requests(args.request_sleep_seconds)

    write_markdown_summary(all_results, md_path, mode=args.mode, top_k=args.top_k, result_suffix=args.result_suffix)
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
