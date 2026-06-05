# Layer 2B Results: chronorag_full

This is a controlled Layer 2B manual-QA runner report, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Method: `chronorag_full`
- Cases: 50
- Top-k: 5
- Result suffix: `layer2b_full50_vertex_final`
- Provider errors: 0
- JSON/schema failures: 0
- Expected evidence retrieved before injection: 0 / 50
- Expected evidence available to model after injection: 50 / 50
- Injected expected evidence rows: 21
- Cases with injected expected evidence: 18
- Expected evidence cited: 49 / 50
- Valid time correctness: 41 / 50
- Behavior correctness: 47 / 50
- Overall contract pass: 38 / 50

Expected-evidence injection was used for at least one case. Injected evidence is gold evidence made available to evaluate answer synthesis with the right evidence in context; it must not be interpreted as retrieval quality.

| Question ID | Type | Expected Behavior | Status | Retrieved Expected Evidence | Available To Model | Injected Evidence IDs | Contract Pass | Failure Reasons |
|---|---|---|---|---:|---:|---|---:|---|
| l2b_manual_001 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-10610 | yes |  |
| l2b_manual_002 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-14506 | yes |  |
| l2b_manual_003 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-15899 | yes |  |
| l2b_manual_004 | wrong_time_trap | answer | completed | yes | yes | l2:federal_register:2025-16484 | yes |  |
| l2b_manual_005 | broad_window_trap | answer | completed | yes | yes | l2:federal_register:2025-18700 | yes |  |
| l2b_manual_006 | partial_or_insufficient | partial | completed | yes | yes | l2:federal_register:2025-16192 | yes |  |
| l2b_manual_007 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-20134 | yes |  |
| l2b_manual_008 | transaction_valid_time_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_009 | comparison | answer | completed | yes | yes | l2:federal_register:2025-16482, l2:federal_register:2025-16484 | no | valid_time_present |
| l2b_manual_010 | ambiguous_time | answer | completed | yes | yes |  | no | valid_time_present |
| l2b_manual_011 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_012 | wrong_time_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_013 | comparison | compare | completed | yes | yes |  | yes |  |
| l2b_manual_014 | exact_lookup | answer | completed | yes | yes | l2:github_releases:transformers:213909788 | no | answer_behavior_correct, conflict_warning_correct |
| l2b_manual_015 | chronology | answer | completed | yes | yes | l2:github_releases:transformers:213909788 | yes |  |
| l2b_manual_016 | broad_window_trap | answer | completed | yes | yes |  | no | answer_behavior_correct |
| l2b_manual_017 | partial_or_insufficient | partial | completed | yes | yes |  | yes |  |
| l2b_manual_018 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_019 | comparison | compare | completed | yes | yes |  | yes |  |
| l2b_manual_020 | wrong_time_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_021 | comparison | compare | completed | yes | yes |  | yes |  |
| l2b_manual_022 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_023 | chronology | compare | completed | yes | yes |  | yes |  |
| l2b_manual_024 | ambiguous_time | partial | completed | yes | yes |  | no | expected_evidence_cited, valid_time_present |
| l2b_manual_025 | broad_window_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_026 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_027 | comparison | compare | completed | yes | yes |  | yes |  |
| l2b_manual_028 | wrong_time_trap | answer | completed | yes | yes | l2:macro_fred:dgs10:1972-05-03 | no | valid_time_present |
| l2b_manual_029 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_030 | chronology | compare | completed | yes | yes | l2:macro_fred:dgs10:1998-07-29 | yes |  |
| l2b_manual_031 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_032 | comparison | compare | completed | yes | yes |  | yes |  |
| l2b_manual_033 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_034 | wrong_time_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_035 | comparison | compare | completed | yes | yes | l2:market_index:nasdaqcom:1985-11-04 | yes |  |
| l2b_manual_036 | chronology | answer | completed | yes | yes |  | yes |  |
| l2b_manual_037 | exact_lookup | answer | completed | yes | yes |  | yes |  |
| l2b_manual_038 | broad_window_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_039 | ambiguous_time | partial | completed | yes | yes |  | yes |  |
| l2b_manual_040 | comparison | compare | completed | yes | yes | l2:market_index:djia:2016-10-14 | yes |  |
| l2b_manual_041 | transaction_valid_time_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_042 | exact_lookup | answer | completed | yes | yes |  | no | valid_time_present |
| l2b_manual_043 | wrong_time_trap | answer | completed | yes | yes | l2:sec_submissions:msft:0000789019-25-000110 | no | valid_time_present |
| l2b_manual_044 | comparison | compare | completed | yes | yes |  | yes |  |
| l2b_manual_045 | transaction_valid_time_trap | answer | completed | yes | yes |  | yes |  |
| l2b_manual_046 | exact_lookup | answer | completed | yes | yes |  | no | valid_time_present |
| l2b_manual_047 | partial_or_insufficient | partial | completed | yes | yes | l2:sec_submissions:googl:0001950047-24-001547 | no | valid_time_present |
| l2b_manual_048 | chronology | answer | completed | yes | yes | l2:sec_submissions:googl:0001950047-25-005059, l2:sec_submissions:googl:0001950047-25-007988 | yes |  |
| l2b_manual_049 | wrong_time_trap | answer | completed | yes | yes |  | no | valid_time_present |
| l2b_manual_050 | ambiguous_time | partial | completed | yes | yes | l2:sec_submissions:nvda:0001921094-25-000014, l2:sec_submissions:nvda:0001921094-25-001250 | no | answer_behavior_correct, partial_refusal_correct |
