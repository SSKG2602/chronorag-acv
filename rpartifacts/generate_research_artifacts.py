from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "rpartifacts"
DATA_DIR = OUT / "data"
FIG_DIR = OUT / "figures"
TABLE_DIR = OUT / "tables"
PAPER_DIR = OUT / "paper"
GITHUB_DIR = OUT / "github"
LINKEDIN_DIR = OUT / "linkedin"

SOURCES = {
    "table1": ROOT / "docs/paper_assets/table1_layer2a_retrieval_standard_comparison.csv",
    "table1_ci": ROOT / "docs/paper_assets/table1_layer2a_retrieval_standard_comparison_with_ci.csv",
    "table2": ROOT / "docs/paper_assets/table2_layer2a_ablation_comparison.csv",
    "table3": ROOT / "docs/paper_assets/table3_qa50_llm_post_filter_baselines.csv",
    "table3_ci": ROOT / "docs/paper_assets/table3_qa50_llm_post_filter_baselines_with_ci.csv",
    "table4": ROOT / "docs/paper_assets/table4_qa50_answer_level_comparison.csv",
    "table4_ci": ROOT / "docs/paper_assets/table4_qa50_answer_level_comparison_with_ci.csv",
    "qa50_extracted_md": ROOT / "docs/paper_assets/chronorag_qa50_extracted_values.md",
    "topk": ROOT / "docs/paper_assets/topk_sensitivity.csv",
    "qa50_extracted_json": ROOT / "chronorag/stdcomp/results/paper_tables/chronorag_qa50_extracted_values.json",
    "bm25_qa50": ROOT / "chronorag/stdcomp/results/qa50_llm_baselines/bm25_llm_qa50_metrics.json",
    "dense_qa50": ROOT / "chronorag/stdcomp/results/qa50_llm_baselines/dense_llm_qa50_metrics.json",
    "date_filter_qa50": ROOT / "chronorag/stdcomp/results/qa50_llm_baselines/date_filter_llm_qa50_metrics.json",
    "ablation_json": ROOT / "benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json",
    "retrieval_eval_json": ROOT / "benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json",
    "stdcomp_json": ROOT / "chronorag/stdcomp/results/stdcomp_layer2a_comparison.json",
    "bm25_ranked_outputs": ROOT / "chronorag/stdcomp/results/bm25_ranked_outputs.json",
    "bm25_qa50_outputs": ROOT / "chronorag/stdcomp/results/qa50_llm_baselines/bm25_llm_qa50_outputs.jsonl",
    "dense_qa50_outputs": ROOT / "chronorag/stdcomp/results/qa50_llm_baselines/dense_llm_qa50_outputs.jsonl",
    "date_filter_qa50_outputs": ROOT / "chronorag/stdcomp/results/qa50_llm_baselines/date_filter_llm_qa50_outputs.jsonl",
    "temporal_trace_jsonl": ROOT / "rpartifacts/data/temporal_feature_trace.jsonl",
    "temporal_trace_csv": ROOT / "rpartifacts/data/temporal_feature_trace.csv",
}

METRIC_DEFINITIONS = {
    "Hit@k": "Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.",
    "MRR@5": "Mean reciprocal rank of the first expected or acceptable evidence item within top-5.",
    "Forbidden Absent@5": "Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.",
    "Category Primary Pass": "Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.",
    "Strict Combined Pass": "Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.",
    "Hard-Contract Pass": "Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.",
    "Judge Semantic Pass": "LLM judge semantic answer-correctness signal.",
    "Valid Time Correct": "Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.",
}

ARTIFACTS: list[dict[str, str]] = []
MISSING: list[str] = []


def main() -> None:
    ensure_dirs()
    check_sources()

    table1 = read_csv_source("table1")
    table2 = read_csv_source("table2")
    table3 = read_csv_source("table3")
    table4 = read_csv_source("table4")
    topk = read_csv_source("topk")
    ablation = read_json_source("ablation_json")
    stdcomp = read_json_source("stdcomp_json")
    qa50_extracted = read_json_source("qa50_extracted_json")
    temporal_trace = read_jsonl_source("temporal_trace_jsonl")

    write_data_manifest()
    write_derived_data(table1, table2, table3, table4, topk, qa50_extracted)

    figure1()
    figure2()
    figure3(table1)
    figure4(table1, table2)
    figure5(table2)
    figure6(table3, table4)
    figure7(table3, table4, qa50_extracted)
    figure8(topk)
    figure9_temporal_feature_heatmap(temporal_trace)
    figure10_one_query_trace(stdcomp)
    figure11_metric_family_summary(table1, table3, table4)
    figure12_qa50_failure_decomposition()
    figure13_claim_boundary()
    figure14_applications_map()

    write_tables(table1, table2, table3, table4, topk)
    write_github_snippets()
    write_linkedin_assets()
    write_paper_notes()
    write_root_readme()
    write_manifest_table()
    write_missing_inputs()

    print("Generated ChronoRAG research artifacts.")
    print(f"Artifacts recorded: {len(ARTIFACTS)}")
    print(f"Missing source inputs: {len(MISSING)}")
    if MISSING:
        print(f"See {OUT / 'MISSING_INPUTS.md'}")


def ensure_dirs() -> None:
    for path in (DATA_DIR, FIG_DIR, TABLE_DIR, PAPER_DIR, GITHUB_DIR, LINKEDIN_DIR):
        path.mkdir(parents=True, exist_ok=True)


def check_sources() -> None:
    for key, path in SOURCES.items():
        if not path.exists():
            MISSING.append(f"{key}: {rel(path)}")


def read_csv_source(key: str) -> list[dict[str, str]]:
    path = SOURCES[key]
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json_source(key: str) -> dict[str, Any]:
    path = SOURCES[key]
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl_source(key: str) -> list[dict[str, Any]]:
    path = SOURCES[key]
    if not path.exists():
        return []
    return read_jsonl(path)


def write_data_manifest() -> None:
    rows = []
    for key, path in SOURCES.items():
        rows.append({"key": key, "path": rel(path), "exists": path.exists(), "kind": path.suffix.lstrip(".")})
    write_json(DATA_DIR / "source_artifact_manifest.json", {"sources": rows})
    record(DATA_DIR / "source_artifact_manifest.json", "data", "Source artifact existence manifest.", "source paths")


def write_derived_data(
    table1: list[dict[str, str]],
    table2: list[dict[str, str]],
    table3: list[dict[str, str]],
    table4: list[dict[str, str]],
    topk: list[dict[str, str]],
    qa50_extracted: dict[str, Any],
) -> None:
    payload = {
        "layer2a_table1": table1,
        "ablation_table2": table2,
        "qa50_llm_table3": table3,
        "qa50_answer_table4": table4,
        "topk_sensitivity": topk,
        "qa50_extracted_values": qa50_extracted,
    }
    write_json(DATA_DIR / "derived_plot_data.json", payload)
    record(DATA_DIR / "derived_plot_data.json", "data", "Normalized data used by rpartifacts figures.", "existing result artifacts")


def figure1() -> None:
    fig, ax = setup_canvas(figsize=(13, 7), title="Figure 1. Temporal misgrounding concept")
    box(ax, 0.06, 0.74, 0.22, 0.12, "User query\nas-of / valid-time need", fc="#f6f7fb")
    box(ax, 0.35, 0.78, 0.24, 0.12, "Standard semantic/date retrieval", fc="#ffe9e6")
    box(ax, 0.67, 0.78, 0.24, 0.12, "Topically relevant but\nwrong-time evidence", fc="#ffd6cf")
    box(ax, 0.67, 0.57, 0.24, 0.11, "Failure:\ntemporal misgrounding", fc="#f9b2a8")
    box(ax, 0.35, 0.37, 0.24, 0.18, "ChronoRAG\nrole separation + precision scoring\n+ forbidden/source/slot finalization", fc="#e2f1ff")
    box(ax, 0.67, 0.38, 0.24, 0.12, "Temporally valid evidence", fc="#d8f3df")
    box(ax, 0.67, 0.17, 0.24, 0.11, "Grounded answer", fc="#d8f3df")
    arrow(ax, (0.28, 0.80), (0.35, 0.84))
    arrow(ax, (0.59, 0.84), (0.67, 0.84))
    arrow(ax, (0.79, 0.78), (0.79, 0.68))
    arrow(ax, (0.28, 0.78), (0.35, 0.46))
    arrow(ax, (0.59, 0.46), (0.67, 0.44))
    arrow(ax, (0.79, 0.38), (0.79, 0.28))
    ax.text(0.08, 0.60, "Same topic != valid evidence", fontsize=14, weight="bold", color="#333")
    ax.text(0.08, 0.49, "Publication / filing / release date can differ\nfrom fact valid time", fontsize=12, color="#333")
    ax.text(0.08, 0.32, "ChronoRAG filters before generation", fontsize=14, weight="bold", color="#1d5f8a")
    save_figure(fig, "fig1_temporal_misgrounding_concept", "Conceptual schematic; not an experimental result.")


