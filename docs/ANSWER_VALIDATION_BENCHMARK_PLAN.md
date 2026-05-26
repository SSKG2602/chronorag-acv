# Answer Validation Benchmark Plan

## Purpose

Layer 1B evaluates ChronoRAG's final evidence-grounded answer behavior. It
tests whether the system can synthesize answers from retrieved evidence,
cite the right evidence, warn on conflicts, refuse unsupported exact answers,
and ask for clarification when temporal queries are ambiguous.

## Why This Is Separate From Temporal Eval v2

Temporal Eval v2 is primarily a retrieval-layer benchmark. It measures evidence
retrieval, valid-time alignment, source-family retrieval, and distractor
avoidance.

Conflict warnings and refusal behavior are answer-time system behaviors. They
depend on retrieved evidence, Temporal Contextual Chunking metadata, evidence
cards, LLM answer synthesis, answer validation, and ChronoSanity conflict logic.
They should not be treated as proven by retrieval-only metrics.

## Required Pipeline

1. Retrieve top-k evidence.
2. Apply Temporal Contextual Chunking metadata and context.
3. Construct evidence cards.
4. Run LLM answer synthesis.
5. Run answer validator.
6. Run ChronoSanity/conflict checker.
7. Score final answer.

## Required Metrics

- Answer contains required facts.
- Answer cites correct evidence IDs.
- Answer uses exact valid-time evidence when available.
- Answer warns on conflict.
- Answer refuses or marks partial when exact evidence is missing.
- Answer does not treat transaction time as valid time.
- Answer asks clarification for ambiguous temporal queries.

## Case Types

- Exact valid-time answer cases.
- Exact evidence plus broad-window distractor cases.
- Transaction-time-only trap cases.
- Conflict cases with two incompatible values for the same valid window.
- Missing-exact-evidence cases requiring partial or refusal behavior.
- Ambiguous temporal query cases requiring clarification.

## Non-Goals

- No Layer 2 domain generalization yet.
- No broad performance claim.
- No external benchmark claim.
- No provider comparison claim.

## Allowed Claims

Layer 1B is implemented in `benchmarks/run_temporal_answer_validation_v2.py`.
ChronoRAG may claim that it has a controlled answer-validation benchmark for
evidence-grounded temporal answers over the Temporal Eval v2 corpus. It still
should not claim external generalization without Layer 2.

## Provider Reliability Guardrails

The implemented benchmark validates the Vertex prompt contract before provider
calls, extracts raw/fenced/prose-wrapped JSON, normalizes harmless schema shape
drift, validates response schema, checks cited evidence IDs against retrieved
cards, and applies deterministic temporal-rule validation. Provider JSON Parse
Failure is treated as a provider-output contract failure, not a reasoning
failure. One retry is allowed only for parse or non-normalizable schema contract
failures; temporal reasoning and grounding failures are not retried away. A
failed retry cannot overwrite a usable initial response.

After a full 15-case Vertex run, the reliability repair simplified the prompt,
moved behavior-specific checks into deterministic validation, added schema
normalization, and preserved usable initial provider output when repair fails.
Default `--top-k` remains 5, the embedding model is unchanged, and optional
`--dynamic-top-k` exists only for complex-case experiments. Comparative runs can
be stored with `--result-suffix` without overwriting default outputs. The final
cleanup makes q02/q11/q13 validation behavior-aware without weakening grounding,
valid-time, or transaction-time checks.
