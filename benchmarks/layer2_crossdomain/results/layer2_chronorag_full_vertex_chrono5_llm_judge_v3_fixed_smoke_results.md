# Layer 2 Results: chronorag_full

This is an optional LLM-judge validation report, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Validator: `llm_judge`
- Corpus rows: 5000
- Questions: 5
- Top-k: 5
- Scored cases: 5
- Provider/infrastructure failures: 0
- Judge parse failures: 0
- Judge provider failures: 0
- Judge retry attempts: 0
- Judge infrastructure failure count: 0
- Judge scored runs: 5
- Judge unscored runs: 0

| Metric | Score |
|---|---:|
| Judge Overall Pass | 1.00 |
| Strict Overall Pass | 1.00 |
| Temporal Scope Correct | 1.00 |
| Factual Grounding | 1.00 |
| Behavior Justified | 1.00 |
| Transaction-Time Clean | 1.00 |
| No Overconfidence | 1.00 |
| Behavior Label Accuracy | 1.00 |
| Citation Grounding Accuracy | 1.00 |
| Schema Field Presence | 1.00 |
| Judge Infrastructure Failure Count | 0.00 |
| Judge Scored Runs | 5.00 |
| Judge Unscored Runs | 0.00 |
| Judge Parse Failures | 0 |
| Judge Provider Failures | 0 |
| Judge Retry Attempts | 0 |

## Failure Analysis

- No strict failures in this run.

| Case | Status | Judge Pass | Strict Pass | Criteria Passed | Diagnostics Failed |
|---|---|---:|---:|---:|---|
| l2q:0000:exact_valid_time_retrieval | completed | True | True | 5 |  |
| l2q:0001:exact_valid_time_retrieval | completed | True | True | 5 |  |
| l2q:0002:exact_valid_time_retrieval | completed | True | True | 5 |  |
| l2q:0003:exact_valid_time_retrieval | completed | True | True | 5 |  |
| l2q:0004:exact_valid_time_retrieval | completed | True | True | 5 |  |
