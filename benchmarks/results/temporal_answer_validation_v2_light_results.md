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

- Corpus rows: 190
- Cases: 15

## Pipeline Summary

retrieve top-k temporal evidence -> build TCC-enriched evidence cards -> run light harness or Vertex Gemini grounded synthesis -> validate answer -> score final answer

## Metrics

| Metric | Score |
|---|---:|
| Answer Overall Pass | 0.73 |
| Required Facts Present | 1.00 |
| Forbidden Facts Absent | 0.93 |
| Expected Evidence Cited | 0.87 |
| Valid-Time Correct | 0.87 |
| Transaction-Time Trap Avoided | 1.00 |
| Conflict Warning Correct | 1.00 |
| Partial/Refusal Correct | 1.00 |
| Clarification Correct | 1.00 |

## Per-Case Table

| Case | Expected Behavior | Detected Behavior | Cited Evidence IDs | Overall Pass | Failure Reason |
|---|---|---|---|---:|---|
| av2_q01_western_europe_1870_exact | answer | answer | e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870 | 1 |  |
| av2_q02_western_europe_1913_window | answer | answer | e2:oecd_pdf:western_europe_exact_1913, e2:oecd_pdf:table_note:western_europe:1913 | 1 |  |
| av2_q03_transaction_time_avoidance | answer | answer | e2:oecd_pdf:data_about_1870_pub_2006 | 1 |  |
| av2_q04_india_1913_wrong_year | answer | answer | e2:maddison:country:gdp_pc:india:1913 | 1 |  |
| av2_q05_india_metric_confusion | prefer_exact | prefer_exact | e2:maddison:country:gdp_pc:india:1870, e2:owid_gdppc:gdp_pc:india:1870 | 1 |  |
| av2_q06_western_europe_compare | compare | compare | e2:oecd_pdf:western_europe_exact_1870, e2:oecd_pdf:western_europe_exact_1913 | 1 |  |
| av2_q07_broad_1000_2006_demote | prefer_exact | prefer_exact | e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870, e2:oecd_pdf:table_note:western_europe:1870 | 1 |  |
| av2_q08_broad_trend_no_exact_value | prefer_exact | prefer_exact | e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870 | 1 |  |
| av2_q09_conflict_warning_1913 | conflict_warning | conflict_warning | e2:oecd_pdf:western_europe_exact_1913, e2:synthetic:conflict:western_europe:gdp_pc:1913 | 1 |  |
| av2_q10_exact_vs_broad_1913 | prefer_exact | prefer_exact | e2:oecd_pdf:western_europe_exact_1913 | 1 |  |
| av2_q11_western_europe_1820_missing | refuse | refuse | e2:maddison:regional:gdp_pc:western_europe:1950 | 0 | forbidden_facts_absent, acceptable_evidence_cited |
| av2_q12_china_1820_partial | partial | partial | e2:owid_global:gdp_total:world:1820 | 0 | acceptable_evidence_cited |
| av2_q13_transaction_time_only_records | partial | partial | e2:owid_gdppc:gdp_pc:brazil:2018 | 0 | expected_evidence_cited, acceptable_evidence_cited, valid_time_correct |
| av2_q14_ambiguous_industrial_era | clarify | clarify | e2:synthetic:western_europe_industrial_ambiguous | 1 |  |
| av2_q15_source_family_grounding | answer | answer | e2:owid_gdppc:gdp_pc:brazil:2018 | 0 | expected_evidence_cited, acceptable_evidence_cited, valid_time_correct |

## Failure Analysis

- `av2_q11_western_europe_1820_missing`: forbidden_facts_absent, acceptable_evidence_cited
- `av2_q12_china_1820_partial`: acceptable_evidence_cited
- `av2_q13_transaction_time_only_records`: expected_evidence_cited, acceptable_evidence_cited, valid_time_correct
- `av2_q15_source_family_grounding`: expected_evidence_cited, acceptable_evidence_cited, valid_time_correct

## Limitations

- Light mode is a deterministic CI/testing harness, not the production answer technology.
- Vertex mode is the full LLM answer-synthesis evaluation, but still over a controlled corpus.
- This is not Layer 2 and does not establish cross-domain generalization.
- No SOTA or external benchmark claim is made.

## Allowed Interpretation

Use these results to evaluate ChronoRAG's controlled Layer 1B answer behavior over Temporal Eval v2 evidence cards.
