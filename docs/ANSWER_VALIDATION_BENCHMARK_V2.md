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

## Commands

```bash
python benchmarks/run_temporal_answer_validation_v2.py --mode light --top-k 5
```

```bash
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --top-k 5
```

Cost-control commands:

```bash
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --limit 3
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --case-id av2_q01_western_europe_1870_exact
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --dry-run-prompts --limit 2
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --estimate-only
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

## Allowed Interpretation

This benchmark can support claims about controlled ChronoRAG answer behavior over
Temporal Eval v2 evidence cards. It cannot support claims about external
generalization, broad QA quality, or state-of-the-art performance.

## Limitations

- Light mode is only a deterministic harness.
- Vertex mode costs money and requires ADC/project configuration.
- The corpus is still controlled and historical-economy focused.
- Cross-domain generalization is Layer 2 future work.