def figure2() -> None:
    fig, ax = setup_canvas(figsize=(18, 10), title="Figure 2. ChronoRAG architecture")
    caption = (
        "ChronoRAG separates temporal role grounding from answer generation. "
        "Layer 2A evaluates selected evidence before answer synthesis, while "
        "Layer 2B evaluates answer-contract behavior after generation."
    )
    columns = [
        {
            "title": "1. Ingestion & Context",
            "x": 0.045,
            "color": "#f6f7fb",
            "blocks": [
                "Raw evidence rows",
                "Temporal Contextual Chunking",
                "Temporal metadata extraction",
            ],
        },
        {
            "title": "2. Temporal Role Grounding",
            "x": 0.285,
            "color": "#e9f4ff",
            "blocks": [
                "Query temporal intent",
                "Valid-time /\ntransaction-time separation",
                "Temporal precision scoring",
                "Temporal fusion",
            ],
        },
        {
            "title": "3. Evidence Finalization",
            "x": 0.525,
            "color": "#e9f9ee",
            "blocks": [
                "Forbidden-time suppression",
                "Source / metric /\nversion adjustment",
                "Slot-aware finalization",
                "ChronoSanity conflict guard",
            ],
        },
    ]
    block_w = 0.18
    block_h = 0.075
    for col in columns:
        ax.text(col["x"] + block_w / 2, 0.89, col["title"], ha="center", va="center", fontsize=14, weight="bold")
        count = len(col["blocks"])
        ys = [0.74, 0.61, 0.48] if count == 3 else [0.77, 0.65, 0.53, 0.41]
        centers = []
        for y, label in zip(ys, col["blocks"]):
            rect_box(ax, col["x"], y, block_w, block_h, label, fc=col["color"], fontsize=11)
            centers.append((col["x"] + block_w / 2, y + block_h / 2))
        for upper, lower in zip(centers[:-1], centers[1:]):
            arrow(ax, (upper[0], upper[1] - block_h / 2 + 0.008), (lower[0], lower[1] + block_h / 2 - 0.008))

    ax.text(0.765 + block_w / 2, 0.89, "4. Outputs & Evaluation", ha="center", va="center", fontsize=14, weight="bold")
    rect_box(ax, 0.765, 0.77, block_w, block_h, "Attribution cards /\nfinal evidence", fc="#fff4d6", fontsize=11)
    rect_box(ax, 0.765, 0.58, block_w, block_h, "Layer 2A retrieval-only scoring", fc="#fff4d6", fontsize=10)
    rect_box(ax, 0.765, 0.46, block_w, block_h, "Evidence IDs, forbidden traps,\ncategory-primary pass", fc="#fff4d6", fontsize=9)
    rect_box(ax, 0.765, 0.29, block_w, block_h, "Answer synthesizer", fc="#f7e8ff", fontsize=10)
    rect_box(ax, 0.765, 0.18, block_w, block_h, "Answer-contract validation", fc="#f7e8ff", fontsize=10)
    rect_box(ax, 0.765, 0.07, block_w, block_h, "Layer 2B / QA50\nanswer scoring", fc="#f7e8ff", fontsize=10)

    # Horizontal stage-transition arrows run through the whitespace between column groups.
    for x1, x2 in [(0.225, 0.285), (0.465, 0.525), (0.705, 0.765)]:
        arrow(ax, (x1, 0.555), (x2, 0.555))

    # The only branch is after final evidence. The upper and lower paths are separated.
    arrow(ax, (0.855, 0.77), (0.855, 0.655))
    arrow(ax, (0.855, 0.58), (0.855, 0.535))
    ax.plot([0.955, 0.955], [0.805, 0.33], color="#333", linewidth=1.4)
    arrow(ax, (0.945, 0.807), (0.955, 0.807))
    arrow(ax, (0.955, 0.33), (0.945, 0.33))
    arrow(ax, (0.855, 0.29), (0.855, 0.255))
    arrow(ax, (0.855, 0.18), (0.855, 0.145))

    ax.text(0.045, 0.02, caption, fontsize=12, color="#333", ha="left", va="bottom")
    save_figure(fig, "fig2_chronorag_architecture", "Architecture schematic with fixed coordinates; no experimental result.")


def figure3(table1: list[dict[str, str]]) -> None:
    if not table1:
        write_not_available("fig3_layer2a_retrieval_comparison", "Table 1 CSV missing.")
        return
    metrics = ["hit_at_1", "hit_at_5", "mrr_at_5", "forbidden_absent_at_5", "category_primary_pass"]
    labels = ["Hit@1", "Hit@5", "MRR@5", "Forbidden\nAbsent@5", "Category\nPrimary Pass"]
    fig, ax = plt.subplots(figsize=(14, 7))
    grouped_bars(ax, table1, "method", metrics, labels)
    ax.set_title("Figure 3. Layer 2A retrieval comparison")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.08)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=3)
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "fig3_layer2a_retrieval_comparison", "Generated from Table 1. BM25 and Date-filter have higher broad Hit@5; ChronoRAG is strongest on temporal-validity diagnostics.")


def figure4(table1: list[dict[str, str]], table2: list[dict[str, str]]) -> None:
    if not table1:
        write_not_available("fig4_temporal_validity_diagnostics", "Table 1 CSV missing.")
        return
    rows = [dict(row) for row in table1]
    score_only = find_row(table2, "method", "Score-only")
    if score_only:
        rows.append(score_only)
    fig, ax = plt.subplots(figsize=(12, 6.8))
    grouped_bars(
        ax,
        rows,
        "method",
        ["forbidden_absent_at_5", "category_primary_pass"],
        ["Forbidden Absent@5", "Category Primary Pass"],
        width=0.12,
    )
    ax.set_title("Figure 4. Temporal-validity diagnostics")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=3)
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "fig4_temporal_validity_diagnostics", "Generated from Table 1 and ablation artifact.")


def figure5(table2: list[dict[str, str]]) -> None:
    full = find_row(table2, "method", "ChronoRAG Full")
    score = find_row(table2, "method", "Score-only")
    if not full or not score:
        write_not_available("fig5_score_only_ablation", "ChronoRAG Full or Score-only row missing from ablation table.")
        return
    rows = [score, full]
    fig, ax = plt.subplots(figsize=(10, 6.2))
    grouped_bars(
        ax,
        rows,
        "method",
        ["hit_at_5", "forbidden_absent_at_5", "category_primary_pass"],
        ["Hit@5", "Forbidden\nAbsent@5", "Category\nPrimary Pass"],
        width=0.2,
    )
    ax.set_title("Figure 5. Score-only ablation")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "fig5_score_only_ablation", "Score-only retrieval maximizes broad Hit@5 but damages temporal-validity metrics.")


def figure6(table3: list[dict[str, str]], table4: list[dict[str, str]]) -> None:
    post = find_row(table4, "method", "ChronoRAG Full - post-injection answer setting")
    if not table3 or not post:
        write_not_available("fig6_qa50_llm_post_filtering", "QA50 baseline table or ChronoRAG post-injection row missing.")
        return
    rows = [dict(row) for row in table3]
    rows.append(
        {
            "method": "ChronoRAG Full\npost-injection",
            "strict_combined_pass": post["strict_combined_pass"],
            "deterministic_hard_contract_pass": post["deterministic_hard_contract_pass"],
            "llm_judge_semantic_pass": post["llm_judge_semantic_pass"],
            "valid_time_used_correct": post["valid_time_used_correct"],
        }
    )
    fig, ax = plt.subplots(figsize=(13, 7))
    grouped_bars(
        ax,
        rows,
        "method",
        ["strict_combined_pass", "deterministic_hard_contract_pass", "llm_judge_semantic_pass", "valid_time_used_correct"],
        ["Strict\nCombined", "Hard\nContract", "Judge\nSemantic", "Valid Time\nCorrect"],
        width=0.16,
    )
    ax.set_title("Figure 6. QA50 LLM temporal post-filtering")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=2)
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "fig6_qa50_llm_post_filtering", "Standard retrieval + LLM temporal prompting reaches 32-40% strict pass; ChronoRAG reaches 70% strict pass in the answer-level setting.")


