# Benchmark V2 Plan

Temporal Eval v2 has been implemented as the Layer 1A controlled multi-source
temporal retrieval benchmark. This document records what v2 addresses, what
Layer 1B validates, and what remains for Layer 2.

## Benchmark Roadmap

- Layer 1A: Temporal Eval v2 retrieval benchmark. Implemented.
- Layer 1B: Evidence-grounded answer-validation benchmark. Implemented.
- Layer 2A: Cross-domain retrieval-only benchmark. Implemented.
- Layer 2B: Natural-language temporal QA answer validation. Implemented.

## Why V1 Was Insufficient

The v1 hard 15-case benchmark remains useful as an archived controlled
diagnostic. Its compact design made several metrics less informative:

- 15 cases
- 19 chunks/rows
- mostly one source family
- limited source diversity
- `Source Hit@5` is not meaningful
- `Window Hit@5` saturates
- `Top1 Window` is the main useful signal

V1 demonstrates temporal retrieval behavior on a small corpus. Temporal Eval v2
replaces it as the main controlled Layer 1A benchmark.

## E2 Benchmark Goals

- Test temporal retrieval behavior across a larger reproducible corpus.
- Make source attribution metrics meaningful.
- Include success, partial, conflict, ambiguity, and insufficient-evidence cases.
- Separate retrieval quality from answer-writing quality.
- Keep retrieval, answer-validation, and cross-domain measurements in their
  separate evaluation layers.

Status: implemented in `benchmarks/build_temporal_eval_v2.py`,
`benchmarks/run_temporal_eval_v2.py`, and `benchmarks/temporal_eval_v2_15.jsonl`.
Layer 1B answer validation is implemented separately and has been repaired after
a full Vertex run to simplify the prompt, normalize harmless provider schema
shape drift, preserve usable initial output across failed retries, and improve
behavior-aware validation without changing Layer 1A retrieval claims.

## Required Corpus Properties

- Multiple source files.
- Multiple source families.
- At least 75-150 chunks.
- Expected evidence IDs for each case.
- Expected behavior labels.
- Human-readable expected answers.
- Clear valid-time and transaction-time metadata.
- Answer-quality checks are handled by Layer 1B after retrieval metrics are stable.

## Required Metrics

- Top1 Window Hit.
- Window Hit@5.
- Expected Evidence ID Hit@5.
- Source Family Hit@5.
- Unit Hit@5 where applicable.
- Conflict Evidence Recall.
- Insufficient Evidence False Positive Rate.
- Latency.

## Required Case Types

1. Exact valid-time retrieval.
2. Same entity / wrong year traps.
3. Broad-window distractors.
4. Transaction-time vs valid-time traps.
5. Conflict / ChronoSanity cases.
6. Partial/refusal/ambiguous cases.

## Layer 2 Domains

- Historical macroeconomic data.
- Policy/regulation revisions, company filing revisions, market/index series,
  software releases, and Federal Register records in Layer 2A.
- Additional candidates for later extensions: research literature revisions,
  medical guideline updates, and legal case history.

## Evaluation Boundaries

- Layer 1A and Layer 2A report retrieval and selected-evidence behavior.
- Layer 1B and Layer 2B report answer synthesis and answer-contract behavior.
- Provider-output contract failures are tracked separately from temporal
  reasoning and grounding failures.
- New datasets or source families should preserve expected evidence IDs,
  behavior labels, and reproducible scoring contracts.

## Claims Allowed After E2

With E2 in place, the repo can claim:

- ChronoRAG has an internal multi-source controlled benchmark.
- Temporal filtering/fusion changes temporal ranking on the tested benchmark.
- Temporal Contextual Chunking supports more precise temporal evidence retrieval
  under controlled conditions.
