# Paper Qualitative Cases

## Extraction Rule

The examples in this file are extracted from existing repository artifacts only.
No new examples or result claims are introduced.

## Case 1: Valid-Time Success

- Question/case ID: `l2q:0000:exact_valid_time_retrieval`
- Query/question text: Retrieve Federal Funds Rate effective federal funds rate on 1954-10-01.
- Selected evidence IDs: `l2:macro_fred:fedfunds:1954-10-01`
- Expected evidence IDs: `l2:macro_fred:fedfunds:1954-10-01`
- Source artifact path: `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`; question text from `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl`
- Short technical note: ChronoRAG selected the exact valid-time evidence for
  the requested date and left the listed nearby same-series dates outside the
  selected evidence set.

## Case 2: Transaction-Time Trap

- Question/case ID: `l2q:0040:valid_time_vs_transaction_time`
- Query/question text: For Alphabet Inc., retrieve 5 filing using valid time/report date/event date 2022-12-31, not filing/publication/transaction date 2023-02-13.
- Selected evidence IDs: `l2:sec_submissions:googl:0001209191-23-008786`, `l2:sec_submissions:googl:0001209191-23-008890`, `l2:sec_submissions:googl:0001209191-23-013907`, `l2:sec_submissions:nvda:0001045810-22-000011`, `l2:sec_submissions:googl:0001209191-23-019177`
- Expected evidence IDs: `l2:sec_submissions:googl:0001209191-23-008786`
- Source artifact path: `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`; question text from `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl`
- Short technical note: The query explicitly asks for report/event time and
  excludes the filing/publication/transaction date. The expected Alphabet
  evidence appears in the selected evidence set, and the retrieval card records
  a pass for the transaction-time category checks.

## Case 3: Forbidden-Date Exclusion

- Question/case ID: `l2q:0020:same_entity_wrong_time_trap`
- Query/question text: Retrieve macro_fred Federal Funds Rate effective federal funds rate on 1954-10-01, not 1956-02-01; exclude other same-entity same-metric dates.
- Selected evidence IDs: `l2:macro_fred:fedfunds:1954-10-01`
- Expected evidence IDs: `l2:macro_fred:fedfunds:1954-10-01`
- Source artifact path: `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`; question text from `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl`
- Short technical note: The selected set contains the target Federal Funds Rate
  row for 1954-10-01 and excludes the forbidden same-series rows for
  1956-02-01, 1957-06-01, and 1958-10-01.

## Case 4: Slot-Aware Comparison

- Question/case ID: `l2q:0060:cross_domain_temporal_comparison`
- Query/question text: Compare kubernetes release v1.30.6 on 2024-10-23 with Federal Funds Rate effective federal funds rate on 1954-10-01.
- Selected evidence IDs: `l2:github_releases:kubernetes:181360153`, `l2:macro_fred:fedfunds:1954-10-01`, `l2:github_releases:kubernetes:181442196`
- Expected evidence IDs: `l2:github_releases:kubernetes:181360153`, `l2:macro_fred:fedfunds:1954-10-01`
- Source artifact path: `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`; question text from `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl`
- Short technical note: The selected evidence set covers both required slots:
  the GitHub release evidence and the FRED macro evidence. The retrieval card
  records a pass for the cross-domain temporal comparison category.

## Case 5: Failure or Borderline Case

- Question/case ID: `l2b_manual_043`
- Query/question text: Did Microsoft file a Form 3 with the SEC on December 5, 2025?
- Selected evidence IDs: `l2:sec_submissions:nvda:0001045810-25-000070`, `l2:github_releases:transformers:212258171`, `l2:sec_submissions:msft:0000789019-25-000110`
- Expected evidence IDs: `l2:sec_submissions:msft:0000789019-25-000110`
- Source artifact path: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl`; manual decision from `benchmarks/layer2_crossdomain/results/layer2b_full50_manual_audit.md`
- Short technical note: The deterministic contract recorded
  `valid_time_present` as the failure reason, while the manual audit accepted
  the case as a correct Microsoft Form 3 filing/report-date distinction. This
  is a validator-strictness case rather than an added result.