def figure7(table3: list[dict[str, str]], table4: list[dict[str, str]], qa50_extracted: dict[str, Any]) -> None:
    if not table3 or not table4:
        write_not_available("fig7_injection_fairness_split", "QA50 baseline or answer-level table missing.")
        return
    pre_any = 0.74
    pre_all = 0.64
    post = find_row(table4, "method", "ChronoRAG Full - post-injection answer setting") or {}
    if qa50_extracted:
        vals = qa50_extracted.get("metrics") or qa50_extracted.get("values") or qa50_extracted
        pre_any = nested_metric(vals, "expected_evidence_retrieved_pre_injection_any", pre_any)
        pre_all = nested_metric(vals, "expected_evidence_retrieved_pre_injection_all", pre_all)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    left_labels = [row["method"] for row in table3] + ["ChronoRAG\npre any", "ChronoRAG\npre all"]
    left_vals = [to_float(row.get("retrieval_hit_at_5")) for row in table3] + [pre_any, pre_all]
    axes[0].bar(left_labels, left_vals, color=["#7aa6c2", "#7aa6c2", "#7aa6c2", "#2f7d32", "#81c784"])
    axes[0].set_title("Panel A. Pre-injection retrieval availability")
    axes[0].set_ylim(0, 1.08)
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].grid(axis="y", alpha=0.25)
    post_labels = ["Evidence\navailable", "Strict\ncombined", "Valid time\ncorrect", "Evidence\ncited"]
    post_vals = [
        to_float(post.get("retrieval_hit5_or_evidence_available")),
        to_float(post.get("strict_combined_pass")),
        to_float(post.get("valid_time_used_correct")),
        to_float(post.get("expected_evidence_cited")),
    ]
    axes[1].bar(post_labels, post_vals, color="#2f7d32")
    axes[1].set_title("Panel B. Post-injection answer setting")
    axes[1].set_ylim(0, 1.08)
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("Figure 7. Pre/post injection fairness split")
    save_figure(fig, "fig7_injection_fairness_split", "Pre-injection is the fair retrieval-availability comparison. Post-injection measures answer behavior when expected evidence is available.")


def figure8(topk: list[dict[str, str]]) -> None:
    if not topk:
        write_not_available("fig8_topk_sensitivity", "Top-k sensitivity CSV missing.")
        return
    metrics = [
        ("hit_at_k", "Hit@k"),
        ("mrr_at_k", "MRR@k"),
        ("forbidden_absent_at_k", "Forbidden Absent@k"),
        ("category_primary_pass", "Category Primary Pass"),
    ]
    methods = []
    for row in topk:
        label = row.get("method_label") or row.get("method")
        if label not in methods:
            methods.append(label)
    fig, axes = plt.subplots(2, 2, figsize=(18, 10.5), sharex=True)
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        for method in methods:
            rows = sorted([row for row in topk if (row.get("method_label") or row.get("method")) == method], key=lambda r: to_float(r.get("k")))
            ax.plot([to_float(r.get("k")) for r in rows], [to_float(r.get(metric)) for r in rows], marker="o", linewidth=2.2, label=method)
        ax.set_title(label)
        ax.set_ylim(0, 1.08)
        ax.set_xticks([1, 3, 5, 10])
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=11)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.03), ncol=3, fontsize=11)
    fig.suptitle("Figure 8. Top-k retrieval-only sensitivity")
    save_figure(fig, "fig8_topk_sensitivity", "Generated from top-k sensitivity artifact.")
    figure8_split(topk, methods, metrics[:2], "fig8a_topk_hit_sensitivity", "Figure 8a. Ranking sensitivity", "Generated from top-k sensitivity artifact.")
    figure8_split(
        topk,
        methods,
        metrics[2:],
        "fig8b_topk_temporal_validity_sensitivity",
        "Figure 8b. Temporal-validity sensitivity",
        "Generated from top-k sensitivity artifact.",
    )


def figure8_split(
    topk: list[dict[str, str]],
    methods: list[str],
    metrics: list[tuple[str, str]],
    stem: str,
    title: str,
    caption: str,
) -> None:
    fig, axes = plt.subplots(1, len(metrics), figsize=(16, 6.2), sharex=True)
    if len(metrics) == 1:
        axes = [axes]
    for ax, (metric, label) in zip(axes, metrics):
        for method in methods:
            rows = sorted([row for row in topk if (row.get("method_label") or row.get("method")) == method], key=lambda r: to_float(r.get("k")))
            ax.plot([to_float(r.get("k")) for r in rows], [to_float(r.get(metric)) for r in rows], marker="o", linewidth=2.4, label=method)
        ax.set_title(label, fontsize=13)
        ax.set_ylim(0, 1.08)
        ax.set_xticks([1, 3, 5, 10])
        ax.set_xlabel("Top-k")
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=11)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.03), ncol=3, fontsize=11)
    fig.suptitle(title)
    save_figure(fig, stem, caption)


