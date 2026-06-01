# Layer 2 Results: chronorag_full

This is an optional LLM-judge validation report, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Validator: `llm_judge`
- Corpus rows: 5000
- Questions: 200
- Top-k: 5
- Scored cases: 32
- Provider/infrastructure failures: 7
- Judge parse failures: 95
- Judge provider failures: 4
- Judge retry attempts: 4

| Metric | Score |
|---|---:|
| Judge Overall Pass | 0.00 |
| Strict Overall Pass | 0.00 |
| Temporal Scope Correct | 0.00 |
| Factual Grounding | 0.00 |
| Behavior Justified | 0.00 |
| Transaction-Time Clean | 0.00 |
| No Overconfidence | 0.00 |
| Behavior Label Accuracy | 0.84 |
| Citation Grounding Accuracy | 1.00 |
| Schema Field Presence | 1.00 |
| Judge Parse Failures | 95 |
| Judge Provider Failures | 4 |
| Judge Retry Attempts | 4 |

## Failure Analysis

- `l2q:0000:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=1
- `l2q:0001:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0002:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0003:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0004:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0005:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=1
- `l2q:0006:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=1
- `l2q:0007:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0008:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0009:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0010:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0011:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0012:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0013:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0014:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0015:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0016:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0017:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0018:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0019:exact_valid_time_retrieval`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0020:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0021:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0022:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=behavior_label_match; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0023:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0024:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=behavior_label_match; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0025:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=behavior_label_match; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0026:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0027:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0028:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0029:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0030:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0031:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=behavior_label_match; judge_parse_failures=2; judge_provider_failures=0
- `l2q:0032:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0033:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0034:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=behavior_label_match; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0035:same_entity_wrong_year_trap`: judge_overall=None; strict=None; criteria_failed=none; diagnostics_failed=none; judge_parse_failures=0; judge_provider_failures=0
- `l2q:0036:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=1
- `l2q:0037:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0
- `l2q:0038:same_entity_wrong_year_trap`: judge_overall=False; strict=False; criteria_failed=temporal_scope_correct, factual_grounding, behavior_justified, transaction_time_clean, no_overconfidence; diagnostics_failed=none; judge_parse_failures=3; judge_provider_failures=0

| Case | Status | Judge Pass | Strict Pass | Criteria Passed | Diagnostics Failed |
|---|---|---:|---:|---:|---|
| l2q:0000:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0001:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0002:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0003:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0004:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0005:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0006:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0007:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0008:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0009:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0010:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0011:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0012:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0013:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0014:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0015:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0016:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0017:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0018:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0019:exact_valid_time_retrieval | completed | False | False | 0 |  |
| l2q:0020:same_entity_wrong_year_trap | completed | False | False | 0 |  |
| l2q:0021:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0022:same_entity_wrong_year_trap | completed | False | False | 0 | behavior_label_match |
| l2q:0023:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0024:same_entity_wrong_year_trap | completed | False | False | 0 | behavior_label_match |
| l2q:0025:same_entity_wrong_year_trap | completed | False | False | 0 | behavior_label_match |
| l2q:0026:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0027:same_entity_wrong_year_trap | completed | False | False | 0 |  |
| l2q:0028:same_entity_wrong_year_trap | completed | False | False | 0 |  |
| l2q:0029:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0030:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0031:same_entity_wrong_year_trap | completed | False | False | 0 | behavior_label_match |
| l2q:0032:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0033:same_entity_wrong_year_trap | completed | False | False | 0 |  |
| l2q:0034:same_entity_wrong_year_trap | completed | False | False | 0 | behavior_label_match |
| l2q:0035:same_entity_wrong_year_trap | provider_error | None | None | 0 |  |
| l2q:0036:same_entity_wrong_year_trap | completed | False | False | 0 |  |
| l2q:0037:same_entity_wrong_year_trap | completed | False | False | 0 |  |
| l2q:0038:same_entity_wrong_year_trap | completed | False | False | 0 |  |
