# ChronoRAG Roadmap

ChronoRAG is a research scaffold for temporal RAG. It implements bitemporal
retrieval concepts and validates them with controlled retrieval and grounding
diagnostics. Layer 1B answer validation is implemented. Layer 2A is currently a
controlled benchmark/debugging layer for temporal retrieval and grounding, not a
SOTA claim or publication-grade proof.

## P0: Credibility Cleanup

- Documentation credibility cleanup.
- Benchmark caveat and corpus disclosure.
- Architecture consistency around implemented Temporal Contextual Chunking.
- Clear separation between internal smoke diagnostics and public controlled
  benchmark results.

## P1: Layer 1A Temporal Eval v2 Retrieval Benchmark

- Maintain Temporal Eval v2 as the main controlled benchmark.
- Use multiple source files and multiple source families.
- Keep `Source Hit` meaningful through source diversity.
- Include expected evidence IDs, expected behavior labels, and readable expected
  answers.
- Keep failure, partial, ambiguity, and conflict cases in the benchmark design.

## P2: Layer 1B Answer Validation

- Maintain the evidence-grounded answer-validation benchmark.
- Score whether answers cite correct evidence IDs.
- Score conflict warnings, refusals, partial answers, and clarification behavior.
- Keep this separate from retrieval-only metrics.
- Use light mode for CI and Vertex mode for full answer synthesis.
- Treat Provider JSON Parse Failure as a provider-output contract failure, not
  a temporal reasoning failure.
- Normalize harmless schema shape drift before scoring.
- Retry only provider-contract failures once; do not retry away grounding or
  temporal-rule failures, and do not let a failed retry overwrite a usable
  initial response.
- Maintain behavior-aware validation for answer completeness, refusal, partial
  answers, clarification, and source-family grounding.
- Keep default top-k at 5; use optional dynamic top-k only for complex-case
  experiments.
- Use `--result-suffix` for comparative result files without overwriting the
  default benchmark outputs.

## P3: Layer 2 Generalization

- Maintain the 5,000-row / 200-question generated dataset path before claiming
  cross-domain performance.
- Evaluate generalization across domains using independent metadata temporal
  RAG and ChronoRAG full under the same corpus and questions.
- Treat small Vertex pilots as diagnostics, not final benchmark results.
- Keep deterministic Layer 2A validation retrieval-only. It reads
  `selected_evidence_ids` and scores expected evidence Hit@1/Hit@k, acceptable
  evidence Hit@k, forbidden evidence absent@k, and category-specific temporal
  trap checks.
- Do not interpret dry-run answer placeholders as answer-quality results.
- Keep generated answer quality in a separate provider-backed grounded answer
  judge.
- Use the `benchmarks/layer2_crossdomain/` framework to compare metadata
  temporal RAG and ChronoRAG full under the same corpus and questions.
- Maintain the Layer 2A v3 question contract: generated questions must expose
  exact target dates, source anchors, metrics, versions, and comparison slots
  whenever those fields are expected by retrieval-only scoring.
- Keep `conflict_detection` out of the scored v3 retrieval categories until the
  corpus has real two-sided conflict evidence pairs. Missing synthetic conflict
  IDs should remain a data-contract diagnostic, not a scored retrieval target.
- Use multi-granularity symbolic temporal precision for dense time-series rows:
  exact dates/timestamps must outrank same-year wrong-date evidence before
  embedding similarity is considered sufficient.
- Keep temporal constraint polarity explicit so dates after local negation
  phrases such as `not` or `instead of` are penalized during retrieval scoring.
- Keep Layer 2A retrieval finalization small and evidence-selection focused:
  exact-time cleanup, valid-time/transaction-time separation, source/metric
  ranking adjustments, and conservative comparison/conflict diversification.
- Keep core TCC precision metadata backward-compatible while extending
  `normalized_start`, `normalized_end`, `precision`, `temporal_role`, and
  ambiguity fields across ingestion paths.
- Next planned step: rerun 50-case and 200-case retrieval-only Layer 2A with
  retrieval finalization, then add active hybrid retrieval with embeddings as a
  separate patch if needed.

## P4: ChronoSanity Strengthening

- Improve semantic conflict detection beyond overlapping windows.
- Measure conflict precision and recall.
- Evaluate when evidence-only degradation changes trust.
- Add better counterfactual/alternative-window reporting.

## Scope Note

- Temporal Contextual Chunking, temporal retrieval, and grounded answer
  validation define the current core path.
- DHQC remains an active support module and may continue to evolve, but it is
  not the main claim of the current checkpoint. Historical Layer 2A experiments
  are outside the active benchmark surface.
- Graph retrieval remains future work until `graph_paths.py` is replaced with a
  real implementation.
