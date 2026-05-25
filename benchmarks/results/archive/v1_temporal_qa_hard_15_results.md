# ChronoRAG Controlled Hard 15-Case Benchmark v1

This is a controlled hard 15-case temporal retrieval diagnostic. It is not an
external benchmark, not publication-grade, and not a broad performance claim. Expected
failure and partial-answer cases are part of the design.

Corpus disclosure:

- Corpus size: 19 ingested rows/chunks.
- Source diversity: mostly one synthetic source family plus conflict variants.
- `Source Hit@5` is not meaningful as a public signal in v1 because source
  diversity is limited.
- `Window Hit@5` saturates because the corpus is small.
- `Top1 Window` is the primary useful signal in this result.

Generated with:

```bash
CHRONORAG_LIGHT=1 python -m cli.chronorag_cli purge
CHRONORAG_LIGHT=1 python -m cli.chronorag_cli ingest data/sample/hard_temporal/*
CHRONORAG_LIGHT=1 python -m benchmarks.run_ablation \
  --cases benchmarks/temporal_qa_hard_15.jsonl \
  --top-k 5 \
  --candidate-k 50 \
  --out benchmarks/results/temporal_qa_hard_15_results.json
```

## Method Summary

| Method | Top1 Window | Window Hit@5 | Source Hit@5 | Unit Hit@5 | Text Hit@5 | Latency ms | Eval n |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 only | 0.54 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Vector only | 0.38 | 1.00 | 1.00 | 0.85 | 1.00 | 0.3 | 13 |
| Hybrid without temporal filter | 0.62 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Hybrid with temporal filter | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Hybrid + temporal fusion | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Hybrid + temporal fusion + rerank | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.4 | 13 |

## Per-Case Full ChronoRAG Results

| Case | Behavior | Difficulty | Feature | Top1 Window | Window Hit@5 | Text Hit@5 |
|---|---|---|---|---:|---:|---:|
| hard_exact_we_gdp_pc_1870 | success | medium | exact valid-time lookup | 1 | 1 | 1 |
| hard_exact_japan_gdp_pc_1950 | success | medium | exact valid-time lookup | 1 | 1 | 1 |
| hard_exact_france_debt_1913 | success | medium | exact valid-time lookup | 1 | 1 | 1 |
| hard_same_entity_we_1870_vs_1913 | success | hard | same entity different year disambiguation | 1 | 1 | 1 |
| hard_same_entity_we_1913_vs_1870 | success | hard | same entity different year disambiguation | 1 | 1 | 1 |
| hard_same_entity_japan_1870_vs_1950 | success | hard | same entity different year disambiguation | 1 | 1 | 1 |
| hard_broad_distractor_we_1870 | partial | hard | broad-window distractor demotion | 1 | 1 | 1 |
| hard_broad_distractor_japan_1950 | partial | hard | broad-window distractor demotion | 1 | 1 | 1 |
| hard_broad_distractor_france_1913 | partial | hard | broad-window distractor demotion | 1 | 1 | 1 |
| hard_conflict_we_1870 | conflict_warning | hard | ChronoSanity conflict behavior | 1 | 1 | 1 |
| hard_conflict_japan_1950 | conflict_warning | hard | ChronoSanity conflict behavior | 1 | 1 | 1 |
| hard_conflict_france_1913 | conflict_warning | hard | ChronoSanity conflict behavior | 1 | 1 | 1 |
| hard_missing_we_1820 | insufficient_evidence | failure_expected | missing evidence refusal | n/a | n/a | 0 |
| hard_publication_time_not_valid_time | insufficient_evidence | failure_expected | transaction time not valid time | n/a | n/a | 1 |
| hard_ambiguous_multi_year_note | ambiguity | failure_expected | ambiguous multi-year evidence | 1 | 1 | 1 |