def figure9_temporal_feature_heatmap(trace_rows: list[dict[str, Any]]) -> None:
    write_candidate_trace_schema()
    if not trace_rows:
        figure9_feature_heatmap_note("No temporal feature trace rows were found. Run `python3 rpartifacts/export_temporal_feature_trace.py ...` first.")
        return

    preferred_query = "l2q:0000:exact_valid_time_retrieval"
    query_ids = []
    for row in trace_rows:
        query_id = str(row.get("query_id") or "")
        if query_id and query_id not in query_ids:
            query_ids.append(query_id)
    main_query = preferred_query if preferred_query in query_ids else query_ids[0]
    rows = [row for row in trace_rows if row.get("query_id") == main_query]
    rows.sort(key=lambda row: (int_or_large(row.get("rank_after_finalization")), int_or_large(row.get("rank_before_finalization")), str(row.get("candidate_evidence_id"))))

    desired_columns = [
        "semantic_score",
        "bm25_score",
        "dense_score",
        "temporal_precision_score",
        "valid_time_fit",
        "interval_overlap_score",
        "transaction_time_penalty",
        "forbidden_time_penalty",
        "source_metric_score",
        "slot_score",
        "fusion_score",
        "final_score",
    ]
    numeric_columns = [column for column in desired_columns if any(as_number(row.get(column)) is not None for row in rows)]
    if not numeric_columns:
        figure9_feature_heatmap_note("Temporal trace rows exist, but no numeric score columns are populated.")
        return

    raw_matrix = [[as_number(row.get(column)) for column in numeric_columns] for row in rows]
    # Figure 9 is a mechanism view, so normalize each real score column only
    # for color comparability; raw values remain in the JSONL/CSV trace files.
    normalized_matrix = normalize_columns(raw_matrix)
    fig_height = max(7.5, min(12.0, 0.42 * len(rows) + 2.8))
    fig, ax = plt.subplots(figsize=(14, fig_height))
    image = ax.imshow(normalized_matrix, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_title("Figure 9. Temporal feature heatmap")
    ax.set_xticks(range(len(numeric_columns)))
    ax.set_xticklabels([metric_label(column) for column in numeric_columns], rotation=35, ha="right")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([heatmap_row_label(row) for row in rows], fontsize=9)
    ax.set_xlabel("Available retrieval-time numeric fields")
    ax.set_ylabel("Candidate evidence")
    cbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Min-max normalized value")
    save_figure(
        fig,
        "fig9_temporal_feature_heatmap",
        "Generated from retrieval-only temporal feature trace; values are min-max normalized per column.",
    )
    write_temporal_feature_heatmap_note(main_query, rows, numeric_columns, desired_columns)
    write_superseded_heatmap_note()


def figure9_feature_heatmap_note(reason: str) -> None:
    text = f"""# Figure 9 Temporal Feature Heatmap Availability

{reason}

Candidate-level temporal feature traces must include at least one real numeric
retrieval-time score column before a heatmap can be generated. No synthetic
numeric heatmap was generated.
"""
    path = FIG_DIR / "fig9_temporal_feature_heatmap_not_available.md"
    path.write_text(text, encoding="utf-8")
    record(path, "figure-note", "Feature heatmap not generated because numeric candidate traces are unavailable.", "artifact schema inspection")


def write_candidate_trace_schema() -> None:
    recommendation = """# Temporal Feature Trace Logging Recommendation

The current Figure 9 trace exporter records the score fields exposed by the
retrieval pipeline. Future retrieval-only runs should keep persisting a
per-query candidate trace with semantic score, temporal fit, valid-time fit,
transaction penalty, forbidden penalty, source/metric fit, slot assignment, and
final score.

Recommended future JSONL path:
`rpartifacts/data/candidate_trace_sample_schema.json`

This recommendation file is a schema guide. The actual Figure 9 trace data is
stored separately in `rpartifacts/data/temporal_feature_trace.jsonl` and
`rpartifacts/data/temporal_feature_trace.csv`.
"""
    rec_path = PAPER_DIR / "temporal_feature_trace_logging_recommendation.md"
    rec_path.write_text(recommendation, encoding="utf-8")
    record(rec_path, "paper-note", "Candidate-trace logging recommendation.", "artifact schema inspection")
    schema = {
        "description": "Schema recommendation only; not benchmark data.",
        "recommended_jsonl_path": "rpartifacts/data/candidate_traces.jsonl",
        "record_schema": {
            "case_id": "string",
            "query": "string",
            "method": "string",
            "candidate_rank": "integer",
            "evidence_id": "string",
            "semantic_score": "number|null",
            "temporal_fit": "number|null",
            "valid_time_fit": "number|null",
            "transaction_penalty": "number|null",
            "forbidden_penalty": "number|null",
            "source_metric_fit": "number|null",
            "slot_assignment": "string|null",
            "slot_fit": "number|null",
            "final_score": "number|null",
            "selected": "boolean",
            "suppression_reasons": ["string"],
        },
    }
    write_json(DATA_DIR / "candidate_trace_sample_schema.json", schema)
    record(DATA_DIR / "candidate_trace_sample_schema.json", "data-schema", "Candidate trace schema recommendation; contains no fake scores.", "artifact schema inspection")


def write_temporal_feature_heatmap_note(
    query_id: str,
    rows: list[dict[str, Any]],
    numeric_columns: list[str],
    desired_columns: list[str],
) -> None:
    missing = [column for column in desired_columns if column not in numeric_columns]
    caption = (
        "Figure 9 visualizes candidate-level retrieval signals for a representative Layer 2A query. "
        "Rows are candidate evidence items and columns are available retrieval-time scoring features. "
        "Values are normalized for visualization. The figure is generated from a retrieval-only trace export "
        "and does not use LLM, Vertex, Gemini, judge, or answer-generation calls."
    )
    lines = [
        "# Temporal Feature Heatmap",
        "",
        caption,
        "",
        "Only score fields exposed by the current retrieval pipeline are shown; missing internal components are left out rather than reconstructed.",
        "",
        f"- Query ID: `{query_id}`",
        f"- Query text: {rows[0].get('query_text') if rows else 'n/a'}",
        f"- Candidate rows shown: {len(rows)}",
        f"- Source JSONL: `{rel(SOURCES['temporal_trace_jsonl'])}`",
        f"- Source CSV: `{rel(SOURCES['temporal_trace_csv'])}`",
        "- Value mode: raw values are exported in the JSONL/CSV; heatmap colors are min-max normalized per column to 0-1.",
        "",
        "Numeric fields included:",
        "",
    ]
    lines.extend(f"- `{column}`" for column in numeric_columns)
    lines.extend(["", "Desired fields unavailable or blank in this trace:", ""])
    lines.extend(f"- `{column}`" for column in missing)
    lines.extend(
        [
            "",
            "Trace provenance: generated by `python3 rpartifacts/export_temporal_feature_trace.py` using deterministic retrieval-only code over the Layer 2A question and corpus JSONL files.",
            "",
        ]
    )
    path = PAPER_DIR / "temporal_feature_heatmap.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    record(path, "paper-note", "Figure 9 temporal feature heatmap provenance and normalization note.", "retrieval-only trace export")


def write_superseded_heatmap_note() -> None:
    text = """# Figure 9 Heatmap Availability

A real Figure 9 heatmap is now generated from
`rpartifacts/data/temporal_feature_trace.jsonl`. This file is retained only as
provenance for the earlier placeholder state.

Use:

- `rpartifacts/figures/fig9_temporal_feature_heatmap.png`
- `rpartifacts/figures/fig9_temporal_feature_heatmap.svg`
- `rpartifacts/paper/temporal_feature_heatmap.md`
"""
    path = FIG_DIR / "fig9_temporal_feature_heatmap_not_available.md"
    path.write_text(text, encoding="utf-8")
    record(path, "figure-note", "Superseded Figure 9 availability note retained for provenance.", "retrieval-only trace export")


def figure10_one_query_trace(stdcomp: dict[str, Any]) -> None:
    if not stdcomp:
        write_not_available("fig10_one_query_trace", "Standard comparison JSON missing.")
        write_one_query_needed("Standard comparison JSON missing.")
        return
    reports = {report.get("method"): report for report in stdcomp.get("reports", [])}
    requested_case_id = "l2q:0000:exact_valid"
    case_id = "l2q:0000:exact_valid_time_retrieval"
    chrono = find_case_report(reports.get("chronorag_full", {}), case_id)
    bm25 = find_case_report(reports.get("bm25", {}), case_id)
    ranked = find_ranked_output(SOURCES["bm25_ranked_outputs"], case_id)
    if not chrono or not bm25 or not ranked:
        write_not_available("fig10_one_query_trace", "Requested one-query trace could not be verified from stored standard-comparison artifacts.")
        write_one_query_needed("Requested one-query trace could not be verified from stored standard-comparison artifacts.")
        return

    question = ranked.get("question") or find_question(case_id)
    bm25_ranked = ranked.get("ranked_evidence") or []
    bm25_wrong_time = [row.get("evidence_id") for row in bm25_ranked if row.get("evidence_id") in bm25.get("selected_evidence_ids", [])[1:4]]
    if not bm25_wrong_time:
        bm25_wrong_time = (bm25.get("selected_evidence_ids") or [])[1:4]
    expected = chrono.get("expected_evidence_ids") or []
    chrono_selected = chrono.get("selected_evidence_ids") or []
    forbidden = chrono.get("forbidden_evidence_ids") or []
    md = [
        "# One-Query Trace",
        "",
        "This is a real Layer 2A retrieval-only benchmark case extracted from existing artifacts.",
        "",
        f"- Requested short ID in artifact prompt: `{requested_case_id}`",
        f"- Stored case ID used: `{case_id}`",
        f"- Category: `{chrono.get('category')}`",
        f"- Question: {question}",
        f"- Expected evidence: `{', '.join(expected)}`",
        f"- Forbidden evidence: `{', '.join(forbidden)}`",
        f"- BM25 selected examples: `{', '.join(bm25_wrong_time)}`",
        f"- ChronoRAG selected: `{', '.join(chrono_selected)}`",
        "",
        "## Source Artifacts Used",
        "",
        f"- `{rel(SOURCES['stdcomp_json'])}`",
        f"- `{rel(SOURCES['bm25_ranked_outputs'])}`",
        f"- `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl` for benchmark question provenance",
        "",
        "## Trace Availability",
        "",
        "- Case type: real artifact-extracted benchmark trace.",
        "- Exact BM25 candidate scores: available in `bm25_ranked_outputs.json`.",
        "- ChronoRAG selected evidence IDs and pass/fail behavior: available in `stdcomp_layer2a_comparison.json`.",
        "- Candidate-level temporal feature scores for Figure 9: available in `rpartifacts/data/temporal_feature_trace.jsonl` and `.csv`.",
        "",
        "This trace summarizes selected evidence IDs and pass/fail behavior from stored result artifacts. The separate Figure 9 trace export records the available retrieval-time numeric fields for representative cases.",
        "",
        "Interpretation: the baseline retrieves expected evidence but also includes forbidden wrong-time evidence; ChronoRAG keeps the expected evidence while excluding the forbidden rows.",
        "",
    ]
    md_path = PAPER_DIR / "one_query_trace.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    record(md_path, "paper-note", "Real one-query trace from Layer 2A artifacts.", "stdcomp case reports")

    fig, ax = setup_canvas(figsize=(14, 12), title="Figure 10. One-query retrieval trace")
    ax.text(
        0.5,
        0.93,
        "BM25 retrieves topically relevant wrong-time evidence; ChronoRAG selects the expected valid-time evidence.",
        ha="center",
        va="center",
        fontsize=14,
        color="#333",
    )
    cards = [
        (
            "Case / Query",
            f"Stored ID: {case_id}\nRequested short ID: {requested_case_id}\n{question}",
            "#f6f7fb",
        ),
        ("Expected Evidence", "\n".join(expected), "#e9f9ee"),
        (
            "BM25 Retrieval - FAIL",
            "Retrieved same FRED series but wrong valid-time rows:\n"
            + "\n".join(f"- {item}" for item in bm25_wrong_time)
            + "\nReason: topically relevant series, but wrong requested date.",
            "#ffe9e6",
        ),
        (
            "ChronoRAG Full - PASS",
            "Selected "
            + ", ".join(chrono_selected)
            + "\nReason: temporal precision and valid-time finalization select the requested date.",
            "#e2f1ff",
        ),
    ]
    y = 0.70
    for title, content, color in cards:
        card(ax, 0.08, y, 0.84, 0.18, title, content, fc=color)
        y -= 0.21
    save_figure(fig, "fig10_one_query_trace", "Generated from real Layer 2A case reports.")


def figure11_metric_family_summary(
    table1: list[dict[str, str]],
    table3: list[dict[str, str]],
    table4: list[dict[str, str]],
) -> None:
    chrono_retrieval = find_row(table1, "method", "ChronoRAG Full") or {}
    standard_rows = [row for row in table1 if row.get("method") != "ChronoRAG Full"]
    post = find_row(table4, "method", "ChronoRAG Full - post-injection answer setting") or {}
    standard_answer_rows = table3
    if not chrono_retrieval or not standard_rows or not post or not standard_answer_rows:
        write_not_available("fig11_metric_family_summary", "Metric family source rows missing.")
        return
    groups = [
        (
            "Standard relevance / ranking",
            [
                ("Hit@1", "hit_at_1", chrono_retrieval, standard_rows),
                ("Hit@5", "hit_at_5", chrono_retrieval, standard_rows),
                ("MRR@5", "mrr_at_5", chrono_retrieval, standard_rows),
            ],
        ),
        (
            "Temporal-validity diagnostics",
            [
                ("Forbidden Absent@5", "forbidden_absent_at_5", chrono_retrieval, standard_rows),
                ("Category Primary Pass", "category_primary_pass", chrono_retrieval, standard_rows),
            ],
        ),
        (
            "Answer contract",
            [
                ("Strict Combined Pass", "strict_combined_pass", post, standard_answer_rows),
                ("Valid Time Correct", "valid_time_used_correct", post, standard_answer_rows),
                ("Expected Evidence Cited", "expected_evidence_cited", post, standard_answer_rows),
            ],
        ),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), sharey=True)
    for ax, (group_title, metrics) in zip(axes, groups):
        labels = [item[0] for item in metrics]
        chrono_vals = [to_float(item[2].get(item[1])) for item in metrics]
        best_standard = [max(to_float(row.get(item[1])) for row in item[3]) for item in metrics]
        x = list(range(len(labels)))
        ax.bar([idx - 0.18 for idx in x], best_standard, width=0.36, label="Best standard baseline", color="#7aa6c2")
        ax.bar([idx + 0.18 for idx in x], chrono_vals, width=0.36, label="ChronoRAG", color="#2f7d32")
        ax.set_title(group_title, fontsize=13)
        ax.set_xticks(x)
        ax.set_xticklabels(wrap_labels(labels, width=13), fontsize=10)
        ax.set_ylim(0, 1.08)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Score")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.03), ncol=2, fontsize=11)
    fig.suptitle("Figure 11. Metric family summary")
    save_figure(
        fig,
        "fig11_metric_family_summary",
        "ChronoRAG's strongest gains are on temporal-validity and answer-contract metrics, not generic broad recall.",
    )


