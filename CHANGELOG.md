# Changelog

## Unreleased — Layer 1B benchmark polish
- Added Temporal Answer Validation v2 result framing for the Vertex top-k 5
  benchmark and dynamic top-k diagnostic run.
- Hardened provider-output handling with schema normalization, robust JSON
  extraction, and retry protection so a failed repair retry cannot overwrite a
  usable initial response.
- Added diagnostics for parse/retry behavior, including
  `initial_parse_succeeded`, `retry_parse_succeeded`, `retry_attempted`,
  `fallback_to_initial_response`, and `schema_normalization_notes`.
- Added `--result-suffix` for storing comparative benchmark runs without
  overwriting default result files.
- Kept the default embedding model at `BAAI/bge-small-en-v1.5` with dimension
  384 and kept default answer-validation top-k at 5.
- Documented the primary Vertex result honestly: 0.80 overall pass on the
  controlled 15-case Layer 1B benchmark, with q08, q11, and q14 remaining as
  failures in the stored top-k 5 run.
- Reaffirmed that ChronoRAG is a temporal-RAG research-demo checkpoint, not a
  SOTA claim, production service, or publication-grade proof.

## v0.1.0 — Initial research scaffold
- Created ChronoRAG repository skeleton with ingest → retrieve → answer pipeline stubs.
- Added configs, scripts, sample data, CLI, tests, and notebooks for smoke validation.
