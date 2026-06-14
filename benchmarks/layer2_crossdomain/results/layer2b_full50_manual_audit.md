# Layer 2B Full-50 Manual Audit

Layer 2B evaluates answer synthesis and answer validation over the 50 manually
built temporal QA cases. Expected evidence was made available to the model
where needed, so this is not a retrieval-quality claim. The strict result uses
deterministic hard validation plus LLM judge.

| Metric | Score |
|---|---:|
| Cases | 50 |
| Deterministic hard-contract pass | 38 / 50 = 76% |
| LLM judge semantic pass | 48 / 50 = 96% |
| Strict combined pass | 35 / 50 = 70% |
| Manually accepted validator-strictness cases | 3 |
| Manual-audited acceptable pass | 41 / 50 = 82% |

The 70% result is the strict combined score. The 96% result is the LLM
semantic judge score. The 82% result is a secondary manual-audited
interpretation after accepting 3 cases where hard validation was stricter than
the answer quality deserved.

## Artifact Links

- Answer result Markdown: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.md`
- Judge result Markdown: `benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.md`
- Manual QA dataset: `benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl`
- Answer runner: `benchmarks/layer2_crossdomain/run_layer2b_manual_qa.py`
- Judge runner: `benchmarks/layer2_crossdomain/run_layer2b_judge.py`

## Manually Accepted Cases

| Case | Manual decision | Why |
|---|---|---|
| `l2b_manual_043` | pass | Correct Microsoft Form 3 filing/report-date distinction. |
| `l2b_manual_047` | pass | Correct partial answer, no hallucinated financial contents. |
| `l2b_manual_049` | pass | Correct Tesla Form 4 filing/report-date distinction. |

## Remaining Failures

These failures remain after removing the 3 accepted manual cases.

| Case | Concise reason |
|---|---|
| `l2b_manual_005` | Unsupported extra detail / hallucination risk. |
| `l2b_manual_009` | Valid-time issue. |
| `l2b_manual_010` | Valid-time issue. |
| `l2b_manual_014` | Behavior/conflict handling issue. |
| `l2b_manual_016` | Behavior label issue. |
| `l2b_manual_024` | Semantic/evidence/valid-time issue. |
| `l2b_manual_028` | Valid-time incomplete. |
| `l2b_manual_041` | Valid-time issue. |
| `l2b_manual_042` | Critical valid-time issue. |
| `l2b_manual_045` | Valid-time issue. |
| `l2b_manual_046` | Valid-time issue. |
| `l2b_manual_050` | Partial/refusal behavior issue. |

This audit keeps the strict score intact and records the manual interpretation
separately. The manual-audited score is not a replacement for the strict score.
