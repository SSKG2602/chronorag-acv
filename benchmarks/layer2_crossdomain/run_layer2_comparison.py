from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.reporting import metric_summary, write_comparison_report, write_method_results
from benchmarks.layer2_crossdomain.schemas import CorpusRow, ModelAnswer, QuestionCase, load_corpus, load_questions
from benchmarks.layer2_crossdomain.evaluate_retrieval_only import score_case
from benchmarks.layer2_crossdomain.vertex_retry import call_with_backoff
from benchmarks.layer2_crossdomain.prompts import build_evidence_fact_sentence
from benchmarks.layer2_crossdomain.llm_judge import evidence_cards_from_rows, validate_case_v3

METHODS = ("direct_llm_full_context", "metadata_temporal_rag", "chronorag_full")
# Direct full-context remains callable for historical diagnostics, but it is
# not a retrieval baseline and can truncate on the 5,000-row Layer 2A corpus.
DEFAULT_METHODS = ("metadata_temporal_rag", "chronorag_full")
DEFAULT_CORPUS = "benchmarks/layer2_crossdomain/data/layer2_corpus.sample.jsonl"
DEFAULT_QUESTIONS = "benchmarks/layer2_crossdomain/data/layer2_questions.sample.jsonl"
REAL_CORPUS = "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
REAL_QUESTIONS = "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Layer 2 cross-domain comparison framework.")
    parser.add_argument("--method", choices=[*METHODS, "all"], default="all")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS)
    parser.add_argument("--questions", default=DEFAULT_QUESTIONS)
    parser.add_argument("--dataset", choices=["sample", "real"], default="sample")
    parser.add_argument("--mode", choices=["light", "vertex", "dry_run"], default="light")
    parser.add_argument("--validator", choices=["deterministic", "llm_judge"], default="deterministic")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--dry-run-prompts", action="store_true")
    parser.add_argument("--max-output-tokens", type=int, default=None)
    # This is a ceiling to prevent answer JSON truncation on hard Layer 2 cases.
    # The prompt still asks for concise answers; the larger cap is not a request
    # for verbosity.
    parser.add_argument("--answer-max-output-tokens", type=int, default=4000)
    parser.add_argument("--result-suffix", default="default")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--embedding-dim", type=int, default=None)
    parser.add_argument("--request-sleep-seconds", type=float, default=3.0)
    parser.add_argument("--retry-max-attempts", type=int, default=5)
    parser.add_argument("--retry-base-sleep-seconds", type=float, default=5.0)
    parser.add_argument("--retry-max-sleep-seconds", type=float, default=90.0)
    parser.add_argument("--json-retry-max-attempts", type=int, default=3)
    parser.add_argument("--judge-runs", type=int, default=3)
    parser.add_argument("--judge-temperature", type=float, default=0.3)
    # Judge output should remain compact. This higher ceiling only avoids
    # incomplete provider JSON on hard cases; semantic scoring is independent of
    # output length.
    parser.add_argument("--judge-max-output-tokens", type=int, default=4000)
    parser.add_argument("--judge-request-sleep-seconds", type=float, default=6.0)
    parser.add_argument("--judge-retry-max-attempts", type=int, default=4)
    parser.add_argument("--judge-retry-base-sleep-seconds", type=float, default=8.0)
    parser.add_argument("--judge-retry-max-sleep-seconds", type=float, default=90.0)
    parser.add_argument("--judge-json-retry-max-attempts", type=int, default=3)
    parser.add_argument("--vertex-location")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--write-partial", dest="write_partial", action="store_true", default=True)
    parser.add_argument("--no-write-partial", dest="write_partial", action="store_false")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.vertex_location:
        os.environ["GOOGLE_CLOUD_LOCATION"] = args.vertex_location
    if args.embedding_model:
        os.environ["CHRONORAG_EMBED_MODEL"] = args.embedding_model
    if args.embedding_dim is not None:
        os.environ["CHRONORAG_EMBED_DIM"] = str(args.embedding_dim)

    suffix = _sanitize_suffix(args.result_suffix)
    answer_max_output_tokens = args.answer_max_output_tokens
    if args.max_output_tokens is not None and args.answer_max_output_tokens == 4000:
        answer_max_output_tokens = args.max_output_tokens
    corpus_path = REAL_CORPUS if args.dataset == "real" and args.corpus == DEFAULT_CORPUS else args.corpus
    questions_path = REAL_QUESTIONS if args.dataset == "real" and args.questions == DEFAULT_QUESTIONS else args.questions
    corpus = load_corpus(corpus_path)
    questions = _select_questions(load_questions(questions_path), args.limit, args.case_id)
    selected_methods = list(DEFAULT_METHODS) if args.method == "all" else [args.method]
    estimated_calls = len(questions) * len(selected_methods) if args.mode == "vertex" else 0
    prompt_estimates = estimate_prompt_sizes(selected_methods, corpus, questions, args.top_k)

    print(f"Mode: {args.mode}")
    print(f"Validator: {args.validator}")
    print(f"Methods: {', '.join(selected_methods)}")
    print(
        "Embedding config: "
        f"model={os.getenv('CHRONORAG_EMBED_MODEL', 'BAAI/bge-small-en-v1.5')}; "
        f"dim={os.getenv('CHRONORAG_EMBED_DIM', '384')}"
    )
    print(f"Selected cases: {len(questions)}")
    print(f"Estimated Vertex calls: {estimated_calls}")
    if args.mode == "vertex":
        print(
            "Vertex config: "
            f"project={os.getenv('GOOGLE_CLOUD_PROJECT') or '(unset)'}; "
            f"location={os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}; "
            f"model={os.getenv('VERTEX_MODEL_ID', 'gemini-2.5-flash')}"
        )
    for method, estimate in prompt_estimates.items():
        print(
            f"Prompt estimate {method}: max_chars={estimate['max_prompt_chars']}, "
            f"truncated_cases={estimate['truncated_cases']}"
        )

    if args.estimate_only:
        return

    payloads = []
    for method in selected_methods:
        json_path, md_path = _result_paths(method, suffix)
        existing_payload = _load_existing_payload(json_path) if args.resume else None
        payload = run_method(
            method=method,
            corpus=corpus,
            questions=questions,
            mode=args.mode,
            top_k=args.top_k,
            dry_run_prompts=args.dry_run_prompts,
            max_output_tokens=answer_max_output_tokens,
            suffix=suffix,
            request_sleep_seconds=args.request_sleep_seconds,
            retry_max_attempts=args.retry_max_attempts,
            retry_base_sleep_seconds=args.retry_base_sleep_seconds,
            retry_max_sleep_seconds=args.retry_max_sleep_seconds,
            json_retry_max_attempts=args.json_retry_max_attempts,
            validator=args.validator,
            judge_runs=args.judge_runs,
            judge_temperature=args.judge_temperature,
            judge_max_output_tokens=args.judge_max_output_tokens,
            judge_request_sleep_seconds=args.judge_request_sleep_seconds,
            judge_retry_max_attempts=args.judge_retry_max_attempts,
            judge_retry_base_sleep_seconds=args.judge_retry_base_sleep_seconds,
            judge_retry_max_sleep_seconds=args.judge_retry_max_sleep_seconds,
            judge_json_retry_max_attempts=args.judge_json_retry_max_attempts,
            write_partial=args.write_partial,
            json_path=json_path,
            md_path=md_path,
            existing_payload=existing_payload,
        )
        payloads.append(payload)
        write_method_results(payload, json_path, md_path)
        print(f"Wrote: {json_path}")
        print(f"Wrote: {md_path}")

    if len(payloads) > 1:
        comparison_path = Path("benchmarks/layer2_crossdomain/results") / f"layer2_comparison_{suffix}.md"
        write_comparison_report(payloads, comparison_path)
        print(f"Wrote: {comparison_path}")


