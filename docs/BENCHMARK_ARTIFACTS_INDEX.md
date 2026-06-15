# Benchmark Artifacts Index

This index maps the repository's benchmark data, result artifacts, scripts,
paper tables, and figures to the paper evidence they support. It is an
inspection guide for existing artifacts only.

## Data Files

| Artifact | Role | Supports |
|---|---|---|
| [Layer 2A corpus](../benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl) | Fixed selected 5,000-row controlled corpus. SHA256 in stored table/runtime JSON: `fe0782eea177ccd1ac90ce21c730c8c69f65c8be388534bc141d3a01a6269287`. | Layer 2A retrieval, ablation, standard comparison, runtime, QA50 baselines |
| [Layer 2A questions](../benchmarks/layer2_crossdomain/data/layer2_questions.jsonl) | Fixed 200-question v3 retrieval benchmark. SHA256 in stored table/runtime JSON: `d8dcaf4e306fa7f3c8d3ccd02aeee7af5c03ce23250d2a47d470c2c7e5c98b7a`. | Table 1, Table 2, runtime table, Figures 3-5, 8, 10, 11, 15 |
| [QA50 manual cases](../benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl) | Fixed 50-case manual temporal QA benchmark. SHA256 in stored QA50 table JSON: `6e41ad8f6bd075060d15a14d175019316417656d8eaacd8f841999a2f9668727`. | Table 3, Table 4, Figures 6, 7, 11, 12 |
| [Layer 2A corpus sample](../benchmarks/layer2_crossdomain/data/layer2_corpus.sample.jsonl) | Small public schema/example sample. | Reader inspection |
| [Raw pool manifest](../benchmarks/layer2_crossdomain/data/raw_pool_manifest.json) | Records raw-pool scale, approximately 46,503 rows/items. | Dataset protocol and reproducibility notes |

## Layer 2A Result Artifacts

| Artifact | Role | Supports |
|---|---|---|
| [Layer 2A retrieval JSON](../benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json) | Stored retrieval-only v3 evaluation. | Final Layer 2A result boundary |
| [Layer 2A retrieval report](../benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md) | Human-readable retrieval-only report. | Final Layer 2A result boundary |
| [Layer 2A ablation JSON](../benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json) | Stored v3 ablation results. | Table 2 |
| [Layer 2A ablation report](../benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md) | Human-readable ablation report. | Table 2 |
| [Standard comparison JSON](../chronorag/stdcomp/results/stdcomp_layer2a_comparison.json) | Combined BM25, Dense-only, Date-filter RAG, Metadata Temporal RAG, and ChronoRAG Full metrics. | Table 1, Figure 3, Figure 10, Figure 15 |
| [Standard comparison CSV](../chronorag/stdcomp/results/stdcomp_layer2a_comparison.csv) | CSV copy of standard comparison. | Table 1 |
| [BM25 metrics](../chronorag/stdcomp/results/bm25_metrics.json) | Standard BM25 retrieval metrics. | Table 1 |
| [Dense-only metrics](../chronorag/stdcomp/results/dense_only_metrics.json) | Standard dense retrieval metrics. | Table 1 |
| [Date-filter metrics](../chronorag/stdcomp/results/date_filter_rag_metrics.json) | Naive date-filter retrieval metrics. | Table 1 |
| [Layer 2A runtime JSON](../chronorag/stdcomp/results/layer2a_runtime_retrieval_200.json) | Full 200-question retrieval-only runtime measurement. | Runtime table, Figure 15 |

## QA50 Result Artifacts

