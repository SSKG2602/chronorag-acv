# Answer Validation Benchmark v2

Layer 1B evaluates ChronoRAG's evidence-grounded temporal answer behavior over
the Temporal Eval v2 corpus. It is not Layer 2, not an external benchmark, and
not a broad performance claim.

## Scope

Layer 1A is the retrieval benchmark. It tests whether ChronoRAG retrieves the
right temporal evidence.

Layer 1B is the answer-validation benchmark. It tests whether final answers use
retrieved TCC-enriched evidence cards correctly.

Layer 2 is future cross-domain generalization.

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

Vertex mode is provider-backed answer synthesis. Light mode is only
CI/plumbing/scoring validation and should not be presented as the production
technology.

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

This benchmark can support claims about controlled ChronoRAG answer behavior over
Temporal Eval v2 evidence cards. It cannot support claims about external
generalization, broad QA quality, or state-of-the-art performance.

## Limitations

- Light mode is only a deterministic harness.
- Vertex mode costs money and requires ADC/project configuration.
- The corpus is still controlled and historical-economy focused.
- Cross-domain generalization is Layer 2 future work.
