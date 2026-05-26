# Temporal Eval v2 Benchmark

Temporal Eval v2 is ChronoRAG's main controlled Layer 1A benchmark for temporal
retrieval and grounding. It is primarily a retrieval-layer benchmark. It tests
whether retrieval can prefer exact valid-time evidence over wrong-year,
broad-window, transaction-time-only, metric-confused, and conflict-prone
distractors.

This is not a broad performance claim, not a publication-grade external
benchmark, and not proof of universal temporal reasoning.

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

Layer 2: Generalization Benchmark.

This is later future work. It will test a different domain, likely versioned
software documentation.

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

## Forbidden Claims

- Do not claim broad benchmark leadership.
- Do not claim external generalization proof.
- Do not call it a publication-grade benchmark.
- Do not claim universal temporal reasoning.

## Limitations

- The benchmark is controlled and still focused on historical economic data.
- Synthetic traps are useful for diagnostics but are not a substitute for a
  natural external benchmark.
- Layer 2 generalization across a second domain remains future work.
- Answer-quality evaluation is separate from retrieval/grounding evaluation and
  belongs in Layer 1B.
