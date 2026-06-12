# ChronoRAG Repo Polish Audit

Status note: this is a historical cleanup audit, not the current roadmap. Later
Layer 2A and Layer 2B public checkpoints supersede the forward-looking items
below.

## Current Status

ChronoRAG now has a consistent public quickstart, verified light-mode demo path,
committed demo assets under `assets/demo/`, Temporal Eval v2 retrieval results,
Layer 1B answer-validation results, a Layer 2A public retrieval-quality
checkpoint, and a Layer 2B public answer-synthesis/validation checkpoint. The
repository should be presented as a temporal-RAG research framework with
layered benchmark evidence for retrieval, answer validation, and ablation
behavior.

## Completed Polish Items

- README now includes an honest "what works / what does not work" section.
- Demo screenshots exist in `assets/demo/`.
- `howtorunme.md` run commands have been corrected.
- Demo ingest commands use the small smoke dataset by default:
  `data/sample/smoke/*`. The larger `data/sample/docs/aihistory*.txt` files
  are optional full-demo inputs.
- The API quickstart uses the actual runner command:
  `python -m app.uvicorn_runner`.
- Light mode avoids heavyweight LLM loading and returns a deterministic evidence
  digest for smoke demos.
- The verified demo path includes API health, CLI ingest, CLI answer,
  attribution card, and controller stats.
- Temporal Contextual Chunking is documented as ChronoRAG's intended chunking
  strategy for separating raw evidence from retrieval context and temporal
  metadata.
- Temporal Contextual Chunking is implemented and wired into ingestion.
- Temporal Eval v2 is implemented as the Layer 1A controlled retrieval
  benchmark.
- Layer 1B Temporal Answer Validation v2 is implemented with light and Vertex
  modes.
- Layer 2 has a cross-domain comparison framework and generated local
  5,000-row / 200-question dataset path.
- Layer 2A v3 question generation removes hidden-target cases by requiring
  exact dates, source anchors, metrics, versions, and comparison slots to appear
  in the question whenever they are part of the expected evidence contract.
- Layer 2 ChronoRAG adapter retrieval applies symbolic multi-granularity
  temporal precision for dense exact-date/timestamp cases, and core TCC now
  preserves the same precision metadata.
- Layer 2A retrieval scoring now includes polarity-aware temporal intent:
  requested temporal mentions are positive constraints, while locally excluded
  mentions such as `not 1990-03-28` are negative constraints.
- Layer 2A `chronorag_full` retrieval now includes a small finalization pass
  after temporal fusion for exact-time cleanup, valid-time/transaction-time
  separation, source/metric-aware ranking, and conservative comparison/conflict
  diversification.
- The primary stored Vertex result is
  `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`.
- The dynamic top-k result is stored separately as a diagnostic at
  `benchmarks/results/temporal_answer_validation_v2_vertex_dynamic_topk_results.md`.

## Remaining Technical Extensions

- Robust temporal expression normalization for relative, fuzzy, implicit, and
  underspecified dates.
- Learned temporal reranking over semantic relevance, valid-time fit,
  transaction-time role, interval overlap, and forbidden-time penalties.
- Multi-hop temporal reasoning over ordered evidence chains.
- Explicit temporal contradiction modeling with contradiction type and severity
  classification.
- Calibrated temporal confidence estimation for evidence fit, conflict
  likelihood, and answer validity.
- Joint optimization of temporal fusion and source-aware, metric-aware, and
  slot-aware evidence finalization.
- Interpretability tools such as temporal score heatmaps, evidence-ranking
  traces, attribution-flow graphs, and before/after finalization
  visualizations.

## Next Priority

### P1: Layer 2 Benchmark

Build a second-domain temporal benchmark beyond historical GDP-style data. Good
candidate domains include policy revisions, software documentation versions,
company filings, or scientific guideline updates.

The comparison framework now exists under `benchmarks/layer2_crossdomain/`.
It supports independent metadata temporal RAG and ChronoRAG full comparisons with
a generated local 5,000-row / 200-question data path. Direct full-context is
kept only as a historical/small-context diagnostic separate from the current
Layer 2A result claim.

Layer 2A diagnostic work has clarified the need for exact temporal intent in
dense daily series. The reusable parser now lives in
`core/ingestion/temporal_precision.py`. Core TCC preserves year, month, day,
hour, minute, second, range, fuzzy, and daypart metadata while carrying role and
polarity in temporal constraints. Valid time remains separate from
transaction/publication/filing/release time. This is retrieval precision
hardening, not a benchmark win.

Historical next step at the time: rerun 50-case and 200-case retrieval-only
Layer 2A with the v3 question set, polarity-aware temporal scoring, and
retrieval finalization. Later public Layer 2A and Layer 2B checkpoints supersede
that forward-looking item.

### P2: External Baselines

Compare ChronoRAG against vanilla vector RAG, hybrid BM25/vector RAG, and at
least one temporal/time-aware retrieval baseline under the same evidence
contracts.

### P3: ChronoSanity Evaluation

Measure semantic conflict detection, refusal quality, and evidence-only
degradation behavior against manually labeled cases.

## Core Path Scope Audit

- TCC is core. Temporal Contextual Chunking is implemented in ingestion and is
  the main architectural contribution of the current checkpoint.
- Layer 1B answer validation is core. The current benchmark evidence depends on
  TCC-enriched evidence cards, temporal retrieval, grounded synthesis, and
  deterministic validation.
- Vertex provider mode is core for full benchmark execution. Light mode remains
  the CI-safe validation harness.
- DHQC status: active auxiliary module. It is instantiated in `app/deps.py`,
  consumed by `app/services/answer_service.py`, and covered by
  `tests/unit/test_dhqc_caps.py`. It affects controller planning telemetry, but
  it is not the main Layer 1B contribution.
- Graph path status: stub-only. `core/retrieval/graph_paths.py` only raises
  `GraphNotConfigured`, so graph retrieval is outside the current evaluation
  path.
- Outside the active evaluation path: graph retrieval, external baseline
  comparison, and any claim that DHQC is the main architectural novelty.