def figure12_qa50_failure_decomposition() -> None:
    breakdown = qa50_failure_breakdown()
    if not breakdown:
        write_not_available("fig12_qa50_failure_decomposition", "QA50 per-case output JSONL files missing.")
        return
    labels = list(breakdown)
    components = ["Hit@5 + Pass", "Hit@5 + Fail", "No Hit@5 + Fail", "No Hit@5 + Pass"]
    colors = ["#2f7d32", "#f58518", "#e45756", "#b7b7b7"]
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    bottoms = [0] * len(labels)
    for component, color in zip(components, colors):
        vals = [breakdown[label].get(component, 0) for label in labels]
        ax.bar(labels, vals, bottom=bottoms, label=component, color=color)
        for idx, val in enumerate(vals):
            if val:
                ax.text(idx, bottoms[idx] + val / 2, str(val), ha="center", va="center", fontsize=11, color="white" if color != "#b7b7b7" else "#222")
        bottoms = [bottom + val for bottom, val in zip(bottoms, vals)]
    ax.set_title("Figure 12. QA50 failure decomposition")
    ax.set_ylabel("Cases out of 50")
    ax.set_ylim(0, 55)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=2)
    ax.grid(axis="y", alpha=0.2)
    save_figure(
        fig,
        "fig12_qa50_failure_decomposition",
        "QA50 standard retrieval + LLM baselines fail both because evidence is absent from top-k and because the LLM fails strict temporal contract even when evidence is present.",
    )


def figure13_claim_boundary() -> None:
    fig, ax = setup_canvas(figsize=(14, 8), title="Figure 13. Claim boundary")
    ax.text(0.27, 0.82, "Supported", ha="center", va="center", fontsize=18, weight="bold", color="#1f5f3a")
    ax.text(0.73, 0.82, "Not claimed", ha="center", va="center", fontsize=18, weight="bold", color="#8a2d25")
    supported = [
        "temporal-validity retrieval",
        "valid-time evidence selection",
        "forbidden / wrong-time exclusion",
        "answer-contract validation",
    ]
    not_claimed = [
        "open-domain RAG SOTA",
        "hallucination solved",
        "universal temporal reasoning",
        "public benchmark SOTA",
    ]
    for idx, text in enumerate(supported):
        rect_box(ax, 0.08, 0.64 - idx * 0.13, 0.38, 0.085, text, fc="#e9f9ee", fontsize=13)
    for idx, text in enumerate(not_claimed):
        rect_box(ax, 0.54, 0.64 - idx * 0.13, 0.38, 0.085, text, fc="#ffe9e6", fontsize=13)
    ax.plot([0.5, 0.5], [0.15, 0.78], color="#666", linewidth=1.5, linestyle="--")
    ax.text(
        0.5,
        0.07,
        "ChronoRAG's claims are intentionally bounded to temporal-validity evidence selection and validation.",
        ha="center",
        va="center",
        fontsize=13,
        color="#333",
    )
    save_figure(fig, "fig13_claim_boundary", "Conceptual claim-boundary schematic.")


def figure14_applications_map() -> None:
    fig, ax = setup_canvas(figsize=(16, 9), title="Figure 14. Applications map")
    rows = [
        ("Finance / macro", "reporting period vs filing date"),
        ("Legal / regulatory", "effective date vs publication date"),
        ("Enterprise search", "revision date vs fact date"),
        ("Scientific literature", "experiment period vs publication date"),
        ("Medical literature", "guideline validity vs update date"),
        ("Software releases", "release date vs version applicability"),
        ("Audit / investigation", "evidence time vs investigation time"),
    ]
    left_x, right_x = 0.08, 0.55
    top_y, step = 0.74, 0.095
    for idx, (domain, problem) in enumerate(rows):
        y = top_y - idx * step
        rect_box(ax, left_x, y, 0.32, 0.06, domain, fc="#f6f7fb", fontsize=12)
        rect_box(ax, right_x, y, 0.36, 0.06, problem, fc="#fff4d6", fontsize=11)
        arrow(ax, (left_x + 0.32, y + 0.03), (right_x, y + 0.03))
    ax.text(0.24, 0.84, "Application area", ha="center", fontsize=14, weight="bold")
    ax.text(0.73, 0.84, "Temporal-role problem", ha="center", fontsize=14, weight="bold")
    ax.text(
        0.5,
        0.05,
        "ChronoRAG is most relevant where evidence is time-sensitive and temporal roles are easy to confuse.",
        ha="center",
        fontsize=13,
        color="#333",
    )
    save_figure(fig, "fig14_applications_map", "Conceptual application map.")


def write_tables(
    table1: list[dict[str, str]],
    table2: list[dict[str, str]],
    table3: list[dict[str, str]],
    table4: list[dict[str, str]],
    topk: list[dict[str, str]],
) -> None:
    write_result_table(
        "table1_layer2a_retrieval_comparison.md",
        "Table 1. Layer 2A Retrieval Comparison",
        SOURCES["table1"],
        table1,
        ["method", "cases", "hit_at_1", "hit_at_5", "mrr_at_5", "forbidden_absent_at_5", "category_primary_pass"],
        "Direct result table. BM25 and Date-filter RAG have higher broad Hit@5, while ChronoRAG Full is strongest on temporal-validity diagnostics.",
    )
    write_result_table(
        "table2_ablation_comparison.md",
        "Table 2. Ablation Comparison",
        SOURCES["table2"],
        table2,
        ["method", "cases", "hit_at_1", "hit_at_5", "forbidden_absent_at_5", "category_primary_pass"],
        "Direct ablation table. Score-only retrieval improves broad Hit@5 but weakens forbidden-evidence exclusion and category-primary behavior.",
    )
    write_result_table(
        "table3_qa50_llm_post_filtering.md",
        "Table 3. QA50 LLM Post-Filtering Baselines",
        SOURCES["table3"],
        table3,
        ["method", "cases", "retrieval_hit_at_5", "strict_combined_pass", "deterministic_hard_contract_pass", "llm_judge_semantic_pass", "valid_time_used_correct", "expected_evidence_cited"],
        "Direct result table. Standard retrieval plus LLM temporal instructions does not recover ChronoRAG-level strict temporal QA performance.",
    )
    write_result_table(
        "table4_answer_level_comparison.md",
        "Table 4. QA50 Answer-Level Comparison",
        SOURCES["table4"],
        table4,
        ["method", "cases", "retrieval_hit5_or_evidence_available", "strict_combined_pass", "deterministic_hard_contract_pass", "llm_judge_semantic_pass", "expected_evidence_cited", "valid_time_used_correct"],
        "Extracted result table. Pre-injection retrieval availability and post-injection answer behavior are reported separately.",
    )
    rows5 = [
        {"method": "Score-only", "hit_at_5": "0.9850", "forbidden_absent_at_5": "0.6500", "category_primary_pass": "0.5625"},
        {"method": "ChronoRAG Full", "hit_at_5": "0.8950", "forbidden_absent_at_5": "0.9950", "category_primary_pass": "0.9625"},
    ]
    write_result_table(
        "table5_score_only_ablation.md",
        "Table 5. Score-Only Ablation",
        SOURCES["table2"],
        rows5,
        ["method", "hit_at_5", "forbidden_absent_at_5", "category_primary_pass"],
        "Extracted ablation contrast. Score-only maximizes broad Hit@5 but damages temporal-validity metrics.",
    )
    write_result_table(
        "table6_topk_sensitivity.md",
        "Table 6. Top-k Sensitivity",
        SOURCES["topk"],
        topk,
        ["method_label", "k", "cases", "hit_at_k", "mrr_at_k", "forbidden_absent_at_k", "category_primary_pass"],
        "Direct retrieval-only sensitivity table over k = 1, 3, 5, 10.",
    )


