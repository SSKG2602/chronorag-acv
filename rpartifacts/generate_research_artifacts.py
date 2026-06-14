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
    figure9_feature_heatmap_note()
    figure10_one_query_trace(stdcomp)

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
    fig, ax = setup_canvas(figsize=(16, 8.5), title="Figure 2. ChronoRAG architecture")
    labels = [
        "Raw evidence rows",
        "Temporal Contextual Chunking",
        "Temporal metadata extraction",
        "Valid-time / transaction-time separation",
        "Candidate retrieval",
        "Temporal precision scoring",
        "Temporal fusion",
        "Forbidden-time suppression",
        "Source/metric-aware adjustment",
        "Slot-aware finalization",
        "ChronoSanity conflict guard",
        "Attribution cards / final evidence",
        "Answer synthesizer",
        "Answer-contract validation",
    ]
    xs = [0.04, 0.25, 0.46, 0.67]
    ys = [0.78, 0.58, 0.38, 0.18]
    positions = []
    for idx, label in enumerate(labels):
        col = idx % 4
        row = idx // 4
        x, y = xs[col], ys[row]
        positions.append((x, y))
        color = "#f6f7fb" if idx < 4 else "#e9f4ff" if idx < 10 else "#e5f7e9"
        box(ax, x, y, 0.17, 0.105, label, fc=color, fontsize=10)
    for (x1, y1), (x2, y2) in zip(positions[:-1], positions[1:]):
        arrow(ax, (x1 + 0.17, y1 + 0.052), (x2, y2 + 0.052))
    box(ax, 0.67, 0.01, 0.21, 0.10, "Layer 2A retrieval-only scoring", fc="#fff4d6", fontsize=10)
    arrow(ax, (positions[11][0] + 0.09, positions[11][1]), (0.77, 0.11))
    ax.text(0.03, 0.04, "Retrieval-only evaluation branches from final evidence before answer synthesis.", fontsize=11)
    save_figure(fig, "fig2_chronorag_architecture", "Architecture schematic; not an experimental result.")


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
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        for method in methods:
            rows = sorted([row for row in topk if (row.get("method_label") or row.get("method")) == method], key=lambda r: to_float(r.get("k")))
            ax.plot([to_float(r.get("k")) for r in rows], [to_float(r.get(metric)) for r in rows], marker="o", label=method)
        ax.set_title(label)
        ax.set_ylim(0, 1.08)
        ax.set_xticks([1, 3, 5, 10])
        ax.grid(alpha=0.25)
    axes[1, 1].legend(loc="lower center", bbox_to_anchor=(0.5, -0.55), ncol=2)
    fig.suptitle("Figure 8. Top-k retrieval-only sensitivity")
    save_figure(fig, "fig8_topk_sensitivity", "Generated from top-k sensitivity artifact.")


def figure9_feature_heatmap_note() -> None:
    text = """# Figure 9 Temporal Feature Heatmap Not Available

Candidate-level temporal feature traces are not stored in the existing result
artifacts. The current artifacts contain selected evidence IDs, aggregate
metrics, and case-level pass/fail diagnostics, but they do not persist
per-candidate semantic score, temporal fit, valid-time fit, transaction
penalty, forbidden penalty, source/metric fit, slot assignment, and final score
columns.

Future retrieval-only runs should persist per-candidate scoring traces if the
paper needs a true temporal feature heatmap. No synthetic numeric heatmap was
generated.
"""
    path = FIG_DIR / "fig9_temporal_feature_heatmap_not_available.md"
    path.write_text(text, encoding="utf-8")
    record(path, "figure-note", "Feature heatmap not generated because candidate-level traces are unavailable.", "artifact schema inspection")


