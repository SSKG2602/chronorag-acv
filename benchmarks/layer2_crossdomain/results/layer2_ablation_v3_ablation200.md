# Layer 2A v3 Ablation Report

Dry-run retrieval-only ablation report. No Vertex, no answer-quality scoring, no SOTA claim.

This dry-run report scores selected evidence IDs only. It does not call Vertex and does not evaluate generated answer quality.

## Overall

| Variant | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Delta vs chronorag_full |
|---|---:|---:|---:|---:|---:|---:|
| metadata_temporal_rag | 200 | 0.6900 | 0.8600 | 0.6950 | 0.4813 | -0.4813 |
| chronorag_score_only | 200 | 0.8150 | 0.9850 | 0.6500 | 0.5625 | -0.4000 |
| chronorag_no_tcc | 200 | 0.8350 | 0.8950 | 0.9950 | 0.9625 | 0.0000 |
| chronorag_no_temporal_precision | 200 | 0.7500 | 0.8500 | 0.9450 | 0.7500 | -0.2125 |
| chronorag_no_transaction_role | 200 | 0.8250 | 0.8950 | 0.9950 | 0.9625 | 0.0000 |
| chronorag_no_source_metric | 200 | 0.8300 | 0.8900 | 1.0000 | 0.9688 | 0.0062 |
| chronorag_no_slot_assembler | 200 | 0.8300 | 0.8900 | 0.8150 | 0.7750 | -0.1875 |
| chronorag_full | 200 | 0.8250 | 0.8950 | 0.9950 | 0.9625 | 0.0000 |

## Per-Category