| Artifact | Role | Supports |
|---|---|---|
| [QA50 answer-generation report](../benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.md) | Stored ChronoRAG Full answer-generation report. | Table 4 |
| [QA50 answer-generation JSONL](../benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl) | Stored ChronoRAG Full answer-generation outputs. | Table 4 |
| [QA50 judge report](../benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.md) | Stored QA50 judge report. | Table 4 |
| [QA50 judge JSONL](../benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.jsonl) | Stored QA50 judge outputs. | Table 4 |
| [QA50 manual audit](../benchmarks/layer2_crossdomain/results/layer2b_full50_manual_audit.md) | Human audit of validator-strictness cases. | QA50 interpretation boundary |
| [BM25 + LLM QA50 metrics](../chronorag/stdcomp/results/qa50_llm_baselines/bm25_llm_qa50_metrics.json) | Stored standard retrieval + LLM baseline metrics. | Table 3, Table 4, Figure 6, Figure 12 |
| [Dense-only + LLM QA50 metrics](../chronorag/stdcomp/results/qa50_llm_baselines/dense_llm_qa50_metrics.json) | Stored standard retrieval + LLM baseline metrics. | Table 3, Table 4, Figure 6, Figure 12 |
| [Date-filter RAG + LLM QA50 metrics](../chronorag/stdcomp/results/qa50_llm_baselines/date_filter_llm_qa50_metrics.json) | Stored standard retrieval + LLM baseline metrics. | Table 3, Table 4, Figure 6, Figure 12 |
| [QA50 extracted values](../chronorag/stdcomp/results/paper_tables/chronorag_qa50_extracted_values.json) | Existing extracted ChronoRAG QA50 table values. | Table 4, Figure 7 |

## Paper Tables

| Artifact | Role | Source |
|---|---|---|
| [Table index](paper_assets/chrono_tables_index.md) | Paper table inventory. | Existing result artifacts |
| [Table 1: Layer 2A retrieval comparison](paper_assets/table1_layer2a_retrieval_standard_comparison.md) | Paper-ready standard retrieval table. | `chronorag/stdcomp/results/stdcomp_layer2a_comparison.json` |
| [Table 1 with Wilson CI](paper_assets/table1_layer2a_retrieval_standard_comparison_with_ci.md) | Wilson interval variant. | Table 1 metrics |
| [Table 2: Layer 2A ablation](paper_assets/table2_layer2a_ablation_comparison.md) | Compact ablation table. | Stored ablation artifacts |
| [Table 2 full: Layer 2A ablation](paper_assets/table2_layer2a_full_ablation_comparison.md) | Full ablation table. | `layer2_ablation_v3_ablation200` artifacts |
| [Runtime table](paper_assets/table_runtime_layer2a_retrieval.md) | Paper-ready retrieval runtime table. | `layer2a_runtime_retrieval_200.json` |
| [Table 3: QA50 LLM baselines](paper_assets/table3_qa50_llm_post_filter_baselines.md) | QA50 standard retrieval + LLM post-filtering. | `chronorag/stdcomp/results/qa50_llm_baselines/` |
| [Table 4: QA50 answer-level comparison](paper_assets/table4_qa50_answer_level_comparison.md) | QA50 answer-level comparison. | QA50 baseline and ChronoRAG artifacts |
| [Top-k sensitivity](paper_assets/topk_sensitivity.md) | Retrieval-only top-k sensitivity. | `chronorag/stdcomp/results/sensitivity/topk_sensitivity.json` |

## Research Artifact Package

| Artifact | Role | Supports |
|---|---|---|
| [Research artifact index](../rpartifacts/README.md) | Figure/table/snippet package index. | Public review |
| [Artifact manifest table](../rpartifacts/tables/table7_artifact_manifest.md) | Generated artifact manifest. | Artifact provenance |
| [Artifact manifest JSON](../rpartifacts/data/artifact_manifest.json) | Machine-readable artifact manifest. | Artifact provenance |
| [Source artifact manifest JSON](../rpartifacts/data/source_artifact_manifest.json) | Source existence manifest. | Artifact provenance |
| [Temporal feature trace JSONL](../rpartifacts/data/temporal_feature_trace.jsonl) | Retrieval-only candidate trace. | Figure 9 |
| [Temporal feature trace CSV](../rpartifacts/data/temporal_feature_trace.csv) | Tabular trace export. | Figure 9 |

## Figures

