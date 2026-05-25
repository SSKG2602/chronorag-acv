# Benchmark V2 Plan

Temporal Eval v2 has been implemented as the Layer 1A controlled multi-source
temporal retrieval benchmark. This document records what v2 addresses, what
Layer 1B should validate next, and what remains for Layer 2.

## Benchmark Roadmap

- Layer 1A: Temporal Eval v2 retrieval benchmark. Implemented.
- Layer 1B: Evidence-grounded answer-validation benchmark. Next.
- Layer 2: Cross-domain generalization benchmark. Later.

## Why V1 Was Insufficient

The v1 hard 15-case benchmark remains useful as an archived controlled
diagnostic, but it is too small for broader claims:

- 15 cases
- 19 chunks/rows
- mostly one source family
- limited source diversity
- `Source Hit@5` is not meaningful
- `Window Hit@5` saturates
- `Top1 Window` is the main useful signal

V1 demonstrates temporal retrieval behavior on a small corpus. It does not
establish broader validation. Temporal Eval v2 replaces it as the main
controlled benchmark.

## E2 Benchmark Goals

- Test temporal retrieval behavior across a larger but still reproducible corpus.
- Make source attribution metrics meaningful.
- Include success, partial, conflict, ambiguity, and insufficient-evidence cases.
- Separate retrieval quality from answer-writing quality.
- Keep claims limited to controlled benchmark behavior.

Status: implemented in `benchmarks/build_temporal_eval_v2.py`,
`benchmarks/run_temporal_eval_v2.py`, and `benchmarks/temporal_eval_v2_15.jsonl`.

## Required Corpus Properties

- Multiple source files.
- Multiple source families.
- At least 75-150 chunks.
- Expected evidence IDs for each case.
- Expected behavior labels.
- Human-readable expected answers.
- Clear valid-time and transaction-time metadata.
- Answer-quality checks later, after retrieval metrics are stable.

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

## Planned Domains

- Historical macroeconomic data.
- Policy/regulation revisions or company filing revisions as a second domain.
- Optional third domain later: research literature revisions or legal case
  history.

## Non-Goals

- No broad performance claim.
- No broad open-domain QA claim.
- No provider or answer-quality claim from retrieval-only metrics.
- No production-readiness claim.

## Claims Allowed After E2

With E2 in place, the repo can claim:

- ChronoRAG has an internal multi-source controlled benchmark.
- Temporal filtering/fusion changes temporal ranking on the tested benchmark.
- Temporal Contextual Chunking supports more precise temporal evidence retrieval
  under controlled conditions.

It still should not claim general RAG advantage without external benchmarks.