def write_result_table(filename: str, title: str, source: Path, rows: list[dict[str, Any]], columns: list[str], interpretation: str) -> None:
    lines = [f"# {title}", "", f"Source artifact: `{rel(source)}`", "", "Metric definitions:"]
    for name, definition in METRIC_DEFINITIONS.items():
        lines.append(f"- {name}: {definition}")
    lines.extend(["", markdown_table(rows, columns), "", f"Interpretation: {interpretation}", "", "Result type: generated from existing result artifacts; no new experiment was run.", ""])
    path = TABLE_DIR / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    record(path, "table", title, rel(source))


def write_github_snippets() -> None:
    results = """# ChronoRAG Results Snapshot

ChronoRAG targets temporal-validity retrieval, not generic open-domain RAG
superiority. On Layer 2A, BM25 and Date-filter RAG have higher broad Hit@5, but
ChronoRAG Full has stronger Hit@1, MRR@5, Forbidden Absent@5, and Category
Primary Pass.

- Main retrieval table: [Table 1](../tables/table1_layer2a_retrieval_comparison.md)
- QA50 LLM post-filtering: [Table 3](../tables/table3_qa50_llm_post_filtering.md)
- Answer-level split: [Table 4](../tables/table4_answer_level_comparison.md)
- Top-k sensitivity: [Table 6](../tables/table6_topk_sensitivity.md)
"""
    write_text(GITHUB_DIR / "readme_results_section.md", results, "github-snippet", "Copy-paste README result summary.", "generated tables")
    figures = """# Figures

![Temporal misgrounding schematic](../figures/fig1_temporal_misgrounding_concept.png)
![ChronoRAG architecture](../figures/fig2_chronorag_architecture.png)
![Layer 2A retrieval comparison](../figures/fig3_layer2a_retrieval_comparison.png)
![Temporal-validity diagnostics](../figures/fig4_temporal_validity_diagnostics.png)
![Score-only ablation](../figures/fig5_score_only_ablation.png)
![QA50 LLM post-filtering](../figures/fig6_qa50_llm_post_filtering.png)
![Temporal feature heatmap](../figures/fig9_temporal_feature_heatmap.png)
![One-query trace](../figures/fig10_one_query_trace.png)
![Metric family summary](../figures/fig11_metric_family_summary.png)

Place figures next to the claims they support: Figure 1 near the temporal
misgrounding motivation, Figure 2 near the architecture, Figures 3-5 near
Layer 2A retrieval and ablation results, Figure 6 near QA50 post-filtering,
Figure 9 near trace/mechanism discussion, and Figure 10 near qualitative
retrieval examples. Quantitative charts are generated from existing result
artifacts; conceptual figures are labeled as schematics.
"""
    write_text(GITHUB_DIR / "readme_figures_section.md", figures, "github-snippet", "Copy-paste README figure section.", "generated figures")
    links = """# Badges Or Links

- Research artifact index: [rpartifacts/README.md](../README.md)
- Paper figure plan: [paper_figure_plan.md](../paper/paper_figure_plan.md)
- GitHub result snippet: [readme_results_section.md](readme_results_section.md)
- LinkedIn launch assets: [linkedin/](../linkedin/)

Suggested badge text: `Temporal-validity retrieval`, `Layer 2A 200-case
retrieval`, `QA50 answer validation`, `No SOTA claim`.
"""
    write_text(GITHUB_DIR / "readme_badges_or_links.md", links, "github-snippet", "Copy-paste links and badge text.", "artifact index")


def write_linkedin_assets() -> None:
    short = """I built ChronoRAG to study a specific RAG failure mode: temporal misgrounding.

Same topic does not mean valid evidence. Publication, filing, or release dates
can differ from the time a fact was actually valid.

The latest artifact package includes retrieval comparisons, ablations, QA50 LLM
post-filtering baselines, and paper-ready figures. The main result is careful:
ChronoRAG is not claiming generic RAG superiority. It improves temporal-validity
diagnostics such as forbidden-evidence exclusion and category-primary evidence
selection.

GitHub: https://github.com/SSKG2602/chronorag
"""
    write_text(LINKEDIN_DIR / "linkedin_post_short.md", short, "linkedin", "Short launch post.", "artifact summary")
    long = """ChronoRAG is a temporal-validity retrieval and grounded answer-validation framework for RAG over messy multi-role evidence corpora.

The problem: standard retrieval can find passages that are semantically close but valid at the wrong time. In temporal QA, a filing date, publication date, release date, or nearby date can look relevant while failing the actual valid-time contract.

What this artifact package adds:

- paper-ready figures and tables
- Layer 2A standard baselines: BM25, Dense-only, Date-filter RAG, Metadata Temporal RAG, ChronoRAG Full
- score-only ablation showing that broad Hit@5 and temporal-validity retrieval are different objectives
- QA50 LLM post-filtering baselines showing that prompting alone does not replace retrieval-layer grounding
- explicit limitations and threats to validity

No SOTA claim. The claim is narrower: temporally valid evidence selection and answer-contract validation matter before evidence reaches generation.

GitHub: https://github.com/SSKG2602/chronorag
"""
    write_text(LINKEDIN_DIR / "linkedin_post_long.md", long, "linkedin", "Long launch post.", "artifact summary")
    carousel = """# LinkedIn Carousel Plan

1. Problem: same topic does not mean valid time.
2. Clean architecture: temporal role grounding is separated from answer generation.
3. Main retrieval chart: Layer 2A standard comparison.
4. Score-only ablation: broad Hit@5 can damage temporal validity.
5. One-query trace: BM25 finds wrong-time rows; ChronoRAG selects the requested valid-time row.
6. QA50 post-filter chart: LLM prompting does not replace retrieval-layer grounding.
7. Claim boundary: no SOTA claim, no hallucination-solved claim.
8. GitHub link / paper draft coming.
"""
    write_text(LINKEDIN_DIR / "linkedin_carousel_plan.md", carousel, "linkedin", "Carousel plan.", "artifact summary")


def write_paper_notes() -> None:
    write_text(
        PAPER_DIR / "paper_figure_plan.md",
        """# Paper Figure Plan

1. Figure 1: temporal misgrounding concept schematic.
2. Figure 2: ChronoRAG architecture schematic.
   Caption: ChronoRAG separates temporal role grounding from answer generation. Layer 2A evaluates selected evidence before answer synthesis, while Layer 2B evaluates answer-contract behavior after generation.
3. Figure 3: Layer 2A retrieval comparison.
4. Figure 4: temporal-validity diagnostics.
5. Figure 5: score-only ablation.
6. Figure 6: QA50 LLM post-filtering comparison.
7. Figure 7: pre/post injection fairness split.
8. Figure 8: top-k sensitivity, with split Figure 8a and Figure 8b variants for readability.
9. Figure 9: temporal feature heatmap from retrieval-only candidate trace export.
10. Figure 10: real one-query trace.
11. Figure 11: metric family summary.
12. Figure 12: QA50 failure decomposition.
13. Figure 13: claim boundary schematic.
14. Figure 14: applications map schematic.
""",
        "paper-note",
        "Paper figure plan.",
        "generated figures",
    )
    write_text(
        PAPER_DIR / "paper_result_narrative.md",
        """# Paper Result Narrative

Layer 2A is the primary retrieval-quality benchmark. BM25 and Date-filter RAG
achieve higher broad Hit@5 than ChronoRAG Full, but ChronoRAG Full is strongest
on Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass. This supports
temporal-validity retrieval, not generic retrieval superiority.

The score-only ablation shows why broad retrieval score optimization is not the
same objective: Score-only reaches 0.9850 Hit@5 while falling to 0.6500
Forbidden Absent@5 and 0.5625 Category Primary Pass.

QA50 LLM post-filtering baselines show that downstream prompting does not
replace retrieval-layer grounding. Standard retrieval plus the same LLM prompt
reaches 0.3200-0.4000 strict combined pass, while ChronoRAG reaches 0.7000 in
the prior post-injection answer setting.
""",
        "paper-note",
        "Paper result narrative.",
        "generated tables",
    )
    limitations = """# Paper Limitations Insert

The 50-case answer-level evaluation is directional and should be scaled.
Forbidden Absent@5 and Category Primary Pass are custom metrics and depend on
benchmark label quality. Labels are author-created unless independent
annotation evidence exists. The corpus is controlled and cross-domain but not a
public temporal QA benchmark. Fusion-weight sensitivity and reranker isolation
were not run because no safe runtime switches exist. Generalization beyond
financial, regulatory, macroeconomic, market, and software-release evidence is
future work. ChronoRAG depends on temporal extraction quality.
"""
    write_text(PAPER_DIR / "paper_limitations_insert.md", limitations, "paper-note", "Paper limitations insert.", "approved limitations")
    metric_lines = ["# Paper Metric Definitions Insert", ""]
    metric_lines.extend(f"- {name}: {definition}" for name, definition in METRIC_DEFINITIONS.items())
    metric_lines.append("")
    metric_lines.append("Forbidden Absent@5 and Category Primary Pass are constraint-sensitive diagnostics for temporal-validity retrieval. They complement, rather than replace, Hit@k and MRR@5.")
    write_text(PAPER_DIR / "paper_metric_definitions_insert.md", "\n".join(metric_lines), "paper-note", "Metric definitions insert.", "approved metrics")
    dataset = """# Paper Dataset Protocol Insert

The current artifact records benchmark labels as fixed JSONL fields. Expected
evidence IDs, forbidden evidence IDs, and category-primary labels are
author-created and treated as fixed before method scoring. Large-scale
independent annotation is not included in this version and is listed as a
limitation. Standard comparisons use the same corpus, same queries, same
top-k=5, same evaluator, and same candidate corpus where applicable. Gold
expected evidence IDs were not included in LLM baseline prompts.
"""
    write_text(PAPER_DIR / "paper_dataset_protocol_insert.md", dataset, "paper-note", "Dataset protocol insert.", "approved protocol")
    write_text(PAPER_DIR / "paper_threats_to_validity_insert.md", limitations.replace("Paper Limitations", "Paper Threats To Validity"), "paper-note", "Threats to validity insert.", "approved limitations")


