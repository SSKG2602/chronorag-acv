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
- The primary stored Vertex result is
  `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`.
- The dynamic top-k result is stored separately as a diagnostic at
  `benchmarks/results/temporal_answer_validation_v2_vertex_dynamic_topk_results.md`.

## Remaining Gaps

- The current benchmark is controlled and useful for a research-demo checkpoint,
  but it is not a publication-grade external benchmark.
- Layer 2 cross-domain evaluation is still required.
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

### P2: External Baselines

Compare ChronoRAG against vanilla vector RAG, hybrid BM25/vector RAG, and at
least one temporal/time-aware retrieval baseline. Do not claim SOTA until this
external comparison exists.

### P3: ChronoSanity Evaluation

Measure semantic conflict detection, refusal quality, and evidence-only
degradation behavior against manually labeled cases.
