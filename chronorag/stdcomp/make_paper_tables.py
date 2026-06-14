from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER_DIR = Path("docs/paper_assets")
TABLE_DIR = Path("chronorag/stdcomp/results/paper_tables")

LAYER2A_STD_PATH = Path("chronorag/stdcomp/results/stdcomp_layer2a_comparison.json")
LAYER2A_ABLATION_PATH = Path("benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json")
QA50_BASELINE_DIR = Path("chronorag/stdcomp/results/qa50_llm_baselines")
QA50_CHRONORAG_JUDGE_PATH = Path("benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.jsonl")
QA50_CHRONORAG_ANSWER_PATH = Path(
    "benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl"
)
QA50_CHRONORAG_EXTRACTED_PATH = Path("chronorag/stdcomp/results/paper_tables/chronorag_qa50_extracted_values.json")

TABLE_SPECS = [
    (
        "table1_layer2a_retrieval_standard_comparison",
        "Layer 2A Retrieval-Only Standard Comparison",
    ),
    (
        "table2_layer2a_ablation_comparison",
        "Layer 2A Ablation Comparison",
    ),
    (
        "table3_qa50_llm_post_filter_baselines",
        "QA50 Standard Retrieval + LLM Temporal Post-Filtering Baselines",
    ),
    (
        "table4_qa50_answer_level_comparison",
        "QA50 Answer-Level Comparison",
    ),
]


def main() -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    generated = [
        write_table1(),
        write_table2(),
        write_table3(),
        write_table4(),
    ]
    write_index(generated)
    for item in generated:
        print(f"Wrote {item['markdown_path']}")
        print(f"Wrote {item['csv_path']}")
        print(f"Wrote {item['json_path']}")
    print(f"Wrote {PAPER_DIR / 'chrono_tables_index.md'}")


def write_table1() -> dict[str, Any]:
    payload = load_json(LAYER2A_STD_PATH)
    summary = {row["method"]: row for row in payload.get("summary") or []}
    order = [
        ("bm25", "BM25"),
        ("dense_only", "Dense-only"),
        ("date_filter_rag", "Date-filter RAG"),
        ("metadata_temporal_rag", "Metadata Temporal RAG"),
        ("chronorag_full", "ChronoRAG Full"),
    ]
    rows = []
    for method, label in order:
        source = summary.get(method, {})
        cases = source.get("cases")
        rows.append(
            {
                "method": label,
                "cases": cases,
                "hit_at_1": source.get("hit@1"),
                "hit_at_5": source.get("hit@5"),
                "mrr_at_5": source.get("mrr@5"),
                "forbidden_absent_at_5": source.get("forbidden_absent@5"),
                "category_primary_pass": source.get("category_primary_pass"),
            }
        )
    meta = base_meta(
        table_id="table1_layer2a_retrieval_standard_comparison",
        title="Layer 2A retrieval-only standard comparison",
        sources=[LAYER2A_STD_PATH],
    )
    meta["corpus"] = payload.get("corpus")
    meta["queries"] = payload.get("queries")
    meta["top_k"] = payload.get("top_k")
    notes = [
        "Extracted from existing Layer 2A standard-comparison artifact; no retrieval or model rerun.",
        f"Top-k: {payload.get('top_k')}. Benchmark: Layer 2A 200-case retrieval-only comparison.",
        "Metrics are scored over selected evidence IDs.",
        "BM25 and Date-filter RAG have higher broad Hit@5, but ChronoRAG Full has stronger Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass.",
        "This supports temporal-validity retrieval, not generic retrieval superiority.",
        "Forbidden Absent@5 and Category Primary Pass complement Hit@k and MRR@5 by measuring temporal-invalidity exclusion and source/category correctness.",
    ]
    columns = [
        ("method", "Method"),
        ("cases", "Cases"),
        ("hit_at_1", "Hit@1"),
        ("hit_at_5", "Hit@5"),
        ("mrr_at_5", "MRR@5"),
        ("forbidden_absent_at_5", "Forbidden Absent@5"),
        ("category_primary_pass", "Category Primary Pass"),
    ]
    return write_outputs(meta, rows, columns, notes)


