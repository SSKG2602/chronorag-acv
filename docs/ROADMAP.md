# ChronoRAG Roadmap

ChronoRAG is a research scaffold for temporal RAG. It implements bitemporal
retrieval concepts and validates them with Temporal Eval v2, a controlled
multi-source retrieval diagnostic. Layer 1B answer validation is implemented.
The Layer 2 multi-domain comparison framework and generated local dataset path
now exist; the next benchmark step is controlled provider-backed comparison
without overclaiming diagnostic pilots.

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
  RAG and ChronoRAG full under the same corpus, model, and validator.
- Treat small Vertex pilots as diagnostics, not final benchmark results.
- Separate retrieval metrics from provider-backed answer synthesis quality.
- Use the new `benchmarks/layer2_crossdomain/` framework to compare metadata
  temporal RAG and ChronoRAG full under the same corpus, model, and validator.
- Use multi-granularity symbolic temporal precision for dense time-series rows:
  exact dates/timestamps must outrank same-year wrong-date evidence before
  embedding similarity is considered sufficient.
- Keep core TCC precision metadata backward-compatible while extending
  `normalized_start`, `normalized_end`, `precision`, `temporal_role`, and
  ambiguity fields across ingestion paths.

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