| Variant | Category | Cases | Category primary pass | Delta vs chronorag_full |
|---|---|---:|---:|---:|
| metadata_temporal_rag | ambiguous_time_query | 20 | n/a | 0.0000 |
| metadata_temporal_rag | cross_domain_temporal_comparison | 20 | 0.0500 | -0.7500 |
| metadata_temporal_rag | exact_valid_time_retrieval | 20 | 0.4000 | -0.6000 |
| metadata_temporal_rag | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| metadata_temporal_rag | metric_specific_exact_time | 20 | 0.9000 | -0.1000 |
| metadata_temporal_rag | multi_slot_temporal_coverage | 20 | 0.0000 | -0.9500 |
| metadata_temporal_rag | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| metadata_temporal_rag | same_entity_wrong_time_trap | 20 | 0.1000 | -0.8500 |
| metadata_temporal_rag | source_specific_exact_time | 20 | 0.4000 | -0.6000 |
| metadata_temporal_rag | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_score_only | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_score_only | cross_domain_temporal_comparison | 20 | 0.5500 | -0.2500 |
| chronorag_score_only | exact_valid_time_retrieval | 20 | 0.3000 | -0.7000 |
| chronorag_score_only | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_score_only | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_score_only | multi_slot_temporal_coverage | 20 | 0.2000 | -0.7500 |
| chronorag_score_only | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_score_only | same_entity_wrong_time_trap | 20 | 0.3000 | -0.6500 |
| chronorag_score_only | source_specific_exact_time | 20 | 0.1500 | -0.8500 |
| chronorag_score_only | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_tcc | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_no_tcc | cross_domain_temporal_comparison | 20 | 0.8000 | 0.0000 |
| chronorag_no_tcc | exact_valid_time_retrieval | 20 | 1.0000 | 0.0000 |
| chronorag_no_tcc | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_no_tcc | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_tcc | multi_slot_temporal_coverage | 20 | 0.9500 | 0.0000 |
| chronorag_no_tcc | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_no_tcc | same_entity_wrong_time_trap | 20 | 0.9500 | 0.0000 |
| chronorag_no_tcc | source_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_tcc | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_temporal_precision | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_no_temporal_precision | cross_domain_temporal_comparison | 20 | 0.5000 | -0.3000 |
| chronorag_no_temporal_precision | exact_valid_time_retrieval | 20 | 1.0000 | 0.0000 |
| chronorag_no_temporal_precision | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_no_temporal_precision | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_temporal_precision | multi_slot_temporal_coverage | 20 | 0.5000 | -0.4500 |
| chronorag_no_temporal_precision | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_no_temporal_precision | same_entity_wrong_time_trap | 20 | 0.0000 | -0.9500 |
| chronorag_no_temporal_precision | source_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_temporal_precision | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_transaction_role | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_no_transaction_role | cross_domain_temporal_comparison | 20 | 0.8000 | 0.0000 |
| chronorag_no_transaction_role | exact_valid_time_retrieval | 20 | 1.0000 | 0.0000 |
| chronorag_no_transaction_role | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_no_transaction_role | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_transaction_role | multi_slot_temporal_coverage | 20 | 0.9500 | 0.0000 |
| chronorag_no_transaction_role | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_no_transaction_role | same_entity_wrong_time_trap | 20 | 0.9500 | 0.0000 |
| chronorag_no_transaction_role | source_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_transaction_role | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_source_metric | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_no_source_metric | cross_domain_temporal_comparison | 20 | 0.8000 | 0.0000 |
| chronorag_no_source_metric | exact_valid_time_retrieval | 20 | 1.0000 | 0.0000 |
| chronorag_no_source_metric | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_no_source_metric | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_source_metric | multi_slot_temporal_coverage | 20 | 0.9500 | 0.0000 |
| chronorag_no_source_metric | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_no_source_metric | same_entity_wrong_time_trap | 20 | 1.0000 | 0.0500 |
| chronorag_no_source_metric | source_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_source_metric | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_slot_assembler | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_no_slot_assembler | cross_domain_temporal_comparison | 20 | 0.5500 | -0.2500 |
| chronorag_no_slot_assembler | exact_valid_time_retrieval | 20 | 1.0000 | 0.0000 |
| chronorag_no_slot_assembler | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_no_slot_assembler | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_no_slot_assembler | multi_slot_temporal_coverage | 20 | 0.1500 | -0.8000 |
| chronorag_no_slot_assembler | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_no_slot_assembler | same_entity_wrong_time_trap | 20 | 1.0000 | 0.0500 |
| chronorag_no_slot_assembler | source_specific_exact_time | 20 | 0.5000 | -0.5000 |
| chronorag_no_slot_assembler | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |
| chronorag_full | ambiguous_time_query | 20 | n/a | 0.0000 |
| chronorag_full | cross_domain_temporal_comparison | 20 | 0.8000 | 0.0000 |
| chronorag_full | exact_valid_time_retrieval | 20 | 1.0000 | 0.0000 |
| chronorag_full | exact_vs_broad_temporal_preference | 20 | 1.0000 | 0.0000 |
| chronorag_full | metric_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_full | multi_slot_temporal_coverage | 20 | 0.9500 | 0.0000 |
| chronorag_full | partial_or_insufficient_evidence | 20 | n/a | 0.0000 |
| chronorag_full | same_entity_wrong_time_trap | 20 | 0.9500 | 0.0000 |
| chronorag_full | source_specific_exact_time | 20 | 1.0000 | 0.0000 |
| chronorag_full | valid_time_vs_transaction_time | 20 | 1.0000 | 0.0000 |

## Component Interpretation

- chronorag_score_only: finalization components contribute beyond fused retrieval scoring in `same_entity_wrong_time_trap`.
- chronorag_score_only: `valid_time_vs_transaction_time` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_score_only: finalization components contribute beyond fused retrieval scoring in `cross_domain_temporal_comparison`.
- chronorag_no_tcc: `exact_valid_time_retrieval` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_tcc: `exact_vs_broad_temporal_preference` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_tcc: `multi_slot_temporal_coverage` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_temporal_precision: temporal precision contributes to exact-time ranking and wrong-time suppression in `same_entity_wrong_time_trap`.
- chronorag_no_temporal_precision: `exact_valid_time_retrieval` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_temporal_precision: `exact_vs_broad_temporal_preference` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_transaction_role: `valid_time_vs_transaction_time` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_source_metric: `source_specific_exact_time` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_source_metric: `metric_specific_exact_time` did not drop; this category may be explained by benchmark alignment or other components rather than the ablated component.
- chronorag_no_slot_assembler: slot assembler contributes to multi-slot evidence coverage in `multi_slot_temporal_coverage`.
- chronorag_no_slot_assembler: slot assembler contributes to multi-slot evidence coverage in `cross_domain_temporal_comparison`.

## Boundary

- This is a controlled Layer 2A retrieval-only ablation, not a SOTA or publication-grade claim.
- Dry-run answer placeholders are not answer-quality results.
- Layer 2B, active embeddings, and Vertex execution are intentionally out of scope for this run.
