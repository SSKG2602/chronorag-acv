from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.answer_validation_v2 import (
    build_chronorag_grounded_synthesis_prompt,
    build_tcc_evidence_cards,
    effective_top_k_for_case,
    load_cases,
    load_corpus,
    retrieve_top_k,
    run_cases,
    write_results,
)


LIGHT_JSON = Path("benchmarks/results/temporal_answer_validation_v2_light_results.json")
LIGHT_MD = Path("benchmarks/results/temporal_answer_validation_v2_light_results.md")
VERTEX_JSON = Path("benchmarks/results/temporal_answer_validation_v2_vertex_results.json")
VERTEX_MD = Path("benchmarks/results/temporal_answer_validation_v2_vertex_results.md")
DRY_JSON = Path("benchmarks/results/temporal_answer_validation_v2_dry_run_prompts.json")
DRY_MD = Path("benchmarks/results/temporal_answer_validation_v2_dry_run_prompts.md")
SUFFIX_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _selected_cases(cases: List[Dict[str, Any]], *, limit: int | None, case_id: str | None) -> List[Dict[str, Any]]:
    if case_id:
        selected = [case for case in cases if case["id"] == case_id]
        if not selected:
            raise SystemExit(f"Unknown case id: {case_id}")
        return selected
    return cases[:limit] if limit is not None else cases


def _sanitize_result_suffix(result_suffix: str | None) -> str | None:
    if result_suffix is None:
        return None
    if not SUFFIX_RE.fullmatch(result_suffix):
        raise SystemExit("--result-suffix may contain only letters, numbers, underscore, and hyphen.")
    return result_suffix


def _suffixed_outputs(mode: str, dry_run: bool, result_suffix: str) -> tuple[Path, Path]:
    if dry_run:
        stem = f"temporal_answer_validation_v2_dry_run_{result_suffix}_prompts"
    elif mode == "vertex":
        stem = f"temporal_answer_validation_v2_vertex_{result_suffix}_results"
    else:
        stem = f"temporal_answer_validation_v2_light_{result_suffix}_results"
    return Path("benchmarks/results") / f"{stem}.json", Path("benchmarks/results") / f"{stem}.md"


def _default_outputs(
    mode: str,
    dry_run: bool,
    output_json: str | None,
    output_md: str | None,
    result_suffix: str | None,
) -> tuple[Path, Path]:
    if output_json or output_md:
        default_json, default_md = _default_outputs(mode, dry_run, None, None, None)
        return Path(output_json) if output_json else default_json, Path(output_md) if output_md else default_md
    if result_suffix:
        return _suffixed_outputs(mode, dry_run, result_suffix)
    if dry_run:
        return DRY_JSON, DRY_MD
    if mode == "vertex":
        return VERTEX_JSON, VERTEX_MD
    return LIGHT_JSON, LIGHT_MD


def _check_vertex_ready() -> None:
    missing = [name for name in ["GOOGLE_CLOUD_PROJECT"] if not os.getenv(name)]
    if missing:
        raise SystemExit(
            "Vertex mode requested but required environment variables are missing: "
            + ", ".join(missing)
            + ". Set GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and VERTEX_MODEL_ID as needed."
        )