def write_table2() -> dict[str, Any]:
    payload = load_json(LAYER2A_ABLATION_PATH)
    by_method = {row["method"]: row for row in payload.get("overall") or []}
    order = [
        ("chronorag_full", "ChronoRAG Full"),
        ("metadata_temporal_rag", "Metadata Temporal RAG"),
        ("chronorag_no_temporal_precision", "No Temporal Precision"),
        ("chronorag_no_slot_assembler", "No Slot Assembler"),
        ("chronorag_score_only", "Score-only"),
        ("chronorag_no_tcc", "No TCC"),
        ("chronorag_no_transaction_role", "No Transaction Role"),
        ("chronorag_no_source_metric", "No Source/Metric Adjustment"),
    ]
    rows = []
    for method, label in order:
        if method not in by_method:
            continue
        source = by_method[method]
        rows.append(
            {
                "method": label,
                "artifact_method": method,
                "cases": source.get("evaluated_cases"),
                "hit_at_1": source.get("generic_hit_at_1"),
                "hit_at_5": source.get("generic_hit_at_5"),
                "mrr_at_5": None,
                "forbidden_absent_at_5": source.get("forbidden_absent_at_5"),
                "category_primary_pass": source.get("category_primary_pass"),
            }
        )
    meta = base_meta(
        table_id="table2_layer2a_ablation_comparison",
        title="Layer 2A ablation comparison",
        sources=[LAYER2A_ABLATION_PATH],
    )
    meta["suffix"] = payload.get("suffix")
    meta["note"] = payload.get("note")
    notes = [
        "Extracted from existing Layer 2A ablation artifact; no retrieval, model, validator, or judge rerun.",
        "MRR@5 is n/a because this ablation artifact does not contain MRR values.",
        "Rows include the requested ablations plus other clearly named variants present in the artifact.",
        "The Score-only ablation achieved the highest raw Hit@5 at 0.9850, but Forbidden Absent@5 fell to 0.6500 and Category Primary Pass fell to 0.5625.",
        "ChronoRAG Full achieved lower broad Hit@5 at 0.8950 but much stronger Forbidden Absent@5 at 0.9950 and Category Primary Pass at 0.9625.",
    ]
    columns = [
        ("method", "Method"),
        ("cases", "Cases"),
        ("hit_at_1", "Hit@1"),
        ("hit_at_5", "Hit@5"),
        ("mrr_at_5", "MRR@5"),
        ("forbidden_absent_at_5", "Forbidden Absent@5"),
        ("category_primary_pass", "Category Primary Pass"),
    ]
    return write_outputs(meta, rows, columns, notes)


def write_table3() -> dict[str, Any]:
    paths = {
        "bm25": QA50_BASELINE_DIR / "bm25_llm_qa50_metrics.json",
        "dense": QA50_BASELINE_DIR / "dense_llm_qa50_metrics.json",
        "date_filter": QA50_BASELINE_DIR / "date_filter_llm_qa50_metrics.json",
    }
    manifest_path = QA50_BASELINE_DIR / "qa50_llm_run_manifest.json"
    manifest = load_json(manifest_path)
    labels = {
        "bm25": "BM25 + LLM",
        "dense": "Dense-only + LLM",
        "date_filter": "Date-filter RAG + LLM",
    }
    rows = []
    for method in ("bm25", "dense", "date_filter"):
        metrics = load_json(paths[method])
        rows.append(qa50_baseline_row(labels[method], metrics))
    meta = base_meta(
        table_id="table3_qa50_llm_post_filter_baselines",
        title="QA50 standard retrieval + LLM temporal post-filtering baselines",
        sources=[*paths.values(), manifest_path],
    )
    meta["manifest"] = manifest
    notes = [
        "Extracted from existing QA50 LLM baseline artifacts; no retriever, Vertex/Gemini, validator, or judge rerun.",
        "All methods use top-k=5, Gemini 2.5 Flash, temperature 0.0, same QA50 cases, same 5,000-row corpus, same prompt template, and same validator/judge settings.",
        "Gold evidence IDs were not included in prompts.",
        "The existing Layer 2B answer schema does not expose a separate transaction_time_used_as_valid_time field; valid-time correctness is reported instead.",
        "Despite explicit instructions to distinguish valid time from transaction time, BM25 + LLM, Dense-only + LLM, and Date-filter RAG + LLM reached strict combined pass of 0.4000, 0.3200, and 0.4000 respectively.",
    ]
    columns = table3_columns()
    return write_outputs(meta, rows, columns, notes, count_denominator=50)