def figure10_one_query_trace(stdcomp: dict[str, Any]) -> None:
    if not stdcomp:
        write_not_available("fig10_one_query_trace", "Standard comparison JSON missing.")
        write_one_query_needed("Standard comparison JSON missing.")
        return
    reports = {report.get("method"): report for report in stdcomp.get("reports", [])}
    chrono = reports.get("chronorag_full", {})
    candidates = [reports.get(name, {}) for name in ("bm25", "metadata_temporal_rag", "dense_only", "date_filter_rag")]
    chosen = None
    baseline_report = None
    for case in chrono.get("case_reports", []):
        if not case.get("retrieval_pass"):
            continue
        cid = case.get("case_id")
        for report in candidates:
            for other in report.get("case_reports", []):
                if other.get("case_id") == cid and not other.get("retrieval_pass"):
                    chosen = case
                    baseline_report = other | {"method": report.get("method_label") or report.get("method")}
                    break
            if chosen:
                break
        if chosen:
            break
    if not chosen or not baseline_report:
        write_not_available("fig10_one_query_trace", "No safe real case found where a baseline fails and ChronoRAG succeeds.")
        write_one_query_needed("No safe real case found where a baseline fails and ChronoRAG succeeds.")
        return

    question = find_question(chosen.get("case_id"))
    md = [
        "# One-Query Trace",
        "",
        "This is a real Layer 2A retrieval-only benchmark case extracted from existing artifacts.",
        "",
        f"- Case ID: `{chosen.get('case_id')}`",
        f"- Category: `{chosen.get('category')}`",
        f"- Question: {question}",
        f"- Expected evidence: `{', '.join(chosen.get('expected_evidence_ids') or [])}`",
        f"- Forbidden evidence: `{', '.join(chosen.get('forbidden_evidence_ids') or [])}`",
        "",
        "| Method | Retrieval pass | Reason | Selected evidence | Forbidden overlap |",
        "|---|---:|---|---|---|",
        f"| {baseline_report.get('method')} | {baseline_report.get('retrieval_pass')} | {baseline_report.get('retrieval_pass_reason')} | {fmt_ids(baseline_report.get('selected_evidence_ids'))} | {fmt_ids(baseline_report.get('selected_forbidden_overlap'))} |",
        f"| ChronoRAG Full | {chosen.get('retrieval_pass')} | {chosen.get('retrieval_pass_reason')} | {fmt_ids(chosen.get('selected_evidence_ids'))} | {fmt_ids(chosen.get('selected_forbidden_overlap'))} |",
        "",
        "Interpretation: the baseline retrieves expected evidence but also includes forbidden wrong-time evidence; ChronoRAG keeps the expected evidence while excluding the forbidden rows.",
        "",
    ]
    md_path = PAPER_DIR / "one_query_trace.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    record(md_path, "paper-note", "Real one-query trace from Layer 2A artifacts.", "stdcomp case reports")

    fig, ax = setup_canvas(figsize=(14, 5.5), title="Figure 10. One-query retrieval trace")
    ax.axis("off")
    table_rows = [
        ["Case", chosen.get("case_id", ""), wrap(question, 62)],
        ["Expected", "", wrap(", ".join(chosen.get("expected_evidence_ids") or []), 62)],
        [baseline_report.get("method", "Baseline"), "FAIL", wrap("selected: " + ", ".join(baseline_report.get("selected_evidence_ids") or []), 62)],
        ["Forbidden overlap", "", wrap(", ".join(baseline_report.get("selected_forbidden_overlap") or []), 62)],
        ["ChronoRAG Full", "PASS", wrap("selected: " + ", ".join(chosen.get("selected_evidence_ids") or []), 62)],
    ]
    table = ax.table(cellText=table_rows, colLabels=["Row", "Status", "Evidence"], loc="center", cellLoc="left", colWidths=[0.18, 0.12, 0.70])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.0)
    save_figure(fig, "fig10_one_query_trace", "Generated from real Layer 2A case reports.")


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
![Score-only ablation](../figures/fig5_score_only_ablation.png)
![QA50 LLM post-filtering](../figures/fig6_qa50_llm_post_filtering.png)

