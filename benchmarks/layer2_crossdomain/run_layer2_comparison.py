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

from benchmarks.layer2_crossdomain.reporting import metric_summary, write_comparison_report, write_method_results
from benchmarks.layer2_crossdomain.schemas import CorpusRow, ModelAnswer, QuestionCase, load_corpus, load_questions
from benchmarks.layer2_crossdomain.validator import validate_answer

METHODS = ("direct_llm_full_context", "metadata_temporal_rag", "chronorag_full")
DEFAULT_CORPUS = "benchmarks/layer2_crossdomain/data/layer2_corpus.sample.jsonl"
DEFAULT_QUESTIONS = "benchmarks/layer2_crossdomain/data/layer2_questions.sample.jsonl"
REAL_CORPUS = "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
REAL_QUESTIONS = "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Layer 2 cross-domain comparison framework.")
    parser.add_argument("--method", choices=[*METHODS, "all"], default="all")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS)
    parser.add_argument("--questions", default=DEFAULT_QUESTIONS)
    parser.add_argument("--dataset", choices=["sample", "real"], default="sample")
    parser.add_argument("--mode", choices=["light", "vertex"], default="light")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--dry-run-prompts", action="store_true")
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--result-suffix", default="default")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    suffix = _sanitize_suffix(args.result_suffix)
    corpus_path = REAL_CORPUS if args.dataset == "real" and args.corpus == DEFAULT_CORPUS else args.corpus
    questions_path = REAL_QUESTIONS if args.dataset == "real" and args.questions == DEFAULT_QUESTIONS else args.questions
    corpus = load_corpus(corpus_path)
    questions = _select_questions(load_questions(questions_path), args.limit, args.case_id)
    selected_methods = list(METHODS) if args.method == "all" else [args.method]
    estimated_calls = len(questions) * len(selected_methods) if args.mode == "vertex" else 0
    prompt_estimates = estimate_prompt_sizes(selected_methods, corpus, questions, args.top_k)

    print(f"Mode: {args.mode}")
    print(f"Methods: {', '.join(selected_methods)}")
    print(f"Selected cases: {len(questions)}")
    print(f"Estimated Vertex calls: {estimated_calls}")
    for method, estimate in prompt_estimates.items():
        print(
            f"Prompt estimate {method}: max_chars={estimate['max_prompt_chars']}, "
            f"truncated_cases={estimate['truncated_cases']}"
        )

    if args.estimate_only:
        return

    payloads = []
    for method in selected_methods:
        payload = run_method(
            method=method,
            corpus=corpus,
            questions=questions,
            mode=args.mode,
            top_k=args.top_k,
            dry_run_prompts=args.dry_run_prompts,
            max_output_tokens=args.max_output_tokens,
            suffix=suffix,
        )
        payloads.append(payload)
        json_path, md_path = _result_paths(method, suffix)
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
) -> dict[str, Any]:
    module = _method_module(method)
    results = []
    started = time.perf_counter()
    for case in questions:
        method_payload = module.build_prompt(case, corpus, top_k)
        prompt = method_payload["prompt"]
        evidence_rows = method_payload["evidence_rows"]
        truncated = bool(method_payload.get("prompt_truncated"))
        method_metadata = dict(method_payload.get("metadata") or {})
        case_started = time.perf_counter()
        if dry_run_prompts:
            answer = _dry_run_answer(prompt)
        elif mode == "light":
            answer = _light_answer(case, evidence_rows)
        else:
            answer = _vertex_answer(prompt, max_output_tokens)
        latency_ms = (time.perf_counter() - case_started) * 1000.0
        model_answer = ModelAnswer.from_dict(answer).to_dict()
        validation = validate_answer(case, answer, corpus)
        results.append(
            {
                "method": method,
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "selected_evidence_ids": [row.id for row in evidence_rows],
                "prompt_truncated": truncated,
                "provider_mode": mode,
                "latency_ms": round(latency_ms, 2),
                "prompt_preview": prompt[:1200] if dry_run_prompts else None,
                "answer": model_answer,
                "validation": validation.to_dict(),
                "metadata": {
                    **method_metadata,
                    "dry_run_prompts": dry_run_prompts,
                },
            }
        )
    latency_ms = (time.perf_counter() - started) * 1000.0
    return {
        "benchmark": "layer2_crossdomain",
        "method": method,
        "mode": mode,
        "result_suffix": suffix,
        "corpus_rows": len(corpus),
        "question_count": len(questions),
        "estimated_calls": len(questions) if mode == "vertex" and not dry_run_prompts else 0,
        "top_k": top_k,
        "prompt_truncation_count": sum(1 for row in results if row["prompt_truncated"]),
        "average_selected_evidence": (
            sum(len(row["selected_evidence_ids"]) for row in results) / len(results) if results else 0.0
        ),
        "latency_ms": round(latency_ms, 2),
        "summary": metric_summary(results),
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
        raise SystemExit(result.provider_error or "Vertex provider failed.")
    return json.loads(_extract_json_object(result.text))


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
    start = text.find("{")
    if start < 0:
        raise SystemExit("Vertex response did not contain a JSON object.")
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        char = text[idx]
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
                return text[start : idx + 1]
    raise SystemExit("Vertex response contained incomplete JSON.")


def _select_questions(questions: list[QuestionCase], limit: int | None, case_id: str | None) -> list[QuestionCase]:
    if case_id:
        questions = [case for case in questions if case.id == case_id]
    if limit is not None:
        questions = questions[:limit]
    return questions


def _sanitize_suffix(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise SystemExit("--result-suffix may contain only letters, numbers, underscore, and hyphen.")
    return value


def _result_paths(method: str, suffix: str) -> tuple[Path, Path]:
    base = Path("benchmarks/layer2_crossdomain/results") / f"layer2_{method}_{suffix}_results"
    return base.with_suffix(".json"), base.with_suffix(".md")


if __name__ == "__main__":
    main()
