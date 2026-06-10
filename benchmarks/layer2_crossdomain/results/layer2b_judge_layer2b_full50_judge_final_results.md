# Layer 2B LLM Judge Results

This is a strict-but-fair Layer 2B answer-quality judge report, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Input answer results: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl`
- Cases: 50
- Result suffix: `layer2b_full50_judge_final`
- Mapping errors: 0
- Judge errors: 0
- Judge parse failures: 0
- Judge provider failures: 0
- Judge retry attempts: 0
- Deterministic hard-contract pass: 38 / 50
- LLM judge pass: 38 / 50
- Combined pass: 35 / 50

| Question ID | Type | Expected Behavior | Status | Deterministic Pass | Judge Pass | Combined Pass | Severity | Failure Reasons |
|---|---|---|---|---:|---:|---:|---|---|
| l2b_manual_001 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_002 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_003 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_004 | wrong_time_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_005 | broad_window_trap | answer | completed | yes | no | no | major | semantic_answer_correct, reference_supported, evidence_grounded, no_hallucination, unsupported_claims, hallucination |
| l2b_manual_006 | partial_or_insufficient | partial | completed | yes | yes | yes | pass |  |
| l2b_manual_007 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_008 | transaction_valid_time_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_009 | comparison | answer | completed | no | no | no | minor | valid_time_correct |
| l2b_manual_010 | ambiguous_time | answer | completed | no | no | no | major | valid_time_correct |
| l2b_manual_011 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_012 | wrong_time_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_013 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_014 | exact_lookup | answer | completed | no | no | no | major | behavior_correct, conflict_handling_correct |
| l2b_manual_015 | chronology | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_016 | broad_window_trap | answer | completed | no | no | no | minor | behavior_correct |
| l2b_manual_017 | partial_or_insufficient | partial | completed | yes | yes | yes | pass |  |
| l2b_manual_018 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_019 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_020 | wrong_time_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_021 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_022 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_023 | chronology | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_024 | ambiguous_time | partial | completed | no | no | no | major | semantic_answer_correct, reference_supported, expected_evidence_used, valid_time_correct |
| l2b_manual_025 | broad_window_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_026 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_027 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_028 | wrong_time_trap | answer | completed | no | no | no | major | valid_time_correct, valid_time_used_incomplete |
| l2b_manual_029 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_030 | chronology | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_031 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_032 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_033 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_034 | wrong_time_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_035 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_036 | chronology | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_037 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_038 | broad_window_trap | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_039 | ambiguous_time | partial | completed | yes | yes | yes | pass |  |
| l2b_manual_040 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_041 | transaction_valid_time_trap | answer | completed | yes | no | no | major | valid_time_correct |
| l2b_manual_042 | exact_lookup | answer | completed | no | no | no | critical | valid_time_correct, valid_time_incorrect |
| l2b_manual_043 | wrong_time_trap | answer | completed | no | yes | no | pass |  |
| l2b_manual_044 | comparison | compare | completed | yes | yes | yes | pass |  |
| l2b_manual_045 | transaction_valid_time_trap | answer | completed | yes | no | no | minor | valid_time_correct |
| l2b_manual_046 | exact_lookup | answer | completed | no | no | no | minor | valid_time_correct |
| l2b_manual_047 | partial_or_insufficient | partial | completed | no | yes | no | pass |  |
| l2b_manual_048 | chronology | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_049 | wrong_time_trap | answer | completed | no | yes | no | pass |  |
| l2b_manual_050 | ambiguous_time | partial | completed | no | no | no | major | behavior_correct, partial_refusal_correct |