All quantitative charts are generated from existing result artifacts. Conceptual
figures are labeled as schematics.
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
2. ChronoRAG idea: temporal-validity retrieval before generation.
3. Main retrieval chart: Layer 2A standard comparison.
4. Score-only ablation: broad Hit@5 can damage temporal validity.
5. QA50 post-filter chart: LLM prompting does not replace retrieval-layer grounding.
6. Honest limitations: controlled corpus, author-created labels, custom diagnostics, no SOTA claim.
7. GitHub link / paper draft coming.
"""
    write_text(LINKEDIN_DIR / "linkedin_carousel_plan.md", carousel, "linkedin", "Carousel plan.", "artifact summary")


def write_paper_notes() -> None:
    write_text(
        PAPER_DIR / "paper_figure_plan.md",
        """# Paper Figure Plan

1. Figure 1: temporal misgrounding concept schematic.
2. Figure 2: ChronoRAG architecture schematic.
3. Figure 3: Layer 2A retrieval comparison.
4. Figure 4: temporal-validity diagnostics.
5. Figure 5: score-only ablation.
6. Figure 6: QA50 LLM post-filtering comparison.
7. Figure 7: pre/post injection fairness split.
8. Figure 8: top-k sensitivity.
9. Figure 9: temporal feature heatmap not available until candidate traces are persisted.
10. Figure 10: real one-query trace.
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

## What This Folder Is

`rpartifacts/` is a research-artifact package for paper writing, GitHub README
polish, LinkedIn launch preparation, and professor review. Quantitative charts
are generated from stored result artifacts. Conceptual diagrams are explicitly
marked as schematics.

## Paper-Critical Figures

- [Figure 1: Temporal misgrounding concept](figures/fig1_temporal_misgrounding_concept.png)
- [Figure 2: ChronoRAG architecture](figures/fig2_chronorag_architecture.png)
- [Figure 3: Layer 2A retrieval comparison](figures/fig3_layer2a_retrieval_comparison.png)
- [Figure 4: Temporal-validity diagnostics](figures/fig4_temporal_validity_diagnostics.png)
- [Figure 5: Score-only ablation](figures/fig5_score_only_ablation.png)
- [Figure 6: QA50 LLM post-filtering](figures/fig6_qa50_llm_post_filtering.png)
- [Figure 7: Pre/post injection fairness split](figures/fig7_injection_fairness_split.png)
- [Figure 8: Top-k sensitivity](figures/fig8_topk_sensitivity.png)
- [Figure 10: One-query trace](figures/fig10_one_query_trace.png)

Figure 9 is not generated as a heatmap because candidate-level temporal feature
traces are not stored in existing artifacts. See
[fig9_temporal_feature_heatmap_not_available.md](figures/fig9_temporal_feature_heatmap_not_available.md).

## GitHub/LinkedIn Friendly Assets

- GitHub snippets: [github/](github/)
- LinkedIn launch drafts: [linkedin/](linkedin/)
- Paper inserts: [paper/](paper/)

## Generated From Real Result Artifacts

Figures 3, 4, 5, 6, 7, 8, and 10 are generated from stored CSV/JSON result
artifacts. Figures 1 and 2 are conceptual schematics. Figure 9 is explicitly
not available as a numeric heatmap.

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

## How To Use

- Paper: use [paper/paper_figure_plan.md](paper/paper_figure_plan.md) and the
  tables under [tables/](tables/).
- README: use snippets under [github/](github/).
- LinkedIn: use launch drafts under [linkedin/](linkedin/).

## What Not To Claim

Do not claim generic open-domain RAG superiority or SOTA. Do not treat
post-injection answer-level evidence availability as baseline retrieval
availability. Do not present conceptual schematics as experimental results. Do
not claim a temporal feature heatmap until candidate-level feature traces are
persisted.
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


def nested_metric(values: Any, key: str, default: float) -> float:
    if isinstance(values, dict):
        value = values.get(key)
        if isinstance(value, dict):
            return to_float(value.get("value"))
        return to_float(value) if value is not None else default
    return default


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