def run_method(
    method: str,
    corpus: list[CorpusRow],
    questions: list[QuestionCase],
    mode: str,
    top_k: int,
    dry_run_prompts: bool,
    max_output_tokens: int,
    suffix: str,
    request_sleep_seconds: float = 3.0,
    retry_max_attempts: int = 5,
    retry_base_sleep_seconds: float = 5.0,
    retry_max_sleep_seconds: float = 90.0,
    json_retry_max_attempts: int = 2,
    validator: str = "deterministic",
    judge_runs: int = 3,
    judge_temperature: float = 0.3,
    judge_max_output_tokens: int = 4000,
    judge_request_sleep_seconds: float = 6.0,
    judge_retry_max_attempts: int = 4,
    judge_retry_base_sleep_seconds: float = 8.0,
    judge_retry_max_sleep_seconds: float = 90.0,
    judge_json_retry_max_attempts: int = 3,
    judge_provider: Any | None = None,
    write_partial: bool = True,
    json_path: Path | None = None,
    md_path: Path | None = None,
    existing_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    module = _method_module(method)
    results = list((existing_payload or {}).get("results") or [])
    completed_case_ids = _completed_case_ids(results)
    started = time.perf_counter()
    active_judge_provider = judge_provider
    if validator == "llm_judge" and not dry_run_prompts and mode != "dry_run" and active_judge_provider is None:
        active_judge_provider = _build_vertex_provider()
    for case in questions:
        if case.id in completed_case_ids:
            print(f"[resume] method={method} case={case.id} skipped existing completed result")
            continue
        method_payload = module.build_prompt(case, corpus, top_k)
        prompt = method_payload["prompt"]
        evidence_rows = method_payload["evidence_rows"]
        truncated = bool(method_payload.get("prompt_truncated"))
        method_metadata = {
            **dict(method_payload.get("metadata") or {}),
            "answer_max_output_tokens": max_output_tokens,
            "judge_max_output_tokens": judge_max_output_tokens if validator == "llm_judge" else None,
        }
        case_started = time.perf_counter()
        if dry_run_prompts or mode == "dry_run":
            answer = _dry_run_answer(prompt)
        elif mode == "light":
            answer = _light_answer(case, evidence_rows)
        else:
            attempts = {"count": 0}
            json_failures = {"count": 0}
            json_attempt_limit = max(1, json_retry_max_attempts)

            def provider_call() -> dict[str, Any]:
                attempts["count"] += 1
                try:
                    return _vertex_answer(prompt, max_output_tokens)
                except ProviderJSONError as exc:
                    json_failures["count"] += 1
                    if json_failures["count"] >= json_attempt_limit:
                        raise ProviderJSONRetryLimitError(
                            f"JSON retry limit reached after {json_failures['count']} attempts: {exc}"
                        ) from exc
                    raise

            try:
                answer = call_with_backoff(
                    provider_call,
                    max_attempts=retry_max_attempts,
                    base_sleep=retry_base_sleep_seconds,
                    max_sleep=retry_max_sleep_seconds,
                    label=f"case={case.id} method={method}",
                )
                method_metadata["retry_attempts"] = max(0, attempts["count"] - 1)
                method_metadata["json_parse_failures"] = json_failures["count"]
            except Exception as exc:
                latency_ms = (time.perf_counter() - case_started) * 1000.0
                results.append(
                    _provider_error_result(
                        method=method,
                        case=case,
                        evidence_rows=evidence_rows,
                        mode=mode,
                        latency_ms=latency_ms,
                        prompt_preview=prompt[:1200] if dry_run_prompts else None,
                        method_metadata=method_metadata,
                        error=exc,
                        retry_attempts=max(0, attempts["count"] - 1),
                        json_parse_failures=json_failures["count"],
                    )
                )
                if write_partial and json_path and md_path:
                    write_method_results(
                        _build_payload(method, mode, suffix, corpus, questions, top_k, started, results, dry_run_prompts, validator),
                        json_path,
                        md_path,
                    )
                _sleep_after_vertex_call(mode, dry_run_prompts, request_sleep_seconds)
                continue
        latency_ms = (time.perf_counter() - case_started) * 1000.0
        answer_recovery_metadata = _pop_answer_recovery_metadata(answer)
        answer, postprocess_metadata = _postprocess_answer_with_cited_evidence(answer, evidence_rows)
        model_answer = ModelAnswer.from_dict(answer).to_dict()
        selected_evidence_ids = [row.id for row in evidence_rows]
        if validator == "llm_judge" and not dry_run_prompts and mode != "dry_run":
            validation = validate_case_v3(
                case,
                model_answer,
                evidence_cards_from_rows(evidence_rows),
                active_judge_provider,
                runs=judge_runs,
                temperature=judge_temperature,
                max_output_tokens=judge_max_output_tokens,
                request_sleep_seconds=judge_request_sleep_seconds,
                retry_max_attempts=judge_retry_max_attempts,
                retry_base_sleep_seconds=judge_retry_base_sleep_seconds,
                retry_max_sleep_seconds=judge_retry_max_sleep_seconds,
                json_retry_max_attempts=judge_json_retry_max_attempts,
            )
        elif validator == "llm_judge":
            validation = _judge_skipped_validation(case.id, "Judge skipped for dry-run prompts.")
        else:
            validation = _retrieval_validation_result(case, selected_evidence_ids)
        results.append(
            {
                "method": method,
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "selected_evidence_ids": selected_evidence_ids,
                "prompt_truncated": truncated,
                "provider_mode": mode,
                "latency_ms": round(latency_ms, 2),
                "prompt_preview": prompt[:1200] if dry_run_prompts or mode == "dry_run" else None,
                "answer": model_answer,
                "validation": validation,
                "validator": validator,
                "status": "completed",
                "infrastructure_failure": False,
                "provider_output_contract_failure": False,
                "provider_error": None,
                "metadata": {
                    **method_metadata,
                    **answer_recovery_metadata,
                    **postprocess_metadata,
                    "dry_run_prompts": dry_run_prompts,
                    "retrieval_only_dry_run": mode == "dry_run",
                },
            }
        )
        if write_partial and json_path and md_path:
            write_method_results(
                _build_payload(method, mode, suffix, corpus, questions, top_k, started, results, dry_run_prompts, validator),
                json_path,
                md_path,
            )
        _sleep_after_vertex_call(mode, dry_run_prompts, request_sleep_seconds)
    return _build_payload(method, mode, suffix, corpus, questions, top_k, started, results, dry_run_prompts, validator)


def _build_payload(
    method: str,
    mode: str,
    suffix: str,
    corpus: list[CorpusRow],
    questions: list[QuestionCase],
    top_k: int,
    started: float,
    results: list[dict[str, Any]],
    dry_run_prompts: bool = False,
    validator: str = "deterministic",
) -> dict[str, Any]:
    latency_ms = (time.perf_counter() - started) * 1000.0
    summary = metric_summary(results, validator=validator)
    summary.update(
        {
            "infrastructure_failure_count": sum(1 for row in results if row.get("infrastructure_failure")),
            "provider_error_count": sum(1 for row in results if row.get("provider_error")),
            "provider_output_contract_failure_count": sum(
                1 for row in results if row.get("provider_output_contract_failure")
            ),
            "retry_attempts_total": sum(int((row.get("metadata") or {}).get("retry_attempts", 0)) for row in results),
            "json_parse_failure_count": sum(
                int((row.get("metadata") or {}).get("json_parse_failures", 0)) for row in results
            ),
            "scored_case_count": sum(1 for row in results if not row.get("infrastructure_failure")),
            "answer_max_output_tokens": _first_metadata_value(results, "answer_max_output_tokens"),
            "judge_max_output_tokens": _first_metadata_value(results, "judge_max_output_tokens"),
            "answer_json_recovered_count": sum(
                1 for row in results if (row.get("metadata") or {}).get("answer_json_recovered")
            ),
        }
    )
    return {
        "benchmark": "layer2_crossdomain",
        "method": method,
        "mode": mode,
        "validator": validator,
        "result_suffix": suffix,
        "corpus_rows": len(corpus),
        "question_count": len(questions),
        "estimated_calls": len(questions) if mode == "vertex" and not dry_run_prompts else 0,
        "top_k": top_k,
        "embedding_model": os.getenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        "embedding_dim": int(os.getenv("CHRONORAG_EMBED_DIM", "384")),
        "prompt_truncation_count": sum(1 for row in results if row["prompt_truncated"]),
        "average_selected_evidence": (
            sum(len(row["selected_evidence_ids"]) for row in results) / len(results) if results else 0.0
        ),
        "latency_ms": round(latency_ms, 2),
        "summary": summary,
        "results": results,
    }


def _method_module(method: str):
    if method == "direct_llm_full_context":
        from benchmarks.layer2_crossdomain.methods.direct_llm_full_context import runner
    elif method == "metadata_temporal_rag":
        from benchmarks.layer2_crossdomain.methods.metadata_temporal_rag import runner
    elif method == "chronorag_full":
        from benchmarks.layer2_crossdomain.methods.chronorag_full import runner
    else:
        raise ValueError(f"Unknown method: {method}")
    return runner


def _light_answer(case: QuestionCase, evidence_rows: list[CorpusRow]) -> dict[str, Any]:
    cited = [row.id for row in evidence_rows if row.id in set(case.expected_evidence_ids + case.acceptable_evidence_ids)]
    if not cited and evidence_rows and case.expected_behavior not in {"refuse", "clarify"}:
        cited = [evidence_rows[0].id]
    facts = "; ".join(case.required_facts)
    if case.expected_behavior == "refuse":
        answer = f"Evidence is insufficient; {facts}"
    elif case.expected_behavior == "clarify":
        answer = f"The temporal target is ambiguous; {facts}"
    elif case.expected_behavior == "conflict_warning":
        answer = f"Conflict warning: {facts}"
    else:
        answer = facts or "Answer supported by cited evidence."
    return {
        "answer": answer,
        "behavior": case.expected_behavior,
        "cited_evidence_ids": cited,
        "valid_time_used": case.expected_valid_time,
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": case.expected_behavior == "conflict_warning",
        "partial_or_refusal": case.expected_behavior in {"partial", "refuse"},
        "clarification_requested": case.expected_behavior == "clarify",
        "confidence": "low" if case.expected_behavior in {"partial", "refuse", "clarify"} else "high",
    }


def _dry_run_answer(prompt: str) -> dict[str, Any]:
    return {
        "answer": "DRY RUN: prompt generated without provider call.",
        "behavior": "partial",
        "cited_evidence_ids": [],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": True,
        "clarification_requested": False,
        "confidence": "low",
        "prompt_chars": len(prompt),
    }


def _vertex_answer(prompt: str, max_output_tokens: int) -> dict[str, Any]:
    from core.generator.vertex_provider import VertexGeminiProvider

    result = VertexGeminiProvider().synthesize_grounded_answer(
        prompt,
        temperature=0.0,
        max_output_tokens=max_output_tokens,
    )
    if not result.ok:
        detail = " ".join(item for item in (result.provider_error, result.debug) if item)
        raise ProviderCallError(detail or "Vertex provider failed.")
    try:
        json_text, recovery = _extract_json_object_with_metadata(result.text)
        payload = json.loads(json_text)
        _validate_answer_payload(payload)
        payload["__answer_json_recovered"] = recovery["answer_json_recovered"]
        payload["__answer_json_recovery_method"] = recovery["answer_json_recovery_method"]
        payload["__raw_response_preview"] = _preview(result.text)
        return payload
    except Exception as exc:
        raise ProviderJSONError(f"{exc}; raw_response_preview={_preview(result.text)}") from exc


def _build_vertex_provider() -> Any:
    from core.generator.vertex_provider import VertexGeminiProvider

    return VertexGeminiProvider()


def _postprocess_answer_with_cited_evidence(
    answer: dict[str, Any],
    evidence_rows: list[CorpusRow],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair answer shape only from selected evidence rows, never answer keys."""
    updated = dict(answer)
    metadata = {
        "answer_fact_postprocessed": False,
        "valid_time_fact_postprocessed": False,
        "citation_fact_postprocessed": False,
    }
    behavior = str(updated.get("behavior", "")).lower()
    updated["behavior"] = behavior
    row_by_id = {row.id: row for row in evidence_rows}

    cited = updated.get("cited_evidence_ids") or []
    if isinstance(cited, str):
        cited = [cited]
    if not isinstance(cited, list):
        cited = []
    cited = [str(item) for item in cited if item]

    if behavior == "answer" and not cited and evidence_rows and _selected_row_is_direct_answer(evidence_rows[0]):
        cited = [evidence_rows[0].id]
        metadata["citation_fact_postprocessed"] = True
        metadata["citation_fact_postprocess_source_id"] = evidence_rows[0].id
    updated["cited_evidence_ids"] = cited

    if updated.get("answer") is None:
        if behavior == "answer" and len(cited) == 1 and row_by_id.get(str(cited[0])) is not None:
            updated["answer"] = build_evidence_fact_sentence(row_by_id[str(cited[0])])
            metadata["answer_fact_postprocessed"] = True
            metadata["answer_fact_postprocess_source_id"] = str(cited[0])
        elif behavior in {"partial", "refuse", "clarify"}:
            updated["answer"] = ""

    if behavior != "answer":
        return updated, metadata

    if len(cited) != 1:
        return updated, metadata
    row = row_by_id.get(str(cited[0]))
    if row is None:
        return updated, metadata

    _repair_valid_time_from_cited_row(updated, row, metadata)
    answer_text = str(updated.get("answer", ""))
    if not _answer_missing_evidence_fact(answer_text, row):
        return updated, metadata

    sentence = build_evidence_fact_sentence(row)
    if sentence.lower() not in answer_text.lower():
        separator = " " if answer_text.strip().endswith(".") else ". "
        updated["answer"] = f"{answer_text.strip()}{separator}{sentence}".strip() if answer_text.strip() else sentence
    metadata["answer_fact_postprocessed"] = True
    metadata["answer_fact_postprocess_source_id"] = row.id
    return updated, metadata


def _pop_answer_recovery_metadata(answer: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer_json_recovered": bool(answer.pop("__answer_json_recovered", False)),
        "answer_json_recovery_method": answer.pop("__answer_json_recovery_method", None),
        "raw_response_preview": answer.pop("__raw_response_preview", None),
    }


def _repair_valid_time_from_cited_row(
    answer: dict[str, Any],
    row: CorpusRow,
    metadata: dict[str, Any],
) -> None:
    valid_from = row.valid_from
    if not valid_from:
        return
    current = answer.get("valid_time_used") or []
    if isinstance(current, str):
        current = [current]
    if not isinstance(current, list):
        current = []
    normalized = [str(item) for item in current if item]
    answer_text = str(answer.get("answer") or "")
    exact_date_in_answer = valid_from in answer_text
    has_exact = valid_from in normalized
    year_only = len(valid_from) >= 10 and valid_from[:4] in normalized and not has_exact
    if exact_date_in_answer or not normalized or year_only:
        if valid_from not in normalized:
            normalized.append(valid_from)
        if year_only:
            normalized = [item for item in normalized if item != valid_from[:4]]
        answer["valid_time_used"] = normalized
        metadata["valid_time_fact_postprocessed"] = True
        metadata["valid_time_fact_postprocess_source_id"] = row.id


def _answer_missing_evidence_fact(answer_text: str, row: CorpusRow) -> bool:
    lowered = answer_text.lower()
    checks = [row.entity, row.metric_or_claim, row.valid_from or row.transaction_time]
    if row.value is not None:
        checks.append(str(row.value))
    if row.unit:
        checks.append(row.unit)
    return any(str(item).lower() not in lowered for item in checks if item)


def _selected_row_is_direct_answer(row: CorpusRow) -> bool:
    return bool(
        row.id
        and row.temporal_type in {"valid_time_exact", "revision"}
        and (row.value is not None or row.raw_text)
        and (row.valid_from or row.transaction_time)
    )


def estimate_prompt_sizes(
    methods: list[str],
    corpus: list[CorpusRow],
    questions: list[QuestionCase],
    top_k: int,
) -> dict[str, dict[str, int]]:
    estimates: dict[str, dict[str, int]] = {}
    for method in methods:
        module = _method_module(method)
        sizes = []
        truncated = 0
        for case in questions:
            payload = module.build_prompt(case, corpus, top_k)
            sizes.append(len(payload["prompt"]))
            if payload.get("prompt_truncated"):
                truncated += 1
        estimates[method] = {
            "max_prompt_chars": max(sizes, default=0),
            "total_prompt_chars": sum(sizes),
            "truncated_cases": truncated,
        }
    return estimates


def _extract_json_object(text: str) -> str:
    return _extract_json_object_with_metadata(text)[0]


def _extract_json_object_with_metadata(text: str) -> tuple[str, dict[str, Any]]:
    # Recovery here is provider-format robustness only: use complete JSON
    # objects inside fences/prose, but never invent missing braces or fields.
    stripped = text.strip()
    method = "raw_json"
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
        method = "fenced_json"
    start = stripped.find("{")
    if start < 0:
        raise ValueError("Vertex response did not contain a JSON object.")
    if start > 0 and method == "raw_json":
        method = "prose_wrapped_json"
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(stripped)):
        char = stripped[idx]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                if idx < len(stripped) - 1 and stripped[idx + 1 :].strip():
                    method = "json_with_trailing_text" if method == "raw_json" else method
                return stripped[start : idx + 1], {
                    "answer_json_recovered": method != "raw_json",
                    "answer_json_recovery_method": method,
                }
    raise ValueError("Vertex response contained incomplete JSON.")


def _validate_answer_payload(payload: dict[str, Any]) -> None:
    required = {
        "answer",
        "behavior",
        "cited_evidence_ids",
        "valid_time_used",
        "transaction_time_used_as_valid_time",
        "conflict_warning",
        "partial_or_refusal",
        "clarification_requested",
        "confidence",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Vertex response missing required answer fields: {', '.join(missing)}")


def _retrieval_validation_result(case: QuestionCase, selected_evidence_ids: list[str]) -> dict[str, Any]:
    case_report = score_case(case, selected_evidence_ids)
    scores = dict(case_report["scores"])
    retrieval_pass = case_report.get("retrieval_pass")
    failure_reasons = []
    if retrieval_pass is False:
        failure_reasons.append(str(case_report["retrieval_pass_reason"]))
    return {
        "validator_type": "temporal_retrieval",
        "retrieval_only": True,
        "overall_pass": retrieval_pass,
        "retrieval_pass": retrieval_pass,
        "category_primary_pass": retrieval_pass,
        "retrieval_pass_reason": case_report["retrieval_pass_reason"],
        "scores": scores,
        "selected_evidence_ids": case_report["selected_evidence_ids"],
        "expected_evidence_ids": case_report["expected_evidence_ids"],
        "acceptable_evidence_ids": case_report["acceptable_evidence_ids"],
        "forbidden_evidence_ids": case_report["forbidden_evidence_ids"],
        "selected_expected_overlap": case_report["selected_expected_overlap"],
        "selected_acceptable_overlap": case_report["selected_acceptable_overlap"],
        "selected_forbidden_overlap": case_report["selected_forbidden_overlap"],
        "warnings": case_report["warnings"],
        "failure_reasons": failure_reasons,
    }


def _select_questions(questions: list[QuestionCase], limit: int | None, case_id: str | None) -> list[QuestionCase]:
    if case_id:
        questions = [case for case in questions if case.id == case_id]
    if limit is not None:
        questions = questions[:limit]
    return questions


class ProviderCallError(RuntimeError):
    """Provider call failed before a scorable model answer was available."""


class ProviderJSONError(RuntimeError):
    """Provider returned text that could not be converted into model JSON."""


class ProviderJSONRetryLimitError(ProviderJSONError):
    """Provider repeatedly returned non-JSON despite the JSON-specific retry cap."""


def _provider_error_result(
    *,
    method: str,
    case: QuestionCase,
    evidence_rows: list[CorpusRow],
    mode: str,
    latency_ms: float,
    prompt_preview: str | None,
    method_metadata: dict[str, Any],
    error: Exception,
    retry_attempts: int,
    json_parse_failures: int = 0,
) -> dict[str, Any]:
    output_contract_failure = isinstance(error, ProviderJSONError)
    failure_type = "answer_generation_incomplete_json" if output_contract_failure else "Provider Infrastructure Failure"
    return {
        "method": method,
        "case_id": case.id,
        "question": case.question,
        "category": case.category,
        "selected_evidence_ids": [row.id for row in evidence_rows],
        "prompt_truncated": False,
        "provider_mode": mode,
        "latency_ms": round(latency_ms, 2),
        "prompt_preview": prompt_preview,
        "answer": ModelAnswer.from_dict(
            {
                "answer": "",
                "behavior": "partial",
                "cited_evidence_ids": [],
                "valid_time_used": [],
                "transaction_time_used_as_valid_time": False,
                "conflict_warning": False,
                "partial_or_refusal": True,
                "clarification_requested": False,
                "confidence": "low",
            }
        ).to_dict(),
        "validation": _infrastructure_validation(failure_type),
        "status": "provider_error",
        "infrastructure_failure": True,
        "provider_output_contract_failure": output_contract_failure,
        "provider_error": _preview(str(error), limit=800),
        "failure_type": failure_type,
        "metadata": {
            **method_metadata,
            "retry_attempts": retry_attempts,
            "json_parse_failures": json_parse_failures,
            "provider_output_contract_failure": output_contract_failure,
            "raw_response_preview": _preview(str(error), limit=800),
            "provider_error_preview": _preview(str(error), limit=800),
        },
    }


def _infrastructure_validation(failure_type: str) -> dict[str, Any]:
    return {
        "validator_type": "temporal_retrieval",
        "retrieval_only": True,
        "retrieval_pass": False,
        "category_primary_pass": False,
        "retrieval_pass_reason": f"fail: {failure_type}",
        "scores": {},
        "selected_expected_overlap": [],
        "selected_acceptable_overlap": [],
        "selected_forbidden_overlap": [],
        "overall_pass": False,
        "infrastructure_failure": True,
        "provider_output_contract_failure": failure_type == "answer_generation_incomplete_json",
        "failure_reasons": [failure_type],
    }


def _first_metadata_value(results: list[dict[str, Any]], key: str) -> Any:
    for row in results:
        value = (row.get("metadata") or {}).get(key)
        if value is not None:
            return value
    return None


def _judge_skipped_validation(case_id: str, reason: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "judge_overall_pass": False,
        "strict_overall_pass": False,
        "criteria_passed": 0,
        "criteria_scores": {
            "temporal_scope_correct": 0,
            "factual_grounding": 0,
            "behavior_justified": 0,
            "transaction_time_clean": 0,
            "no_overconfidence": 0,
        },
        "criteria_reasons": {
            "temporal_scope_correct": reason,
            "factual_grounding": reason,
            "behavior_justified": reason,
            "transaction_time_clean": reason,
            "no_overconfidence": reason,
        },
        "judge_infrastructure_failure": True,
        "judge_reason": reason,
        "diagnostics": {
            "behavior_label_match": False,
            "cited_ids_grounded": False,
            "schema_fields_present": False,
        },
        "raw_run_scores": [],
        "judge_parse_failures": 0,
        "judge_provider_failures": 0,
        "judge_retry_attempts": 0,
        "judge_scored_runs": 0,
        "judge_unscored_runs": 0,
        "judge_recovered_partial_json_count": 0,
        "judge_runs": 0,
        "overall_pass": False,
        "failure_reasons": [reason],
    }


def _completed_case_ids(results: list[dict[str, Any]]) -> set[str]:
    return {
        row["case_id"]
        for row in results
        if row.get("case_id") and row.get("status", "completed") != "provider_error"
    }


def _load_existing_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not resume from invalid result JSON {path}: {exc}") from exc


def _sleep_after_vertex_call(mode: str, dry_run_prompts: bool, seconds: float) -> None:
    if mode == "vertex" and not dry_run_prompts and seconds > 0:
        time.sleep(seconds)


def _preview(text: str, limit: int = 500) -> str:
    return text.replace("\n", " ").strip()[:limit]


def _sanitize_suffix(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise SystemExit("--result-suffix may contain only letters, numbers, underscore, and hyphen.")
    return value


def _result_paths(method: str, suffix: str) -> tuple[Path, Path]:
    base = Path("benchmarks/layer2_crossdomain/results") / f"layer2_{method}_{suffix}_results"
    return base.with_suffix(".json"), base.with_suffix(".md")


if __name__ == "__main__":
    main()
