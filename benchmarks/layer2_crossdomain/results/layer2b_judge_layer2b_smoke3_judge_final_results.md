# Layer 2B LLM Judge Results

This is a strict-but-fair Layer 2B answer-quality judge report, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Input answer results: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_smoke3_vertex_final_results.jsonl`
- Cases: 3
- Result suffix: `layer2b_smoke3_judge_final`
- Mapping errors: 0
- Judge errors: 0
- Judge parse failures: 1
- Judge provider failures: 0
- Judge retry attempts: 0
- Deterministic hard-contract pass: 3 / 3
- LLM judge pass: 3 / 3
- Combined pass: 3 / 3

| Question ID | Type | Expected Behavior | Status | Deterministic Pass | Judge Pass | Combined Pass | Severity | Failure Reasons |
|---|---|---|---|---:|---:|---:|---|---|
| l2b_manual_001 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_002 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
| l2b_manual_003 | exact_lookup | answer | completed | yes | yes | yes | pass |  |
