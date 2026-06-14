# ChronoRAG Research Artifacts

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
