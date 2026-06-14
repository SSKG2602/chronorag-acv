# Temporal Eval v2 Benchmark

Temporal Eval v2 is ChronoRAG's main controlled Layer 1A benchmark for temporal
retrieval and grounding. It is primarily a retrieval-layer benchmark. It tests
whether retrieval can prefer exact valid-time evidence over wrong-year,
broad-window, transaction-time-only, metric-confused, and conflict-prone
distractors.

The benchmark result should be read as Layer 1A retrieval evidence: a controlled
measurement of temporal evidence selection before answer synthesis.

## Why V1 Was Insufficient

The archived v1 hard benchmark was useful as a diagnostic, but it was too small:

- 15 cases.
- 19 rows/chunks.
- Mostly one source family.
- `Source Hit@5` was not meaningful.
- `Window Hit@5` saturated.
- `Top1 Window` was the main useful signal.

V1 remains archived as a diagnostic benchmark. Temporal Eval v2 replaces it as
the main controlled benchmark.

## Benchmark Layers

Layer 1A: Controlled Multi-Source Temporal Retrieval Benchmark.

This is the currently implemented Temporal Eval v2 benchmark. It tests
retrieval, temporal window alignment, source-family retrieval, and distractor
avoidance.

Layer 1B: Evidence-Grounded Answer Validation Benchmark.

This is implemented separately in
`benchmarks/run_temporal_answer_validation_v2.py`. It tests final answer
behavior using retrieved evidence, Temporal Contextual Chunking-enriched
evidence cards, Vertex Gemini synthesis in full mode, answer validation,
refusal handling, and ChronoSanity-style conflict warnings.

Layer 1B has its own result files under `benchmarks/results/`. Temporal Eval v2
retrieval metrics should not be mixed with answer-completeness or provider JSON
contract failures.

Layer 2: Cross-Domain Benchmark.

Layer 2A and Layer 2B are separate cross-domain checkpoints with their own
retrieval-only and answer-validation result files.

## Raw Data Paths

```text
data/raw/temporal_eval_v2/maddison/mpd2023_web.xlsx
data/raw/temporal_eval_v2/oecd/oecd3.pdf
data/raw/temporal_eval_v2/owid/gdp-maddison-project-database.csv
data/raw/temporal_eval_v2/owid/gdp-per-capita-maddison-project-database.csv
data/raw/temporal_eval_v2/owid/global-gdp-over-the-long-run.csv
```

## Generated Data Paths

```text
data/sample/temporal_eval_v2/temporal_eval_v2_corpus.jsonl
data/sample/temporal_eval_v2/temporal_eval_v2_sources.json
data/sample/temporal_eval_v2/temporal_eval_v2_manifest.json
benchmarks/temporal_eval_v2_15.jsonl
benchmarks/results/temporal_eval_v2_results.json
benchmarks/results/temporal_eval_v2_results.md
```

## Source Families

- `maddison_project_2023`
- `owid_maddison_gdppc`
- `owid_maddison_gdp`
- `owid_global_gdp_long_run`
- `oecd_world_economy_pdf`
- `synthetic_temporal_traps`

`Source Hit@5` is more meaningful in v2 than v1 because the corpus contains
multiple source families.

## Corpus Construction

The builder creates 150-200 rows. Source-backed rows use values present in the
raw files. Synthetic rows are explicit traps for conflict, ambiguity,
wrong-year, wrong-metric, or transaction-time behavior.

OECD PDF-derived rows use short derived passages and metadata only. The repo
does not commit long OECD PDF text or copied tables.

## Case Categories

The benchmark has exactly 15 cases:

- A. Exact valid-time retrieval: 3 cases.
- B. Same entity / wrong year traps: 3 cases.
- C. Broad-window distractors: 2 cases.
- D. Transaction-time vs valid-time traps: 2 cases.
- E. Conflict / ChronoSanity cases: 2 cases.
- F. Expected partial/failure/ambiguous cases: 3 cases.

## Metrics

- Top1 Evidence ID.
- Hit@5 Evidence ID.
- Top1 Window.
- Hit@5 Window.
- Source Family Hit@5.
- Distractor Avoidance.
- Proxy Conflict Correctness.
- Proxy Partial/Refusal Correctness.

The proxy behavior metrics are light-runner checks only. They are not final
answer-validation scores. Final conflict/refusal evaluation belongs in the
separate Layer 1B answer-validation benchmark. Layer 1B keeps default top-k at
5, has optional dynamic top-k for complex-case experiments, and scores provider
JSON contract failures separately from answer reasoning failures.

## Reproduction

```bash
python benchmarks/build_temporal_eval_v2.py
python benchmarks/run_temporal_eval_v2.py --light
```

For local machines where vector model downloads are undesirable:

```bash
python benchmarks/run_temporal_eval_v2.py --light --skip-vector
```

## Allowed Claims

Temporal Eval v2 is a controlled multi-source benchmark testing whether
ChronoRAG can prefer exact valid-time evidence over wrong-year, broad-window,
transaction-time-only, metric-confused, and conflict-prone distractors.

## Interpretation Boundaries

- Layer 1A reports retrieval-layer behavior over Temporal Eval v2.
- Layer 1B reports answer-level behavior over TCC-enriched evidence cards.
- Layer 2A and Layer 2B report separate cross-domain retrieval and
  answer-validation checkpoints.

## Technical Limitations

### Temporal Expression Parsing

ChronoRAG currently relies on explicit or reliably extractable temporal
expressions. More robust handling of relative, implicit, underspecified, and
fuzzy temporal references remains an important technical extension.

### Rule-Weighted Temporal Fusion

The current temporal fusion layer uses explicitly designed scoring signals. A
learned temporal reranker could adapt the relative importance of semantic
relevance, valid-time fit, transaction-time role, interval overlap, and
forbidden-time penalties across different domains.

### Multi-Hop Temporal Reasoning

ChronoRAG focuses on temporally valid evidence selection and slot-aware
assembly. Extending the framework to multi-hop temporal reasoning, where
answers require ordered chains of evidence across multiple events or intervals,
remains future work.

### Temporal Contradiction Modeling

ChronoSanity detects temporally inconsistent or role-conflicting evidence in
retrieved candidates. Future work should extend this into explicit temporal
contradiction modeling, including contradiction type classification and
contradiction severity scoring.

### Temporal Confidence Calibration

The current framework exposes confidence and attribution metadata, but
calibrated uncertainty estimation for temporal fit, conflict likelihood, and
answer validity remains an open extension.

### Joint Optimization of Evidence Finalization

Source-aware, metric-aware, and slot-aware finalization are implemented as
modular retrieval-time controls. A future version can investigate whether these
controls can be jointly optimized through learning-based evidence selection.

### Interpretability Visualization

The repository includes numerical retrieval tables, ablation results, a
retrieval-only temporal feature heatmap, and a one-query trace. Broader
interpretability coverage, such as more per-category traces and before/after
evidence finalization diagrams, remains future work.
