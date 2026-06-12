# Answer Validation Benchmark v2

Status note: this document describes the historical Layer 1B answer-validation
benchmark. Layer 2A and Layer 2B now exist as separate cross-domain checkpoints
and should be cited separately.

Layer 1B evaluates ChronoRAG's evidence-grounded temporal answer behavior over
the Temporal Eval v2 corpus. It should be cited as the Layer 1B
answer-validation checkpoint, separate from Layer 2A retrieval and Layer 2B
cross-domain answer validation.

## Scope

Layer 1A is the retrieval benchmark. It tests whether ChronoRAG retrieves the
right temporal evidence.

Layer 1B is the answer-validation benchmark. It tests whether final answers use
retrieved TCC-enriched evidence cards correctly.

At the time of this Layer 1B design, cross-domain generalization was future
work. It is now covered separately by Layer 2A and Layer 2B.

## Pipeline

```text
Temporal Eval v2 corpus
-> temporal retrieval
-> Temporal Contextual Chunking metadata
-> TCC-enriched evidence cards
-> ChronoRAG grounded synthesis prompt
-> light harness or Vertex Gemini synthesis
-> rule-based answer validator
-> answer-level metrics
```

## Modes

Light mode is a deterministic CI/testing harness. It uses the same retrieval and
TCC evidence-card path, but it does not evaluate LLM reasoning.

Vertex mode is the full-force answer-synthesis benchmark. It uses Vertex Gemini
through the ChronoRAG grounded synthesis prompt. By default, Vertex mode attempts
hybrid lexical + BGE vector retrieval + temporal metadata scoring. If vector
dependencies are unavailable, the run fails clearly unless `--skip-vector` is
explicitly passed.

Vertex mode is provider-backed answer synthesis. Light mode is the deterministic
CI, plumbing, and scoring-validation harness.

## Provider Contract Hardening

The Vertex path validates the ChronoRAG prompt before sending it to the provider.
The prompt must contain the unchanged benchmark question, TCC-enriched evidence
cards, raw-JSON-only instructions, valid-time and transaction-time rules, an
evidence citation rule, and the JSON schema.

The runner then applies:

- robust JSON extraction for raw, fenced, or short prose-wrapped JSON;
- schema normalization for harmless provider shape drift before validation;
- schema validation including behavior and confidence enums;
- evidence-ID grounding validation against retrieved evidence cards;
- deterministic temporal-rule validation for wrong-year, transaction-time,
  broad-window, conflict, partial/refusal, and ambiguity cases;
- one retry only for provider-output contract failures such as JSON parse or
  non-normalizable schema validation failure.

Provider JSON Parse Failure is an infrastructure/provider-contract failure, not
a temporal reasoning failure. Reasoning, grounding, and temporal-rule failures
are not retried away. A failed repair retry cannot overwrite a usable initial
provider response.

## Vertex Run Repair Notes

A full 15-case Vertex run was executed. The observed failures were concentrated
in answer completeness, provider JSON truncation, behavior-specific validator
strictness, and one q15 retrieval/benchmark mismatch. Grounding validation,
temporal-rule validation, transaction-time avoidance, and invented-evidence
checks held.

The repair keeps benchmark cases immutable except for q15's evidence target,
which now uses a narrow source-family grounding policy card because the original
expected India rows did not honestly answer the citation-policy question. The
prompt is intentionally simple: it requires evidence-only grounded JSON output,
valid-time discipline, evidence-ID citation, and no outside knowledge. The
validator, not the prompt, handles schema normalization, behavior-aware required
facts, grounding checks, temporal-rule checks, and retry separation. The final
cleanup accepts q02-style answers when the correct value is present and
`valid_time_used` carries the exact 1913 window, accepts q11-style true refusals
with empty citations, and infers q13 partial/refusal flags from behavior while
logging normalization notes. Grounding, valid-time, and transaction-time checks
remain strict.

## Commands

```bash
python benchmarks/run_temporal_answer_validation_v2.py --mode light --top-k 5
```

```bash
python benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --top-k 5 \
  --case-id av2_q01_western_europe_1870_exact \
  --max-output-tokens 2048
```

Optional dynamic top-k expands only complex cases and keeps the base default at
5:

```bash
python benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --top-k 5 \
  --dynamic-top-k \
  --max-output-tokens 2048
```

Use `--result-suffix` to store comparative runs without changing default output
behavior:

```bash
python benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --top-k 5 \
  --max-output-tokens 2048 \
  --result-suffix topk5
```

Cost-control commands:

```bash
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --limit 3
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --case-id av2_q01_western_europe_1870_exact --max-output-tokens 2048
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --dry-run-prompts --limit 2
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --estimate-only
```

Manual Vertex validation sequence:

```bash
python benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --top-k 5 \
  --case-id av2_q01_western_europe_1870_exact \
  --max-output-tokens 2048

python benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --top-k 5 \
  --limit 3 \
  --max-output-tokens 2048

python benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --top-k 5 \
  --max-output-tokens 2048
```

## Metrics

- Answer Overall Pass.
- Required Facts Present.
- Forbidden Facts Absent.
- Expected Evidence Cited.
- Valid-Time Correct.
- Transaction-Time Trap Avoided.
- Conflict Warning Correct.
- Partial/Refusal Correct.
- Clarification Correct.
- Confidence Correct.
- Provider Contract Pass.
- Grounding Validation Pass.
- Temporal Rule Validation Pass.

## Current Stored Results

Primary result:

```text
benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md
```

Diagnostic result:

```text
benchmarks/results/temporal_answer_validation_v2_vertex_dynamic_topk_results.md
```

Light and dry-run artifacts:

```text
benchmarks/results/temporal_answer_validation_v2_light_results.md
benchmarks/results/temporal_answer_validation_v2_dry_run_prompts.md
```

| Run | Role | Overall Pass | Expected Evidence | Valid-Time Correct | Provider Contract | Grounding | Temporal Rules | Stored failures |
|---|---|---:|---:|---:|---:|---:|---:|---|
| top-k 5 | primary | 0.80 | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | q08, q11, q14 |
| dynamic top-k | diagnostic | 0.80 | 0.87 | 0.87 | 0.87 | 1.00 | 1.00 | q05, q08, q11 |

The top-k 5 run is the benchmark result to cite for this checkpoint. The
dynamic top-k run is useful for debugging retrieval/answer sensitivity, but it
is not the primary claim.

## Allowed Interpretation

This benchmark supports claims about controlled ChronoRAG answer behavior over
Temporal Eval v2 evidence cards. Layer 2A and Layer 2B provide the separate
cross-domain retrieval and answer-validation checkpoints.

## Technical Limitations

### Temporal Expression Parsing

ChronoRAG currently relies on explicit or reliably extractable temporal
expressions. More robust handling of relative, implicit, underspecified, and
fuzzy temporal references remains an important technical extension.

### Rule-Weighted Temporal Fusion

The current temporal fusion layer uses explicitly designed scoring signals. A
learned temporal reranker could adapt the relative importance of semantic
relevance, valid-time fit, transaction-time role, interval overlap, and
forbidden-time penalties across different domains.

### Multi-Hop Temporal Reasoning

ChronoRAG focuses on temporally valid evidence selection and slot-aware
assembly. Extending the framework to multi-hop temporal reasoning, where
answers require ordered chains of evidence across multiple events or intervals,
remains future work.

### Temporal Contradiction Modeling

ChronoSanity detects temporally inconsistent or role-conflicting evidence in
retrieved candidates. Future work should extend this into explicit temporal
contradiction modeling, including contradiction type classification and
contradiction severity scoring.

### Temporal Confidence Calibration

The current framework exposes confidence and attribution metadata, but
calibrated uncertainty estimation for temporal fit, conflict likelihood, and
answer validity remains an open extension.

### Joint Optimization of Evidence Finalization

Source-aware, metric-aware, and slot-aware finalization are implemented as
modular retrieval-time controls. A future version can investigate whether these
controls can be jointly optimized through learning-based evidence selection.

### Interpretability Visualization

The current repository reports numerical retrieval and ablation results.
Additional visual analysis, such as score heatmaps, temporal-ranking traces,
and before/after evidence finalization diagrams, would improve interpretability
of the temporal retrieval process.
