from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ANSWER_PATH = Path("benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl")
JUDGE_PATH = Path("benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.jsonl")
OUT_JSON = Path("chronorag/stdcomp/results/paper_tables/chronorag_qa50_extracted_values.json")
OUT_MD = Path("docs/paper_assets/chronorag_qa50_extracted_values.md")


def main() -> None:
    answer_rows = read_jsonl(ANSWER_PATH)
    judge_rows = read_jsonl(JUDGE_PATH)
    payload = extract_values(answer_rows, judge_rows)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


def extract_values(answer_rows: list[dict[str, Any]], judge_rows: list[dict[str, Any]]) -> dict[str, Any]:
    cases = len(judge_rows)
    answer_cases = len(answer_rows)
    deterministic = [row.get("deterministic_validation") or {} for row in judge_rows]
    judge = [row.get("judge_validation") or {} for row in judge_rows]
    answer_validation = [row.get("validation") or {} for row in answer_rows]
    retrieval_metadata = [row.get("retrieval_metadata") or {} for row in answer_rows]

    metrics = {
        "cases": metric_value(cases, cases, "judge rows", "count"),
        "answer_rows": metric_value(answer_cases, answer_cases, "answer rows", "count"),
        "strict_combined_pass": bool_ratio(judge_rows, "combined_pass", "judge row combined_pass"),
        "deterministic_hard_contract_pass": bool_ratio(
            judge_rows,
            "deterministic_overall_contract_pass",
            "judge row deterministic_overall_contract_pass",
        ),
        "judge_overall_pass": bool_ratio(judge, "overall_judge_pass", "judge_validation.overall_judge_pass"),
        "judge_semantic_pass": bool_ratio(judge, "semantic_answer_correct", "judge_validation.semantic_answer_correct"),
        "expected_evidence_cited": bool_ratio(
            deterministic,
            "expected_evidence_cited",
            "deterministic_validation.expected_evidence_cited",
        ),
        "valid_time_correct": bool_ratio(judge, "valid_time_correct", "judge_validation.valid_time_correct"),
        "valid_time_present": bool_ratio(deterministic, "valid_time_present", "deterministic_validation.valid_time_present"),
        "expected_evidence_retrieved_pre_injection_any": pre_injection_any(answer_rows),
        "expected_evidence_retrieved_pre_injection_all": pre_injection_all(answer_rows),
        "expected_evidence_available_after_injection": bool_ratio(
            retrieval_metadata,
            "expected_evidence_available_to_model",
            "retrieval_metadata.expected_evidence_available_to_model",
            fallback_rows=answer_validation,
            fallback_key="expected_evidence_available_to_model",
            fallback_path="validation.expected_evidence_available_to_model",
        ),
        "expected_evidence_injected": bool_ratio(
            retrieval_metadata,
            "expected_evidence_injected",
            "retrieval_metadata.expected_evidence_injected",
        ),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [str(ANSWER_PATH), str(JUDGE_PATH)],
        "rerun_performed": False,
        "metrics": metrics,
        "notes": [
            "Values extracted from existing ChronoRAG QA50 answer and judge artifacts only.",
            "Pre-injection any expected evidence is computed from expected_evidence_ids intersecting retrieval_metadata.retrieved_evidence_ids_before_injection.",
            "Pre-injection all expected evidence uses retrieval_metadata.expected_evidence_retrieved_before_injection when present; this field is all-expected coverage in the existing runner.",
            "Post-injection availability uses retrieval_metadata.expected_evidence_available_to_model with validation.expected_evidence_available_to_model as fallback.",
        ],
    }