def write_table4() -> dict[str, Any]:
    baseline_paths = {
        "bm25": QA50_BASELINE_DIR / "bm25_llm_qa50_metrics.json",
        "dense": QA50_BASELINE_DIR / "dense_llm_qa50_metrics.json",
        "date_filter": QA50_BASELINE_DIR / "date_filter_llm_qa50_metrics.json",
    }
    labels = {
        "bm25": "BM25 + LLM",
        "dense": "Dense-only + LLM",
        "date_filter": "Date-filter RAG + LLM",
    }
    rows = []
    for method in ("bm25", "dense", "date_filter"):
        metrics = load_json(baseline_paths[method])
        row = qa50_baseline_row(labels[method], metrics)
        row["retrieval_hit5_or_evidence_available"] = metrics.get("retrieval_hit@5")
        row["retrieval_hit5_or_evidence_available_note"] = "Retrieval Hit@5"
        row["notes"] = "Standard retrieval top-k=5; LLM prompt handles temporal filtering."
        rows.append(row)

    judge_rows = read_jsonl(QA50_CHRONORAG_JUDGE_PATH)
    answer_rows = read_jsonl(QA50_CHRONORAG_ANSWER_PATH)
    rows.extend(chronorag_qa50_rows(judge_rows, answer_rows))

    table4_sources = [*baseline_paths.values(), QA50_CHRONORAG_JUDGE_PATH, QA50_CHRONORAG_ANSWER_PATH]
    if QA50_CHRONORAG_EXTRACTED_PATH.exists():
        table4_sources.append(QA50_CHRONORAG_EXTRACTED_PATH)
    meta = base_meta(
        table_id="table4_qa50_answer_level_comparison",
        title="QA50 answer-level comparison",
        sources=table4_sources,
    )
    notes = [
        "Answer-level QA50 comparison extracted from existing artifacts; no model, retriever, validator, or judge rerun.",
        "ChronoRAG Full result is an existing prior L2B result and was not rerun.",
        "Standard retrieval + LLM baselines were run with the same LLM model and validator where possible.",
        "ChronoRAG used retrieval-layer temporal grounding; standard baselines used normal retrieval and relied on the LLM prompt to distinguish valid time from transaction time.",
        "Baseline methods are evaluated without evidence injection. ChronoRAG pre-injection evidence availability is the fair retrieval-availability comparison point. ChronoRAG post-injection answer-level results are reported separately to show performance when expected evidence is available to the generator.",
        "ChronoRAG pre-injection any expected evidence is 0.7400 (37/50), pre-injection all expected evidence is 0.6400 (32/50), and post-injection evidence available is 1.0000 (50/50).",
    ]
    columns = [
        ("method", "Method"),
        ("cases", "Cases"),
        ("retrieval_hit5_or_evidence_available", "Retrieval Hit@5 / Evidence Available"),
        ("strict_combined_pass", "Strict Combined Pass"),
        ("deterministic_hard_contract_pass", "Deterministic Hard-Contract Pass"),
        ("llm_judge_overall_pass", "LLM Judge Overall Pass"),
        ("llm_judge_semantic_pass", "LLM Judge Semantic Pass"),
        ("expected_evidence_cited", "Expected Evidence Cited"),
        ("valid_time_used_correct", "Valid Time Used Correct"),
        ("notes", "Notes"),
    ]
    return write_outputs(meta, rows, columns, notes, count_denominator=50)