| Figure | Artifact | Source basis |
|---|---|---|
| Figure 1 | [Temporal misgrounding concept](../rpartifacts/figures/fig1_temporal_misgrounding_concept.png) | Schematic |
| Figure 2 | [ChronoRAG architecture](../rpartifacts/figures/fig2_chronorag_architecture.png) | Schematic |
| Figure 3 | [Layer 2A retrieval comparison](../rpartifacts/figures/fig3_layer2a_retrieval_comparison.png) | Table 1 CSV |
| Figure 4 | [Temporal-validity diagnostics](../rpartifacts/figures/fig4_temporal_validity_diagnostics.png) | Table 1 and Table 2 CSVs |
| Figure 5 | [Score-only ablation](../rpartifacts/figures/fig5_score_only_ablation.png) | Table 2 CSV |
| Figure 6 | [QA50 LLM post-filtering](../rpartifacts/figures/fig6_qa50_llm_post_filtering.png) | Table 3 and Table 4 CSVs |
| Figure 7 | [Pre/post injection fairness split](../rpartifacts/figures/fig7_injection_fairness_split.png) | QA50 extracted values |
| Figure 8 | [Top-k sensitivity](../rpartifacts/figures/fig8_topk_sensitivity.png) | Top-k sensitivity CSV |
| Figure 9 | [Temporal feature heatmap](../rpartifacts/figures/fig9_temporal_feature_heatmap.png) | Retrieval-only temporal feature trace |
| Figure 10 | [One-query retrieval trace](../rpartifacts/figures/fig10_one_query_trace.png) | Layer 2A ranked output artifacts |
| Figure 11 | [Metric family summary](../rpartifacts/figures/fig11_metric_family_summary.png) | Layer 2A and QA50 tables |
| Figure 12 | [QA50 failure decomposition](../rpartifacts/figures/fig12_qa50_failure_decomposition.png) | QA50 baseline output JSONL files |
| Figure 13 | [Claim boundary](../rpartifacts/figures/fig13_claim_boundary.png) | Schematic |
| Figure 14 | [Applications map](../rpartifacts/figures/fig14_applications_map.png) | Schematic |
| Figure 15 | [Runtime-quality tradeoff](../rpartifacts/figures/fig15_runtime_quality_tradeoff.png) | Runtime table and Table 1 CSV |

## Scripts

| Script | Role |
|---|---|
| [build_layer2_corpus.py](../benchmarks/layer2_crossdomain/build_layer2_corpus.py) | Builds the selected Layer 2A corpus from configured raw inputs. |
| [generate_layer2_questions_v3.py](../benchmarks/layer2_crossdomain/generate_layer2_questions_v3.py) | Generates aligned Layer 2A v3 questions. |
| [validate_layer2_dataset.py](../benchmarks/layer2_crossdomain/validate_layer2_dataset.py) | Validates Layer 2A data/question contracts. |
| [run_layer2_comparison.py](../benchmarks/layer2_crossdomain/run_layer2_comparison.py) | Runs retrieval-only Layer 2A method comparison. |
| [evaluate_retrieval_only.py](../benchmarks/layer2_crossdomain/evaluate_retrieval_only.py) | Scores selected evidence IDs for retrieval-only outputs. |
| [run_layer2_ablations.py](../benchmarks/layer2_crossdomain/run_layer2_ablations.py) | Runs Layer 2A ablation variants. |
| [evaluate_stdcomp.py](../chronorag/stdcomp/evaluate_stdcomp.py) | Runs standard retrieval comparison baselines and combined table generation. |
| [evaluate_qa50_llm_baselines.py](../chronorag/stdcomp/evaluate_qa50_llm_baselines.py) | Runs QA50 standard retrieval + LLM baselines; provider-backed, not a routine cleanup command. |
| [add_wilson_ci_to_paper_tables.py](../chronorag/stdcomp/add_wilson_ci_to_paper_tables.py) | Adds Wilson interval variants to stored paper tables. |
| [generate_research_artifacts.py](../rpartifacts/generate_research_artifacts.py) | Regenerates the research artifact package from stored result artifacts. |
| [export_temporal_feature_trace.py](../rpartifacts/export_temporal_feature_trace.py) | Exports retrieval-only temporal feature traces for Figure 9. |

## Cleanup Boundary

Ignored local smoke/dry/debug files, caches, virtual environments, and OS junk
are not part of the public artifact boundary. If a file is tracked, referenced
from this index, or used as a source for a paper table/figure, it should not be
removed during repository cleanup.
