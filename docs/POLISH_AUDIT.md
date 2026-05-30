# ChronoRAG Repo Polish Audit

## Current Status

ChronoRAG now has a consistent public quickstart, verified light-mode demo path,
committed demo assets under `assets/demo/`, Temporal Eval v2 retrieval results,
and Layer 1B answer-validation results. The repository should still be
presented as a temporal-RAG research-demo scaffold, not as a production service
or publication-grade proof.

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
- Layer 2 ChronoRAG adapter retrieval applies symbolic multi-granularity
  temporal precision for dense exact-date/timestamp cases, and core TCC now
  preserves the same precision metadata.
- The primary stored Vertex result is
  `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`.
- The dynamic top-k result is stored separately as a diagnostic at
  `benchmarks/results/temporal_answer_validation_v2_vertex_dynamic_topk_results.md`.

## Remaining Gaps

- The current benchmark is controlled and useful for a research-demo checkpoint,
  but it is not a publication-grade external benchmark.
- Full Layer 2 provider-backed comparison is still required.
- External baseline comparisons against other time-aware RAG or temporal
  retrieval systems are still future work.
- No production deployment layer, migration path, or external observability stack
  is committed yet.
- No public hosted demo URL is documented.
- The CLI output is verbose for large ingests and should eventually support a
  concise demo mode.
- The light-mode answer screenshot is a smoke-mode evidence digest, not a
  full-quality model-backed answer.

## Next Priority

### P1: Layer 2 Benchmark

Build a second-domain temporal benchmark beyond historical GDP-style data. Good
candidate domains include policy revisions, software documentation versions,
company filings, or scientific guideline updates.

The comparison framework now exists under `benchmarks/layer2_crossdomain/`.
It supports independent metadata temporal RAG and ChronoRAG full comparisons with
a generated local 5,000-row / 200-question data path. Direct full-context is
kept only as a historical/small-context diagnostic. It does not establish a
result claim yet.

A limited Vertex pilot was diagnostic only. It showed that ChronoRAG's adapter
could fail dense FRED daily exact-date retrieval when time was reduced to year
granularity. Adapter-side precision fixed the ChronoRAG-only pilot from 2/5 to
5/5, and the reusable parser was moved into `core/ingestion/temporal_precision.py`.
Core TCC now preserves year, month, day, hour, minute, second, range, fuzzy,
daypart, and role metadata while keeping valid time separate from
transaction/publication/filing/release time. This repair should not be presented
as a benchmark win.

### P2: External Baselines

Compare ChronoRAG against vanilla vector RAG, hybrid BM25/vector RAG, and at
least one temporal/time-aware retrieval baseline. Do not claim SOTA until this
external comparison exists.

### P3: ChronoSanity Evaluation

Measure semantic conflict detection, refusal quality, and evidence-only
degradation behavior against manually labeled cases.

## Core Path Scope Audit

- TCC is core. Temporal Contextual Chunking is implemented in ingestion and is
  the main architectural contribution of the current checkpoint.
- Layer 1B answer validation is core. The current benchmark proof depends on
  TCC-enriched evidence cards, temporal retrieval, grounded synthesis, and
  deterministic validation.
- Vertex provider mode is core for full benchmark execution. Light mode remains
  the CI-safe validation harness.
- DHQC status: active auxiliary module. It is instantiated in `app/deps.py`,
  consumed by `app/services/answer_service.py`, and covered by
  `tests/unit/test_dhqc_caps.py`. It affects controller planning telemetry, but
  it is not the main Layer 1B contribution.
- Graph path status: stub-only. `core/retrieval/graph_paths.py` only raises
  `GraphNotConfigured`, so graph retrieval is not implemented in the current
  proof path.
- Not part of current proof: graph retrieval, external baseline comparison,
  Layer 2 cross-domain generalization, and any claim that DHQC is the
  main architectural novelty.
