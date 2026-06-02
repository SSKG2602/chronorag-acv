# Layer 2B Results: chronorag_full

This is a controlled Layer 2B manual-QA runner report, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Method: `chronorag_full`
- Cases: 3
- Top-k: 5
- Result suffix: `layer2b_smoke3_vertex_final`
- Provider errors: 0
- JSON/schema failures: 0
- Expected evidence retrieved before injection: 0 / 3
- Expected evidence available to model after injection: 3 / 3
- Injected expected evidence rows: 3
- Cases with injected expected evidence: 3
- Expected evidence cited: 3 / 3
- Valid time correctness: 3 / 3
- Behavior correctness: 3 / 3
- Overall contract pass: 3 / 3

Expected-evidence injection was used for at least one case. Injected evidence is gold evidence made available to evaluate answer synthesis with the right evidence in context; it must not be interpreted as retrieval quality.

| Question ID | Type | Expected Behavior | Status | Retrieved Expected Evidence | Available To Model | Injected Evidence IDs | Contract Pass | Failure Reasons |
|---|---|---|---|---:|---:|---|---:|---|
| l2b_manual_001 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-10610 | yes |  |
| l2b_manual_002 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-14506 | yes |  |
| l2b_manual_003 | exact_lookup | answer | completed | yes | yes | l2:federal_register:2025-15899 | yes |  |