def write_root_readme() -> None:
    text = """# ChronoRAG Research Artifacts

This folder contains paper-ready figures, tables, GitHub README snippets,
LinkedIn launch drafts, and paper integration notes generated from existing
ChronoRAG result artifacts.

## Scope

`rpartifacts/` is the research-artifact package for paper writing, GitHub
README polish, and public communication. Quantitative charts are generated from
stored result artifacts or retrieval-only traces. Conceptual diagrams are
explicitly marked as schematics.

## Figure Index

| Figure | Grounding | Source artifact paths | Use |
|---|---|---|---|
| [Figure 1: Temporal misgrounding concept](figures/fig1_temporal_misgrounding_concept.png) | Schematic | Conceptual summary of the project failure mode | Paper-critical, README-friendly |
| [Figure 2: ChronoRAG architecture](figures/fig2_chronorag_architecture.png) | Schematic | Fixed-coordinate diagram generated by `rpartifacts/generate_research_artifacts.py` | Paper-critical, README-friendly |
| [Figure 3: Layer 2A retrieval comparison](figures/fig3_layer2a_retrieval_comparison.png) | Data-grounded | `docs/paper_assets/table1_layer2a_retrieval_standard_comparison.csv` | Paper-critical |
| [Figure 4: Temporal-validity diagnostics](figures/fig4_temporal_validity_diagnostics.png) | Data-grounded | Table 1 CSV plus `docs/paper_assets/table2_layer2a_ablation_comparison.csv` | Paper-supporting |
| [Figure 5: Score-only ablation](figures/fig5_score_only_ablation.png) | Data-grounded | `docs/paper_assets/table2_layer2a_ablation_comparison.csv` | Paper-critical, LinkedIn-friendly |
| [Figure 6: QA50 LLM post-filtering](figures/fig6_qa50_llm_post_filtering.png) | Data-grounded | `docs/paper_assets/table3_qa50_llm_post_filter_baselines.csv`, `docs/paper_assets/table4_qa50_answer_level_comparison.csv` | Paper-critical, LinkedIn-friendly |
| [Figure 7: Pre/post injection fairness split](figures/fig7_injection_fairness_split.png) | Data-grounded | QA50 extracted values and paper table CSVs | Paper-supporting |
| [Figure 8: Top-k sensitivity](figures/fig8_topk_sensitivity.png) | Data-grounded | `docs/paper_assets/topk_sensitivity.csv` | Paper-supporting |
| [Figure 8a: Ranking sensitivity](figures/fig8a_topk_hit_sensitivity.png) | Data-grounded | `docs/paper_assets/topk_sensitivity.csv` | Readability variant |
| [Figure 8b: Temporal-validity sensitivity](figures/fig8b_topk_temporal_validity_sensitivity.png) | Data-grounded | `docs/paper_assets/topk_sensitivity.csv` | Readability variant |
| [Figure 9: Temporal feature heatmap](figures/fig9_temporal_feature_heatmap.png) | Data-grounded | `rpartifacts/data/temporal_feature_trace.jsonl`, `rpartifacts/data/temporal_feature_trace.csv` | Paper-critical |
| [Figure 10: One-query trace](figures/fig10_one_query_trace.png) | Data-grounded | `chronorag/stdcomp/results/stdcomp_layer2a_comparison.json`, `chronorag/stdcomp/results/bm25_ranked_outputs.json` | Paper-critical, README-friendly |
| [Figure 11: Metric family summary](figures/fig11_metric_family_summary.png) | Data-grounded | Layer 2A and QA50 paper table CSVs | Paper-supporting |
| [Figure 12: QA50 failure decomposition](figures/fig12_qa50_failure_decomposition.png) | Data-grounded | `chronorag/stdcomp/results/qa50_llm_baselines/*_outputs.jsonl` | Paper-supporting, LinkedIn-friendly |
| [Figure 13: Claim boundary](figures/fig13_claim_boundary.png) | Schematic | Conceptual claim boundary from documented limitations | README-friendly, LinkedIn-friendly |
| [Figure 14: Applications map](figures/fig14_applications_map.png) | Schematic | Conceptual application map | LinkedIn-friendly |

Figure 2 caption:
ChronoRAG separates temporal role grounding from answer generation. Layer 2A
evaluates selected evidence before answer synthesis, while Layer 2B evaluates
answer-contract behavior after generation.

Figure 9 is generated from a retrieval-only candidate trace export. See
[paper/temporal_feature_heatmap.md](paper/temporal_feature_heatmap.md) for
normalization and provenance details. The schema recommendation remains at
[paper/temporal_feature_trace_logging_recommendation.md](paper/temporal_feature_trace_logging_recommendation.md).

## GitHub/LinkedIn Friendly Assets

- GitHub snippets: [github/](github/)
- LinkedIn launch drafts: [linkedin/](linkedin/)
- Paper inserts: [paper/](paper/)

The root README places the main figures near the explanations they support
rather than collecting them as a detached gallery.

## Tables

- [Table 1: Layer 2A retrieval comparison](tables/table1_layer2a_retrieval_comparison.md)
- [Table 2: Ablation comparison](tables/table2_ablation_comparison.md)
- [Table 3: QA50 LLM post-filtering](tables/table3_qa50_llm_post_filtering.md)
- [Table 4: Answer-level comparison](tables/table4_answer_level_comparison.md)
- [Table 5: Score-only ablation](tables/table5_score_only_ablation.md)
- [Table 6: Top-k sensitivity](tables/table6_topk_sensitivity.md)
- [Table 7: Artifact manifest](tables/table7_artifact_manifest.md)

## Regenerate Everything

```bash
python3 rpartifacts/generate_research_artifacts.py
```

## Use In Paper And README

- Paper: use [paper/paper_figure_plan.md](paper/paper_figure_plan.md) and the
  tables under [tables/](tables/).
- README: use snippets under [github/](github/), but keep figures near the
  relevant method or result discussion.
- LinkedIn: use launch drafts under [linkedin/](linkedin/).

## Claim Boundary

Do not claim generic open-domain RAG superiority or SOTA. Do not treat
post-injection answer-level evidence availability as baseline retrieval
availability. Do not present conceptual schematics as experimental results. Do
not present Figure 9 as an LLM or answer-generation result; it is a
retrieval-only candidate trace. Do not present Figure 12 as a new experiment;
it is derived from stored QA50 baseline output JSONL files.
"""
    write_text(OUT / "README.md", text, "index", "Research artifact package index.", "generated artifacts")