def _write_dry_run_prompts(
    *,
    cases: List[Dict[str, Any]],
    corpus: List[Dict[str, Any]],
    top_k: int,
    dynamic_top_k: bool,
    use_vector: bool,
    command: str,
    output_json: Path,
    output_md: Path,
    result_suffix: str | None,
) -> None:
    prompts = []
    for case in cases:
        effective_top_k = effective_top_k_for_case(case, top_k, dynamic_top_k)
        cards = build_tcc_evidence_cards(retrieve_top_k(case["question"], corpus, top_k=effective_top_k, use_vector=use_vector))
        prompts.append(
            {
                "case_id": case["id"],
                "top_k": top_k,
                "effective_top_k": effective_top_k,
                "retrieved_evidence_ids": [card["evidence_id"] for card in cards],
                "prompt": build_chronorag_grounded_synthesis_prompt(case, cards),
            }
        )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    payload = {"command": command, "result_suffix": result_suffix, "prompt_count": len(prompts), "prompts": prompts}
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Temporal Answer Validation v2 Dry-Run Prompts", "", f"```bash\n{command}\n```"]
    for item in prompts:
        lines.extend(
            [
                "",
                f"## {item['case_id']}",
                "",
                f"Top-k: {item['top_k']} (effective: {item['effective_top_k']})",
                "",
                f"Evidence IDs: {', '.join(item['retrieved_evidence_ids'])}",
                "",
                "```text",
                item["prompt"],
                "```",
            ]
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ChronoRAG Layer 1B answer-validation benchmark.")
    parser.add_argument("--mode", choices=["light", "vertex"], default="light")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--dry-run-prompts", action="store_true")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--skip-vector", action="store_true", help="Explicitly downgrade Vertex mode to lexical+temporal retrieval.")
    parser.add_argument(
        "--dynamic-top-k",
        action="store_true",
        help="Expand complex answer-validation cases up to top-k 7-10 while preserving the base --top-k default.",
    )
    parser.add_argument("--output-md", default=None)
    parser.add_argument("--output-json", default=None)
    parser.add_argument(
        "--result-suffix",
        default=None,
        help="Write default outputs with a safe suffix, for example vertex_topk5_results.",
    )
    args = parser.parse_args()
    result_suffix = _sanitize_result_suffix(args.result_suffix)
    # Vertex JSON responses are brittle when truncated. Use a safer provider
    # default while preserving explicit CLI overrides and the light-mode default.
    max_output_tokens = args.max_output_tokens
    if max_output_tokens is None:
        max_output_tokens = 2048 if args.mode == "vertex" else 512

    cases = _selected_cases(load_cases(), limit=args.limit, case_id=args.case_id)
    corpus = load_corpus()
    command = " ".join(sys.argv)
    vertex_calls = len(cases) if args.mode == "vertex" and not args.dry_run_prompts else 0
    use_vector = args.mode == "vertex" and not args.skip_vector

    print(f"Mode: {args.mode}")
    print(f"Selected cases: {len(cases)}")
    print(f"Estimated Vertex calls: {vertex_calls}")
    print(f"Dynamic top-k: {'enabled' if args.dynamic_top_k else 'disabled'}")
    if args.mode == "vertex" and args.skip_vector:
        print("Retrieval: explicit --skip-vector downgrade to lexical + temporal metadata scoring")
    elif args.mode == "vertex":
        print("Retrieval: hybrid lexical + BGE vector + temporal metadata scoring")
    else:
        print("Retrieval: deterministic light lexical + temporal metadata scoring")

    if args.estimate_only:
        return

    if args.mode == "vertex":
        _check_vertex_ready()

    output_json, output_md = _default_outputs(args.mode, args.dry_run_prompts, args.output_json, args.output_md, result_suffix)

    if args.dry_run_prompts:
        _write_dry_run_prompts(
            cases=cases,
            corpus=corpus,
            top_k=args.top_k,
            dynamic_top_k=args.dynamic_top_k,
            use_vector=use_vector,
            command=command,
            output_json=output_json,
            output_md=output_md,
            result_suffix=result_suffix,
        )
        print(f"Wrote: {output_json}")
        print(f"Wrote: {output_md}")
        return

    result = run_cases(
        cases,
        corpus,
        mode=args.mode,
        top_k=args.top_k,
        temperature=args.temperature,
        max_output_tokens=max_output_tokens,
        use_vector=use_vector,
        dynamic_top_k=args.dynamic_top_k,
    )
    payload = {
        "benchmark": "temporal_answer_validation_v2",
        "mode": args.mode,
        "command": command,
        "top_k": args.top_k,
        "dynamic_top_k": args.dynamic_top_k,
        "result_suffix": result_suffix,
        "case_count": len(cases),
        "corpus_row_count": len(corpus),
        "retrieval": "hybrid_lexical_bge_temporal" if use_vector else "lexical_temporal",
        "skip_vector": args.skip_vector,
        "max_output_tokens": max_output_tokens,
        "temperature": args.temperature,
        "metrics": result["metrics"],
        "details": result["details"],
    }
    write_results(payload, output_json, output_md)
    print(f"Wrote: {output_json}")
    print(f"Wrote: {output_md}")


if __name__ == "__main__":
    main()
