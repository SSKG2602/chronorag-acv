# Layer 2B LLM Judge Results

This is a strict-but-fair Layer 2B answer-quality judge report, not a SOTA or publication-grade claim.

- Mode: `dry_run`
- Input answer results: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_smoke3_vertex_final_results.jsonl`
- Cases: 3
- Result suffix: `layer2b_judge_retry_defaults_dry`
- Mapping errors: 0
- Judge errors: 0
- Judge parse failures: 0
- Judge provider failures: 0
- Judge retry attempts: 0
- Deterministic hard-contract pass: 3 / 3
- LLM judge pass: n/a
- Combined pass: n/a

Dry run validates result, case, and evidence mapping only. It does not call Vertex and does not evaluate generated answer quality.

| Question ID | Type | Expected Behavior | Status | Deterministic Pass | Judge Pass | Combined Pass | Severity | Failure Reasons |
|---|---|---|---|---:|---:|---:|---|---|
| l2b_manual_001 | exact_lookup | answer | completed | yes | n/a | n/a | not_applicable | judge_not_called_in_dry_run |
| l2b_manual_002 | exact_lookup | answer | completed | yes | n/a | n/a | not_applicable | judge_not_called_in_dry_run |
| l2b_manual_003 | exact_lookup | answer | completed | yes | n/a | n/a | not_applicable | judge_not_called_in_dry_run |
