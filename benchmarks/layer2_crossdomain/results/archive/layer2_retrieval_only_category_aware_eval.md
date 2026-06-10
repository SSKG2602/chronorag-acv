# Layer 2 Retrieval-Only Evaluation

Retrieval-only scoring is diagnostic. Generic Hit@k is retained for visibility, but category-specific metrics are the meaningful checks for Layer 2 temporal behavior. This is not a SOTA or publication-grade proof metric.

| Method | Benchmark cases | Result rows | Evaluated | Skipped | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Embedding |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| chronorag_full | 200 | 200 | 200 | 0 | 0.27 | 0.50 | 0.92 | 0.42 | BAAI/bge-base-en-v1.5 / 768 |
| metadata_temporal_rag | 200 | 200 | 200 | 0 | 0.31 | 0.48 | 0.94 | 0.33 | BAAI/bge-small-en-v1.5 / 384 |

## chronorag_full Category Breakdown

| Category | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Main diagnostics |
|---|---:|---:|---:|---:|---:|---|
| ambiguous_time_query | 20 | 0.00 | 0.10 | 1.00 | n/a | ambiguity_evidence_hit@5=0.10; ambiguity_forbidden_absent@5=1.00; behavior_target_clarify=1.00 |
| broad_window_distractor | 20 | 0.15 | 0.50 | 1.00 | 0.50 | narrow_or_exact_hit@5=0.50; broad_window_forbidden_absent@5=1.00 |
| conflict_detection | 20 | 0.10 | 0.35 | 1.00 | 0.00 | conflict_side_coverage@5=0.00 |
| cross_domain_temporal_comparison | 20 | 1.00 | 1.00 | 1.00 | 0.35 | both_side_coverage@5=0.35 |
| exact_valid_time_retrieval | 20 | 0.95 | 1.00 | 0.80 | 0.95 | expected_hit@1=0.95; expected_hit@5=1.00 |
| metric_specific_query | 20 | 0.15 | 0.40 | 0.95 | 0.35 | metric_temporal_hit@5=0.40; metric_forbidden_absent@5=0.95 |
| partial_or_insufficient_evidence | 20 | 0.00 | 0.05 | 1.00 | n/a | behavior_target_partial_or_refuse=1.00; fallback_expected_hit@5=0.05; fallback_forbidden_absent@5=1.00 |
| same_entity_wrong_year_trap | 20 | 0.00 | 0.40 | 0.50 | 0.00 | target_year_hit@5=0.40; wrong_year_forbidden_absent@5=0.50 |
| source_specific_temporal_query | 20 | 0.15 | 0.50 | 1.00 | 0.50 | source_temporal_hit@5=0.50; source_forbidden_absent@5=1.00 |
| transaction_time_vs_valid_time | 20 | 0.20 | 0.70 | 0.90 | 0.70 | valid_time_hit@5=0.70; transaction_forbidden_absent@5=0.90 |

### Warnings

| Warning | Count |
|---|---:|
| behavior_target_category_not_primary_retrieval_pass | 40 |
| malformed_wrong_year_question | 14 |
| synthetic_conflict_ids_present_in_key | 20 |

## metadata_temporal_rag Category Breakdown

| Category | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass | Main diagnostics |
|---|---:|---:|---:|---:|---:|---|
| ambiguous_time_query | 20 | 0.10 | 0.20 | 1.00 | n/a | ambiguity_evidence_hit@5=0.20; ambiguity_forbidden_absent@5=1.00; behavior_target_clarify=1.00 |
| broad_window_distractor | 20 | 0.20 | 0.50 | 1.00 | 0.50 | narrow_or_exact_hit@5=0.50; broad_window_forbidden_absent@5=1.00 |
| conflict_detection | 20 | 0.20 | 0.50 | 1.00 | 0.00 | conflict_side_coverage@5=0.00 |
| cross_domain_temporal_comparison | 20 | 1.00 | 1.00 | 1.00 | 0.00 | both_side_coverage@5=0.00 |
| exact_valid_time_retrieval | 20 | 0.95 | 1.00 | 0.85 | 0.95 | expected_hit@1=0.95; expected_hit@5=1.00 |
| metric_specific_query | 20 | 0.20 | 0.50 | 0.95 | 0.45 | metric_temporal_hit@5=0.50; metric_forbidden_absent@5=0.95 |
| partial_or_insufficient_evidence | 20 | 0.00 | 0.00 | 1.00 | n/a | behavior_target_partial_or_refuse=1.00; fallback_expected_hit@5=0.00; fallback_forbidden_absent@5=1.00 |
| same_entity_wrong_year_trap | 20 | 0.25 | 0.60 | 0.60 | 0.20 | target_year_hit@5=0.60; wrong_year_forbidden_absent@5=0.60 |
| source_specific_temporal_query | 20 | 0.20 | 0.50 | 1.00 | 0.50 | source_temporal_hit@5=0.50; source_forbidden_absent@5=1.00 |
| transaction_time_vs_valid_time | 20 | 0.00 | 0.00 | 1.00 | 0.00 | valid_time_hit@5=0.00; transaction_forbidden_absent@5=1.00 |

### Warnings

| Warning | Count |
|---|---:|
| behavior_target_category_not_primary_retrieval_pass | 40 |
| malformed_wrong_year_question | 14 |
| synthetic_conflict_ids_present_in_key | 20 |

## Pairwise Same-Case Comparison: chronorag_full vs metadata_temporal_rag

Common evaluated cases: 200 / 200

| Metric | both_hit | left_only | right_only | neither | not_applicable | skipped/missing |
|---|---:|---:|---:|---:|---:|---:|
| Generic Hit@5 | 85 | 15 | 11 | 89 | 0 | 0 |
| Category primary pass | 45 | 22 | 7 | 86 | 40 | 0 |
| Forbidden absent@5 | 183 | 0 | 5 | 12 | 0 | 0 |

### Per-category pairwise deltas

| Category | Cases | Generic Hit@5 left_only/right_only | Primary pass left_only/right_only | Forbidden left_only/right_only |
|---|---:|---:|---:|---:|
| ambiguous_time_query | 20 | 0/2 | 0/0 | 0/0 |
| broad_window_distractor | 20 | 0/0 | 0/0 | 0/0 |
| conflict_detection | 20 | 0/3 | 0/0 | 0/0 |
| cross_domain_temporal_comparison | 20 | 0/0 | 7/0 | 0/0 |
| exact_valid_time_retrieval | 20 | 0/0 | 1/1 | 0/1 |
| metric_specific_query | 20 | 0/2 | 0/2 | 0/0 |
| partial_or_insufficient_evidence | 20 | 1/0 | 0/0 | 0/0 |
| same_entity_wrong_year_trap | 20 | 0/4 | 0/4 | 0/2 |
| source_specific_temporal_query | 20 | 0/0 | 0/0 | 0/0 |
| transaction_time_vs_valid_time | 20 | 14/0 | 14/0 | 0/2 |

### Pairwise warnings

- chronorag_full: behavior_target_category_not_primary_retrieval_pass=40
- chronorag_full: malformed_wrong_year_question=14
- chronorag_full: synthetic_conflict_ids_present_in_key=20
- metadata_temporal_rag: behavior_target_category_not_primary_retrieval_pass=40
- metadata_temporal_rag: malformed_wrong_year_question=14
- metadata_temporal_rag: synthetic_conflict_ids_present_in_key=20