def qa50_baseline_row(label: str, metrics: dict[str, Any]) -> dict[str, Any]:
    cases = metrics.get("cases")
    return {
        "method": label,
        "cases": cases,
        "retrieval_hit_at_1": metrics.get("retrieval_hit@1"),
        "retrieval_hit_at_5": metrics.get("retrieval_hit@5"),
        "retrieval_mrr_at_5": metrics.get("retrieval_mrr@5"),
        "strict_combined_pass": metrics.get("strict_combined_pass"),
        "deterministic_hard_contract_pass": metrics.get("deterministic_hard_contract_pass"),
        "llm_judge_overall_pass": metrics.get("llm_judge_overall_pass"),
        "llm_judge_semantic_pass": metrics.get("llm_judge_semantic_pass"),
        "valid_time_used_correct": metrics.get("valid_time_used_correct"),
        "expected_evidence_cited": metrics.get("expected_evidence_cited"),
        "provider_errors": metrics.get("provider_errors"),
        "judge_errors": metrics.get("judge_errors"),
        "answer_correctness": metrics.get("answer_correctness"),
        "expected_evidence_available_to_model": metrics.get("expected_evidence_available_to_model"),
    }


def chronorag_qa50_rows(judge_rows: list[dict[str, Any]], answer_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = len(judge_rows)
    deterministic = [row.get("deterministic_validation") or {} for row in judge_rows]
    judge = [row.get("judge_validation") or {} for row in judge_rows]
    answer_validation = [row.get("validation") or {} for row in answer_rows]
    pre_any_count = sum(
        bool(set(row.get("expected_evidence_ids") or []) & set((row.get("retrieval_metadata") or {}).get("retrieved_evidence_ids_before_injection") or []))
        for row in answer_rows
    )
    pre_all_count = sum(
        bool((row.get("retrieval_metadata") or {}).get("expected_evidence_retrieved_before_injection"))
        for row in answer_rows
    )
    available_count = sum(bool(validation.get("expected_evidence_available_to_model")) for validation in answer_validation)
    pre_row = {
        "method": "ChronoRAG Full - pre-injection retrieval",
        "cases": cases,
        "retrieval_hit5_or_evidence_available": ratio(pre_any_count, len(answer_rows)),
        "retrieval_hit5_or_evidence_available_note": "Any expected evidence retrieved before complete-evidence injection",
        "strict_combined_pass": None,
        "deterministic_hard_contract_pass": None,
        "llm_judge_overall_pass": None,
        "llm_judge_semantic_pass": None,
        "expected_evidence_cited": None,
        "valid_time_used_correct": None,
        "pre_injection_any_expected_evidence_count": pre_any_count,
        "pre_injection_all_expected_evidence_count": pre_all_count,
        "notes": "Fair retrieval availability comparison; no complete-evidence injection.",
    }
    post_row = {
        "method": "ChronoRAG Full - post-injection answer setting",
        "cases": cases,
        "retrieval_hit5_or_evidence_available": ratio(available_count, len(answer_rows)),
        "retrieval_hit5_or_evidence_available_note": "Expected evidence available to generator after complete-evidence injection",
        "strict_combined_pass": ratio_count(judge_rows, "combined_pass"),
        "deterministic_hard_contract_pass": ratio_count(judge_rows, "deterministic_overall_contract_pass"),
        "llm_judge_overall_pass": ratio_count(judge, "overall_judge_pass"),
        "llm_judge_semantic_pass": ratio_count(judge, "semantic_answer_correct"),
        "expected_evidence_cited": ratio_count(deterministic, "expected_evidence_cited"),
        "valid_time_used_correct": ratio_count(judge, "valid_time_correct"),
        "evidence_available_after_injection_count": available_count,
        "pre_injection_any_expected_evidence_count": pre_any_count,
        "pre_injection_all_expected_evidence_count": pre_all_count,
        "notes": "Prior L2B complete-evidence answer setting; not rerun.",
    }
    return [pre_row, post_row]


def table3_columns() -> list[tuple[str, str]]:
    return [
        ("method", "Method"),
        ("cases", "Cases"),
        ("retrieval_hit_at_1", "Retrieval Hit@1"),
        ("retrieval_hit_at_5", "Retrieval Hit@5"),
        ("retrieval_mrr_at_5", "Retrieval MRR@5"),
        ("strict_combined_pass", "Strict Combined Pass"),
        ("deterministic_hard_contract_pass", "Deterministic Hard-Contract Pass"),
        ("llm_judge_overall_pass", "LLM Judge Overall Pass"),
        ("llm_judge_semantic_pass", "LLM Judge Semantic Pass"),
        ("valid_time_used_correct", "Valid Time Used Correct"),
        ("expected_evidence_cited", "Expected Evidence Cited"),
        ("provider_errors", "Provider Errors"),
        ("judge_errors", "Judge Errors"),
    ]


def write_outputs(
    meta: dict[str, Any],
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    notes: list[str],
    *,
    count_denominator: int | None = None,
) -> dict[str, Any]:
    table_id = meta["table_id"]
    md_path = PAPER_DIR / f"{table_id}.md"
    csv_path = PAPER_DIR / f"{table_id}.csv"
    json_path = TABLE_DIR / f"{table_id}.json"
    write_markdown(md_path, meta["title"], rows, columns, notes, count_denominator=count_denominator)
    write_csv(csv_path, rows, columns)
    write_json(
        json_path,
        {
            "metadata": meta,
            "columns": [{"key": key, "label": label} for key, label in columns],
            "rows": rows,
            "notes": notes,
        },
    )
    return {
        "id": table_id,
        "title": meta["title"],
        "markdown_path": str(md_path),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "rows": rows,
        "notes": notes,
    }


def write_markdown(
    path: Path,
    title: str,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    notes: list[str],
    *,
    count_denominator: int | None,
) -> None:
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(label for _, label in columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        cells = [format_markdown_cell(row.get(key), key, row, count_denominator) for key, _ in columns]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "Notes:"])
    lines.extend(f"- {note}" for note in notes)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    fieldnames = [key for key, _ in columns]
    extra_fields = sorted({key for row in rows for key in row if key not in fieldnames})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*fieldnames, *extra_fields], lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_index(generated: list[dict[str, Any]]) -> None:
    lines = [
        "# ChronoRAG Paper Tables Index",
        "",
        "Generated from existing result artifacts only. No retrieval, model, validator, or judge runs were executed by this table builder.",
        "",
        "Use these tables as the paper-ready result boundary for Layer 2A retrieval, Layer 2A ablations, QA50 standard retrieval + LLM post-filtering, and QA50 answer-level comparison.",
        "",
    ]
    for index, item in enumerate(generated, start=1):
        md_name = Path(item["markdown_path"]).name
        csv_name = Path(item["csv_path"]).name
        json_name = Path(item["json_path"]).name
        lines.append(f"{index}. [{item['title']}]({md_name})")
        lines.append(f"   - CSV: `{csv_name}`")
        lines.append(f"   - JSON: `chronorag/stdcomp/results/paper_tables/{json_name}`")
    lines.append("")
    (PAPER_DIR / "chrono_tables_index.md").write_text("\n".join(lines), encoding="utf-8")


def base_meta(table_id: str, title: str, sources: list[Path]) -> dict[str, Any]:
    return {
        "table_id": table_id,
        "title": title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {
                "path": str(path),
                "exists": path.exists(),
                "sha256": sha256(path) if path.exists() else None,
            }
            for path in sources
        ],
        "rerun_performed": False,
    }


def ratio_count(rows: list[dict[str, Any]], key: str) -> float | None:
    if not rows:
        return None
    values = [row.get(key) for row in rows if isinstance(row.get(key), bool)]
    if not values:
        return None
    return sum(1 for value in values if value) / len(rows)


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def format_markdown_cell(value: Any, key: str, row: dict[str, Any], count_denominator: int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if count_denominator and 0.0 <= value <= 1.0 and key != "retrieval_mrr_at_5":
            count = round(value * count_denominator)
            return f"{value:.4f} ({count}/{count_denominator})"
        return f"{value:.4f}"
    return str(value)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Required source artifact is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Required source artifact is missing: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
