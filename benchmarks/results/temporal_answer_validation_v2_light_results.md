# Temporal Answer Validation v2 Results

## Benchmark Scope

Layer 1B evaluates ChronoRAG answer behavior using temporal retrieval, TCC evidence cards, grounded synthesis, and rule-based validation. It is not Layer 2, not an external benchmark, and not a broad performance claim.

## Mode

light/mock CI harness

## Command

```bash
benchmarks/run_temporal_answer_validation_v2.py --mode light --top-k 5
```

## Cost Note

Light mode is deterministic and makes no Vertex calls. It validates benchmark plumbing and scoring only.

## Corpus And Case Count

- Corpus rows: 191
- Cases: 15
- Base top-k: 5
- Dynamic top-k: False
- Result suffix: none

## Pipeline Summary

retrieve top-k temporal evidence -> build TCC-enriched evidence cards -> validate prompt contract -> run light harness or Vertex Gemini grounded synthesis -> extract JSON -> normalize harmless schema shape drift -> validate schema/evidence/temporal rules -> score final answer

## Provider Contract Diagnostics

- Provider JSON Parse Failure is an infrastructure/provider-output contract failure, not a temporal reasoning failure.
- Harmless schema shape drift is normalized before scoring.
- One repair retry is allowed only for JSON parse or non-normalizable schema failures.
- A failed retry cannot overwrite a usable initial response.
- Grounding and temporal-rule failures are scored as answer/grounding failures and are not retried away.

## Metrics

| Metric | Score |
|---|---:|
| Answer Overall Pass | 1.00 |
| Required Facts Present | 1.00 |
| Forbidden Facts Absent | 1.00 |
| Expected Evidence Cited | 1.00 |
| Valid-Time Correct | 1.00 |
| Transaction-Time Trap Avoided | 1.00 |
| Conflict Warning Correct | 1.00 |
| Partial/Refusal Correct | 1.00 |
| Clarification Correct | 1.00 |
| Confidence Correct | 1.00 |
| Provider Contract Pass | 1.00 |
| Grounding Validation Pass | 1.00 |
| Temporal Rule Validation Pass | 1.00 |

## Per-Case Table

| Case | Expected Behavior | Detected Behavior | Cited Evidence IDs | Overall Pass | Failure Type | Failure Reason |
|---|---|---|---|---:|---|---|
| av2_q01_western_europe_1870_exact | answer | answer | e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870 | 1 |  |  |
| av2_q02_western_europe_1913_window | answer | answer | e2:oecd_pdf:western_europe_exact_1913, e2:oecd_pdf:table_note:western_europe:1913 | 1 |  |  |
| av2_q03_transaction_time_avoidance | answer | answer | e2:oecd_pdf:data_about_1870_pub_2006 | 1 |  |  |
| av2_q04_india_1913_wrong_year | answer | answer | e2:maddison:country:gdp_pc:india:1913 | 1 |  |  |
| av2_q05_india_metric_confusion | prefer_exact | prefer_exact | e2:maddison:country:gdp_pc:india:1870, e2:owid_gdppc:gdp_pc:india:1870 | 1 |  |  |
| av2_q06_western_europe_compare | compare | compare | e2:oecd_pdf:western_europe_exact_1870, e2:oecd_pdf:western_europe_exact_1913 | 1 |  |  |
| av2_q07_broad_1000_2006_demote | prefer_exact | prefer_exact | e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870, e2:oecd_pdf:table_note:western_europe:1870 | 1 |  |  |
| av2_q08_broad_trend_no_exact_value | prefer_exact | prefer_exact | e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870 | 1 |  |  |
| av2_q09_conflict_warning_1913 | conflict_warning | conflict_warning | e2:oecd_pdf:western_europe_exact_1913, e2:synthetic:conflict:western_europe:gdp_pc:1913 | 1 |  |  |
| av2_q10_exact_vs_broad_1913 | prefer_exact | prefer_exact | e2:oecd_pdf:western_europe_exact_1913 | 1 |  |  |
| av2_q11_western_europe_1820_missing | refuse | refuse |  | 1 |  |  |
| av2_q12_china_1820_partial | partial | partial | e2:oecd_pdf:china_background_1820, e2:synthetic:china_partial_background | 1 |  |  |
| av2_q13_transaction_time_only_records | partial | partial | e2:oecd_pdf:publication_2006, e2:oecd_pdf:data_about_1870_pub_2006 | 1 |  |  |
| av2_q14_ambiguous_industrial_era | clarify | clarify | e2:synthetic:western_europe_industrial_ambiguous | 1 |  |  |
| av2_q15_source_family_grounding | answer | answer | e2:synthetic:source_family_grounding_policy | 1 |  |  |

## Failure Analysis

- No failures.

## Limitations

- Light mode is a deterministic CI/testing harness, not the production answer technology.
- Vertex mode is the full LLM answer-synthesis evaluation, but still over a controlled corpus.
- This is not Layer 2 and does not establish cross-domain generalization.
- No SOTA or external benchmark claim is made.

## Allowed Interpretation

Use these results to evaluate ChronoRAG's controlled Layer 1B answer behavior over Temporal Eval v2 evidence cards.