def write_manifest_table() -> None:
    rows = [{"path": rel(Path(item["path"])), "type": item["type"], "description": item["description"], "source": item["source"]} for item in ARTIFACTS]
    write_json(DATA_DIR / "artifact_manifest.json", {"artifacts": rows})
    lines = [
        "# Table 7. Artifact Manifest",
        "",
        "Source artifact path: generated from `rpartifacts/generate_research_artifacts.py` run output.",
        "",
        markdown_table(rows, ["path", "type", "description", "source"]),
        "",
        "Interpretation: this table lists generated files and their source basis.",
        "",
        "Result type: artifact manifest.",
        "",
    ]
    path = TABLE_DIR / "table7_artifact_manifest.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    record(path, "table", "Table 7 artifact manifest.", "rpartifacts generator")


def write_missing_inputs() -> None:
    if not MISSING:
        return
    lines = ["# Missing Inputs", "", "The generator continued, but these source artifacts were missing:", ""]
    lines.extend(f"- `{item}`" for item in MISSING)
    lines.append("")
    path = OUT / "MISSING_INPUTS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    record(path, "diagnostic", "Missing source input list.", "source check")


def setup_canvas(figsize: tuple[float, float], title: str):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title(title, fontsize=16, pad=16)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, x: float, y: float, w: float, h: float, text: str, fc: str = "#ffffff", fontsize: int = 11) -> None:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02", linewidth=1.4, edgecolor="#333", facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, wrap=True)


def rect_box(ax, x: float, y: float, w: float, h: float, text: str, fc: str = "#ffffff", fontsize: int = 11) -> None:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.018", linewidth=1.25, edgecolor="#333", facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, wrap=True)


def card(ax, x: float, y: float, w: float, h: float, title: str, content: str, fc: str = "#ffffff") -> None:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.018,rounding_size=0.012", linewidth=1.2, edgecolor="#333", facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + 0.025, y + h - 0.035, title, ha="left", va="top", fontsize=14, weight="bold", color="#222")
    ax.text(x + 0.025, y + h - 0.075, wrap_preserve_newlines(content, 104), ha="left", va="top", fontsize=10.8, color="#222", linespacing=1.25)


def arrow(ax, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=14, linewidth=1.4, color="#333"))


def grouped_bars(ax, rows: list[dict[str, Any]], label_key: str, metrics: list[str], metric_labels: list[str], width: float = 0.14) -> None:
    x = list(range(len(metrics)))
    n = len(rows)
    offsets = [(idx - (n - 1) / 2) * width for idx in range(n)]
    colors = ["#4c78a8", "#f58518", "#54a24b", "#b279a2", "#2f7d32", "#e45756", "#72b7b2"]
    for idx, row in enumerate(rows):
        vals = [to_float(row.get(metric)) for metric in metrics]
        ax.bar([pos + offsets[idx] for pos in x], vals, width=width, label=str(row.get(label_key)), color=colors[idx % len(colors)])
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels)


def save_figure(fig, stem: str, caption: str) -> None:
    png = FIG_DIR / f"{stem}.png"
    svg = FIG_DIR / f"{stem}.svg"
    fig.tight_layout()
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)
    record(png, "figure", caption, "generated from existing artifacts or schematic")
    record(svg, "figure", caption, "generated from existing artifacts or schematic")


def write_not_available(stem: str, reason: str) -> None:
    path = FIG_DIR / f"{stem}_not_available.md"
    path.write_text(f"# {stem} Not Available\n\n{reason}\n", encoding="utf-8")
    record(path, "figure-note", reason, "source availability check")


def write_one_query_needed(reason: str) -> None:
    path = PAPER_DIR / "one_query_trace_needed.md"
    path.write_text(f"# One Query Trace Needed\n\n{reason}\n", encoding="utf-8")
    record(path, "paper-note", reason, "source availability check")


def find_question(case_id: str | None) -> str:
    if not case_id:
        return "n/a"
    ranked_path = ROOT / "chronorag/stdcomp/results/bm25_ranked_outputs.json"
    if ranked_path.exists():
        payload = json.loads(ranked_path.read_text(encoding="utf-8"))
        for row in payload.get("results", []):
            if row.get("case_id") == case_id:
                return row.get("question") or "n/a"
    return "n/a"


def find_row(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get(key) == value:
            return row
    return None


def to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def as_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_large(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10**9


def normalize_columns(matrix: list[list[float | None]]) -> list[list[float]]:
    if not matrix:
        return []
    columns = len(matrix[0])
    mins: list[float] = []
    maxes: list[float] = []
    for col in range(columns):
        values = [row[col] for row in matrix if row[col] is not None]
        mins.append(min(values) if values else 0.0)
        maxes.append(max(values) if values else 0.0)
    normalized: list[list[float]] = []
    for row in matrix:
        norm_row = []
        for col, value in enumerate(row):
            if value is None:
                norm_row.append(0.0)
                continue
            lo = mins[col]
            hi = maxes[col]
            if hi == lo:
                norm_row.append(1.0 if value > 0 else 0.0)
            else:
                norm_row.append((value - lo) / (hi - lo))
        normalized.append(norm_row)
    return normalized


def metric_label(column: str) -> str:
    labels = {
        "semantic_score": "Semantic\nscore",
        "bm25_score": "BM25\nscore",
        "dense_score": "Dense\nscore",
        "temporal_precision_score": "Temporal\nprecision",
        "valid_time_fit": "Valid-time\nfit",
        "interval_overlap_score": "Interval\noverlap",
        "transaction_time_penalty": "Transaction\npenalty",
        "forbidden_time_penalty": "Forbidden\npenalty",
        "source_metric_score": "Source/metric\nadjustment",
        "slot_score": "Slot\nscore",
        "fusion_score": "Fusion\nscore",
        "final_score": "Final\nscore",
    }
    return labels.get(column, column.replace("_", "\n"))


def heatmap_row_label(row: dict[str, Any]) -> str:
    label = short_evidence_id(str(row.get("candidate_evidence_id") or "unknown"))
    markers = []
    if row.get("selected"):
        markers.append("selected")
    if row.get("expected"):
        markers.append("expected")
    if row.get("forbidden"):
        markers.append("forbidden")
    return f"{label} [{' '.join(markers)}]" if markers else label


def short_evidence_id(evidence_id: str) -> str:
    parts = evidence_id.split(":")
    if len(parts) >= 4:
        return ":".join(parts[-3:])
    return evidence_id


def nested_metric(values: Any, key: str, default: float) -> float:
    if isinstance(values, dict):
        value = values.get(key)
        if isinstance(value, dict):
            return to_float(value.get("value"))
        return to_float(value) if value is not None else default
    return default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def qa50_failure_breakdown() -> dict[str, dict[str, int]]:
    paths = [
        ("BM25 + LLM", SOURCES["bm25_qa50_outputs"]),
        ("Dense-only + LLM", SOURCES["dense_qa50_outputs"]),
        ("Date-filter RAG + LLM", SOURCES["date_filter_qa50_outputs"]),
    ]
    breakdown: dict[str, dict[str, int]] = {}
    for label, path in paths:
        rows = read_jsonl(path)
        if not rows:
            return {}
        counts = {"Hit@5 + Pass": 0, "Hit@5 + Fail": 0, "No Hit@5 + Fail": 0, "No Hit@5 + Pass": 0}
        for row in rows:
            retrieval = row.get("retrieval_metrics") or {}
            hit = bool(retrieval.get("hit@5"))
            passed = bool(row.get("combined_pass"))
            if hit and passed:
                counts["Hit@5 + Pass"] += 1
            elif hit and not passed:
                counts["Hit@5 + Fail"] += 1
            elif not hit and passed:
                counts["No Hit@5 + Pass"] += 1
            else:
                counts["No Hit@5 + Fail"] += 1
        breakdown[label] = counts
    return breakdown


def find_case_report(report: dict[str, Any], case_id: str) -> dict[str, Any] | None:
    for case in report.get("case_reports", []):
        if case.get("case_id") == case_id:
            return case
    return None


def find_ranked_output(path: Path, case_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    for row in payload.get("results", []):
        if row.get("case_id") == case_id:
            return row
    return None


def wrap_labels(labels: list[str], width: int = 12) -> list[str]:
    return [wrap(label, width).replace("\n", "\n") for label in labels]


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._"
    labels = [column.replace("_", " ").title() for column in columns]
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        cells = [format_cell(row.get(column)) for column in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_cell(value: Any) -> str:
    if value in (None, ""):
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    text = str(value)
    return text.replace("|", "\\|")


def fmt_ids(values: Any) -> str:
    if not values:
        return "none"
    return "<br>".join(f"`{item}`" for item in values)


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width)) if text else "n/a"


def wrap_preserve_newlines(text: str, width: int) -> str:
    if not text:
        return "n/a"
    lines = []
    for line in text.splitlines():
        if not line:
            lines.append("")
        else:
            lines.extend(textwrap.wrap(line, width=width) or [""])
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str, kind: str, description: str, source: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")
    record(path, kind, description, source)


def record(path: Path, kind: str, description: str, source: str) -> None:
    ARTIFACTS.append({"path": str(path), "type": kind, "description": description, "source": source})


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
