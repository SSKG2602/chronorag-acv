# Controlled Hard 15-Case Benchmark

This benchmark is designed to test temporal retrieval behavior, not broad
open-domain QA. It is controlled, small, and intentionally includes cases where
ChronoRAG should return partial evidence, surface conflict risk, or show
insufficient evidence. It is not a broad performance claim.

## Corpus Disclosure

This v1 hard benchmark is a controlled diagnostic, not a publication-grade
external benchmark.

- Corpus size: 19 ingested rows/chunks in the current controlled dataset.
- Case count: 15 benchmark cases.
- Source families: mostly one synthetic source family plus conflict variants.
- Source diversity is intentionally limited in v1.
- `Source Hit@5` is not very meaningful in v1 because most rows share the same
  source family and URI pattern.
- `Window Hit@5` saturates because the corpus is small and top-5 covers much of
  the evidence pool.
- `Top1 Window` is the primary useful signal in the current result table.

Use this benchmark to inspect whether temporal filtering/fusion changes ranking
behavior on the controlled corpus. Do not present these numbers as broad
validation.

Dataset:

```text
data/sample/hard_temporal/
```

Cases:

```text
benchmarks/temporal_qa_hard_15.jsonl
```

Run:

```bash
CHRONORAG_LIGHT=1 python -m cli.chronorag_cli purge
CHRONORAG_LIGHT=1 python -m cli.chronorag_cli ingest data/sample/hard_temporal/*
CHRONORAG_LIGHT=1 python -m benchmarks.run_ablation \
  --cases benchmarks/temporal_qa_hard_15.jsonl \
  --top-k 5 \
  --candidate-k 50 \
  --out benchmarks/results/temporal_qa_hard_15_results.json
```

## Case Guide

| Case | Feature Tested | Expected Behavior | Expected Evidence | Why Baselines May Fail | What ChronoRAG Should Do |
|---|---|---|---|---|---|
| `hard_exact_we_gdp_pc_1870` | Exact valid-time lookup | success | Western Europe GDP per capita, 1870 | Query omits year; lexical/vector ranking may prefer another year. | Use valid window to surface 1870 evidence. |
| `hard_exact_japan_gdp_pc_1950` | Exact valid-time lookup | success | Japan GDP per capita, 1950 | Same entity has several year rows. | Select exact 1950 evidence. |
| `hard_exact_france_debt_1913` | Exact valid-time lookup | success | France public debt ratio, 1913 | Percent/debt evidence competes with broad fiscal text. | Return 1913 percent evidence. |
| `hard_same_entity_we_1870_vs_1913` | Same entity, different year | success | Western Europe, 1870 | Same query can match 1913 equally well. | Let query window disambiguate. |
| `hard_same_entity_we_1913_vs_1870` | Same entity, different year | success | Western Europe, 1913 | Same text surface as 1870 case. | Let query window select 1913. |
| `hard_same_entity_japan_1870_vs_1950` | Same entity, different year | success | Japan, 1870 | Later Japan rows are semantically close. | Prefer exact 1870. |
| `hard_broad_distractor_we_1870` | Broad-window demotion | partial | Exact 1870 plus broad 1870-1913 context | Broad range is highly relevant but less precise. | Keep broad evidence but rank exact-year evidence higher when possible. |
| `hard_broad_distractor_japan_1950` | Broad-window demotion | partial | Exact Japan 1950 plus broad Japan range | Broad range contains 1950 but is less precise. | Use broad evidence as support, not primary exact fact. |
| `hard_broad_distractor_france_1913` | Broad-window demotion | partial | Exact France 1913 plus broad fiscal range | Broad fiscal text overlaps the query terms. | Prefer exact 1913 debt row. |
| `hard_conflict_we_1870` | ChronoSanity conflict | conflict_warning | Western Europe 1870 values 1,960 and 1,850 | Baselines may return one value without conflict context. | Surface both or trigger conflict warning downstream. |
| `hard_conflict_japan_1950` | ChronoSanity conflict | conflict_warning | Japan 1950 values 1,921 and 1,750 | Same valid window has incompatible values. | Preserve conflict evidence. |
| `hard_conflict_france_1913` | ChronoSanity conflict | conflict_warning | France 1913 debt ratio 67 percent and 58 percent | Lexical ranking may hide one conflicting value. | Retrieve both conflict candidates when possible. |
| `hard_missing_we_1820` | Missing evidence | insufficient_evidence | No exact 1820 Western Europe value exists | Baselines may return nearby years confidently. | Refuse or mark insufficient evidence. |
| `hard_publication_time_not_valid_time` | Transaction time vs valid time | insufficient_evidence | 2006 publication metadata only | Systems may confuse publication year with claim-valid year. | Do not treat 2006 as GDP valid time. |
| `hard_ambiguous_multi_year_note` | Ambiguous evidence | ambiguity | Multi-year table note plus precise rows | Ambiguous note mentions several years/entities. | Prefer precise rows or mark ambiguity. |

## Interpretation

The hard benchmark is public-facing because it is discriminative: simple
retrieval methods are expected to fail or partially fail some cases, and
temporal filtering/fusion should improve exact valid-time behavior. Expected
failure cases are included to test refusal, partial answer behavior, and
conflict visibility.

The older `benchmarks/temporal_qa_15.jsonl` file is an internal smoke benchmark.
It validates that the pipeline runs; it is not the public benchmark claim.
