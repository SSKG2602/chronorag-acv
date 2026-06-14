# Table 7. Artifact Manifest

Source artifact path: generated from `rpartifacts/generate_research_artifacts.py` run output.

| Path | Type | Description | Source |
|---|---|---|---|
| rpartifacts/data/source_artifact_manifest.json | data | Source artifact existence manifest. | source paths |
| rpartifacts/data/derived_plot_data.json | data | Normalized data used by rpartifacts figures. | existing result artifacts |
| rpartifacts/figures/fig1_temporal_misgrounding_concept.png | figure | Conceptual schematic; not an experimental result. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig1_temporal_misgrounding_concept.svg | figure | Conceptual schematic; not an experimental result. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig2_chronorag_architecture.png | figure | Architecture schematic; not an experimental result. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig2_chronorag_architecture.svg | figure | Architecture schematic; not an experimental result. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig3_layer2a_retrieval_comparison.png | figure | Generated from Table 1. BM25 and Date-filter have higher broad Hit@5; ChronoRAG is strongest on temporal-validity diagnostics. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig3_layer2a_retrieval_comparison.svg | figure | Generated from Table 1. BM25 and Date-filter have higher broad Hit@5; ChronoRAG is strongest on temporal-validity diagnostics. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig4_temporal_validity_diagnostics.png | figure | Generated from Table 1 and ablation artifact. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig4_temporal_validity_diagnostics.svg | figure | Generated from Table 1 and ablation artifact. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig5_score_only_ablation.png | figure | Score-only retrieval maximizes broad Hit@5 but damages temporal-validity metrics. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig5_score_only_ablation.svg | figure | Score-only retrieval maximizes broad Hit@5 but damages temporal-validity metrics. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig6_qa50_llm_post_filtering.png | figure | Standard retrieval + LLM temporal prompting reaches 32-40% strict pass; ChronoRAG reaches 70% strict pass in the answer-level setting. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig6_qa50_llm_post_filtering.svg | figure | Standard retrieval + LLM temporal prompting reaches 32-40% strict pass; ChronoRAG reaches 70% strict pass in the answer-level setting. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig7_injection_fairness_split.png | figure | Pre-injection is the fair retrieval-availability comparison. Post-injection measures answer behavior when expected evidence is available. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig7_injection_fairness_split.svg | figure | Pre-injection is the fair retrieval-availability comparison. Post-injection measures answer behavior when expected evidence is available. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig8_topk_sensitivity.png | figure | Generated from top-k sensitivity artifact. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig8_topk_sensitivity.svg | figure | Generated from top-k sensitivity artifact. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig9_temporal_feature_heatmap_not_available.md | figure-note | Feature heatmap not generated because candidate-level traces are unavailable. | artifact schema inspection |
| rpartifacts/paper/one_query_trace.md | paper-note | Real one-query trace from Layer 2A artifacts. | stdcomp case reports |
| rpartifacts/figures/fig10_one_query_trace.png | figure | Generated from real Layer 2A case reports. | generated from existing artifacts or schematic |
| rpartifacts/figures/fig10_one_query_trace.svg | figure | Generated from real Layer 2A case reports. | generated from existing artifacts or schematic |
| rpartifacts/tables/table1_layer2a_retrieval_comparison.md | table | Table 1. Layer 2A Retrieval Comparison | docs/paper_assets/table1_layer2a_retrieval_standard_comparison.csv |
| rpartifacts/tables/table2_ablation_comparison.md | table | Table 2. Ablation Comparison | docs/paper_assets/table2_layer2a_ablation_comparison.csv |
| rpartifacts/tables/table3_qa50_llm_post_filtering.md | table | Table 3. QA50 LLM Post-Filtering Baselines | docs/paper_assets/table3_qa50_llm_post_filter_baselines.csv |
| rpartifacts/tables/table4_answer_level_comparison.md | table | Table 4. QA50 Answer-Level Comparison | docs/paper_assets/table4_qa50_answer_level_comparison.csv |
| rpartifacts/tables/table5_score_only_ablation.md | table | Table 5. Score-Only Ablation | docs/paper_assets/table2_layer2a_ablation_comparison.csv |
| rpartifacts/tables/table6_topk_sensitivity.md | table | Table 6. Top-k Sensitivity | docs/paper_assets/topk_sensitivity.csv |
| rpartifacts/github/readme_results_section.md | github-snippet | Copy-paste README result summary. | generated tables |
| rpartifacts/github/readme_figures_section.md | github-snippet | Copy-paste README figure section. | generated figures |
| rpartifacts/github/readme_badges_or_links.md | github-snippet | Copy-paste links and badge text. | artifact index |
| rpartifacts/linkedin/linkedin_post_short.md | linkedin | Short launch post. | artifact summary |
| rpartifacts/linkedin/linkedin_post_long.md | linkedin | Long launch post. | artifact summary |
| rpartifacts/linkedin/linkedin_carousel_plan.md | linkedin | Carousel plan. | artifact summary |
| rpartifacts/paper/paper_figure_plan.md | paper-note | Paper figure plan. | generated figures |
| rpartifacts/paper/paper_result_narrative.md | paper-note | Paper result narrative. | generated tables |
| rpartifacts/paper/paper_limitations_insert.md | paper-note | Paper limitations insert. | approved limitations |
| rpartifacts/paper/paper_metric_definitions_insert.md | paper-note | Metric definitions insert. | approved metrics |
| rpartifacts/paper/paper_dataset_protocol_insert.md | paper-note | Dataset protocol insert. | approved protocol |
| rpartifacts/paper/paper_threats_to_validity_insert.md | paper-note | Threats to validity insert. | approved limitations |
| rpartifacts/README.md | index | Research artifact package index. | generated artifacts |

Interpretation: this table lists generated files and their source basis.

Result type: artifact manifest.