def pre_injection_any(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    missing_path_count = 0
    for row in rows:
        expected = set(row.get("expected_evidence_ids") or [])
        metadata = row.get("retrieval_metadata") or {}
        retrieved = metadata.get("retrieved_evidence_ids_before_injection")
        if retrieved is None:
            missing_path_count += 1
            retrieved = row.get("retrieved_evidence_ids_before_injection") or []
        if expected and expected & set(retrieved or []):
            count += 1
    metric = metric_value(count, len(rows), "expected_evidence_ids ∩ retrieval_metadata.retrieved_evidence_ids_before_injection", "ratio")
    if missing_path_count:
        metric["notes"] = [f"retrieval_metadata.retrieved_evidence_ids_before_injection missing for {missing_path_count} rows; top-level fallback used where available."]
    return metric


def pre_injection_all(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    missing_path_count = 0
    for row in rows:
        metadata = row.get("retrieval_metadata") or {}
        if "expected_evidence_retrieved_before_injection" in metadata:
            if metadata.get("expected_evidence_retrieved_before_injection") is True:
                count += 1
            continue
        missing_path_count += 1
        expected = set(row.get("expected_evidence_ids") or [])
        retrieved = set(metadata.get("retrieved_evidence_ids_before_injection") or row.get("retrieved_evidence_ids_before_injection") or [])
        if expected and expected.issubset(retrieved):
            count += 1
    metric = metric_value(count, len(rows), "retrieval_metadata.expected_evidence_retrieved_before_injection", "ratio")
    if missing_path_count:
        metric["notes"] = [f"retrieval_metadata.expected_evidence_retrieved_before_injection missing for {missing_path_count} rows; all-expected set fallback used."]
    return metric


def bool_ratio(
    rows: list[dict[str, Any]],
    key: str,
    field_path: str,
    *,
    fallback_rows: list[dict[str, Any]] | None = None,
    fallback_key: str | None = None,
    fallback_path: str | None = None,
) -> dict[str, Any]:
    values = [row.get(key) for row in rows]
    if not any(isinstance(value, bool) for value in values) and fallback_rows is not None and fallback_key is not None:
        fallback_values = [row.get(fallback_key) for row in fallback_rows]
        if any(isinstance(value, bool) for value in fallback_values):
            count = sum(1 for value in fallback_values if value is True)
            metric = metric_value(count, len(fallback_rows), fallback_path or fallback_key, "ratio")
            metric["notes"] = [f"{field_path} unavailable; used {fallback_path or fallback_key}."]
            return metric
    if not any(isinstance(value, bool) for value in values):
        return {
            "value": None,
            "count": None,
            "denominator": len(rows),
            "field_path": field_path,
            "status": "n/a",
            "missing_field_path": field_path,
        }
    count = sum(1 for value in values if value is True)
    return metric_value(count, len(rows), field_path, "ratio")


def metric_value(count: int, denominator: int, field_path: str, metric_type: str) -> dict[str, Any]:
    return {
        "value": count / denominator if denominator else None,
        "count": count,
        "denominator": denominator,
        "field_path": field_path,
        "type": metric_type,
        "status": "available",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ChronoRAG QA50 Extracted Values",
        "",
        "Extracted from existing artifacts only. No model, retriever, validator, or judge rerun was performed.",
        "",
        "| Metric | Value | Count | Field path / derivation |",
        "|---|---:|---:|---|",
    ]
    for key, metric in payload["metrics"].items():
        value = metric.get("value")
        rendered = "n/a" if value is None else (str(value) if metric.get("type") == "count" else f"{value:.4f}")
        count = "n/a" if metric.get("count") is None else f"{metric.get('count')}/{metric.get('denominator')}"
        lines.append(f"| `{key}` | {rendered} | {count} | {metric.get('field_path') or metric.get('missing_field_path')} |")
    lines.extend(["", "Notes:"])
    for note in payload["notes"]:
        lines.append(f"- {note}")
    for key, metric in payload["metrics"].items():
        for note in metric.get("notes") or []:
            lines.append(f"- `{key}`: {note}")
    lines.append("")
    return "\n".join(lines)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Required artifact is missing: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


if __name__ == "__main__":
    main()
