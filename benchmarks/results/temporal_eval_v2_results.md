# Temporal Eval v2 Results

Temporal Eval v2 is a controlled multi-source temporal retrieval and grounding benchmark. It tests whether ChronoRAG can prefer exact valid-time evidence over wrong-year, broad-window, transaction-time-only, metric-confused, and conflict-prone distractors. It is not a broad performance claim, not a publication-grade benchmark, and not proof of external generalization.

## Command

```bash
benchmarks/run_temporal_eval_v2.py --light
```

## Corpus

- Rows: 191
- Source families: 6

- `maddison_project_2023`: 68
- `oecd_world_economy_pdf`: 30
- `owid_global_gdp_long_run`: 10
- `owid_maddison_gdp`: 28
- `owid_maddison_gdppc`: 42
- `synthetic_temporal_traps`: 13

## Category Breakdown

- `A. Exact valid-time retrieval`: 3
- `B. Same entity / wrong year traps`: 3
- `C. Broad-window distractors`: 2
- `D. Transaction-time vs valid-time traps`: 2
- `E. Conflict / ChronoSanity cases`: 2
- `F. Expected partial/failure/ambiguous cases`: 3

## Method Comparison

| Method | Hit@5 Evidence | Top1 Window | Hit@5 Window | Source Family Hit@5 | Distractor Avoidance | Proxy Conflict Correct | Proxy Partial/Refusal Correct | Proxy Behavior Correct | Latency ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 only | 0.33 | 0.40 | 0.87 | 0.80 | 0.80 | 0.00 | 0.07 | 0.20 | 3.04 |
| Vector only | 0.47 | 0.47 | 0.80 | 0.93 | 0.73 | 0.00 | 0.07 | 0.33 | 3.03 |
| Hybrid without temporal filter | 0.40 | 0.47 | 0.87 | 0.93 | 0.67 | 0.00 | 0.07 | 0.20 | 3.04 |
| Hybrid with temporal filter | 0.60 | 0.47 | 0.93 | 0.93 | 0.73 | 0.00 | 0.20 | 0.33 | 3.06 |
| Hybrid + temporal fusion | 0.60 | 0.80 | 0.87 | 1.00 | 0.87 | 0.07 | 0.13 | 0.60 | 3.10 |
| Hybrid + temporal fusion + rerank | 0.73 | 0.80 | 0.87 | 0.93 | 1.00 | 0.07 | 0.07 | 0.73 | 3.17 |

## Metric Scope

Temporal Eval v2 is primarily a retrieval-layer benchmark.

`Hit@5 Evidence`, `Top1 Window`, `Hit@5 Window`, `Source Family Hit@5`, and `Distractor Avoidance` are retrieval-layer metrics. They measure whether the runner retrieves the expected evidence, aligns with the requested valid-time window, reaches the correct source family, and avoids known distractors.

`Proxy Conflict Correct`, `Proxy Partial/Refusal Correct`, and `Proxy Behavior Correct` are light-runner proxy checks. They should not be interpreted as final answer-validation scores.

Full conflict/refusal evaluation requires a separate evidence-grounded answer-validation benchmark that runs retrieved evidence through Temporal Contextual Chunking metadata, evidence cards, LLM answer synthesis, an answer validator, and ChronoSanity/conflict logic.

## Per-Case Full ChronoRAG Results

| Case | Category | Behavior | Top1 Evidence | Hit@5 Evidence | Top1 Window | Proxy Behavior Correct |
|---|---|---|---|---:|---:|---:|
| e2_q01_western_europe_1870_exact | A | answer | e2:maddison:regional:gdp_pc:western_europe:1870 | 1 | 1 | 1 |
| e2_q02_western_europe_1913_exact | A | answer | e2:oecd_pdf:western_europe_exact_1913 | 1 | 1 | 1 |
| e2_q03_india_1870_exact | A | answer | e2:maddison:country:gdp_pc:india:1870 | 1 | 1 | 1 |
| e2_q04_western_europe_compare_1870_1913 | B | compare | e2:oecd_pdf:western_europe_exact_1870 | 1 | 1 | 1 |
| e2_q05_india_1913_not_1870 | B | answer | e2:owid_gdppc:gdp_pc:india:1913 | 1 | 1 | 1 |
| e2_q06_japan_1950_exact_or_broad | B | answer | e2:owid_gdppc:gdp_pc:japan:1950 | 1 | 1 | 1 |
| e2_q07_broad_range_cannot_answer_exact | C | prefer_exact | e2:maddison:regional:gdp_pc:western_europe:1870 | 1 | 1 | 1 |
| e2_q08_broad_1000_2006_demote | C | prefer_exact | e2:oecd_pdf:table_note:western_europe:1870 | 1 | 1 | 1 |
| e2_q09_china_1820_partial | D | partial | e2:maddison:regional:gdp_pc:world:1820 | 0 | 1 | 0 |
| e2_q10_publication_2006_not_valid_1870 | D | answer | e2:maddison:regional:gdp_pc:world:1870 | 0 | 1 | 0 |
| e2_q11_transaction_time_only_records | E | partial | e2:synthetic:source_family_grounding_policy | 0 | 0 | 0 |
| e2_q12_conflict_western_europe_1913 | E | conflict_warning | e2:synthetic:conflict:western_europe:gdp_pc:1913 | 1 | 1 | 1 |
| e2_q13_exact_vs_broad_1913 | F | prefer_exact | e2:oecd_pdf:western_europe_exact_1913 | 1 | 1 | 1 |
| e2_q14_western_europe_1820_missing_exact | F | refuse | e2:synthetic:conflict:western_europe:gdp_pc:1870 | 0 | 0 | 0 |
| e2_q15_ambiguous_industrial_era_europe | F | clarify | e2:synthetic:western_europe_industrial_ambiguous | 1 | 0 | 1 |

## Limitations

- Controlled corpus, not an external benchmark.
- Synthetic traps are included and explicitly labeled.
- OECD rows are short derived passages only; no long copyrighted PDF text is committed.
- Layer 2 generalization across domains remains future work.
