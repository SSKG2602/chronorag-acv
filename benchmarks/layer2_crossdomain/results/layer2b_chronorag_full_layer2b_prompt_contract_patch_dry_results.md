# Layer 2B Results: chronorag_full

This is a controlled Layer 2B manual-QA runner report, not a SOTA or publication-grade claim.

- Mode: `dry_run`
- Method: `chronorag_full`
- Cases: 3
- Top-k: 5
- Result suffix: `layer2b_prompt_contract_patch_dry`
- Provider errors: 0
- JSON/schema failures: 0
- Expected evidence retrieved before injection: 0 / 3
- Expected evidence available to model after injection: 3 / 3
- Injected expected evidence rows: 3
- Cases with injected expected evidence: 3
- Expected evidence cited: 0 / 3
- Valid time correctness: 0 / 3
- Behavior correctness: 0 / 3
- Overall contract pass: 0 / 3

Dry run retrieves evidence and checks retrieval coverage only. It does not call Vertex and does not evaluate generated answer quality.

Expected-evidence injection was used for at least one case. Injected evidence is gold evidence made available to evaluate answer synthesis with the right evidence in context; it must not be interpreted as retrieval quality.

| Question ID | Type | Expected Behavior | Status | Retrieved Expected Evidence | Available To Model | Injected Evidence IDs | Contract Pass | Failure Reasons |
|---|---|---|---|---:|---:|---|---:|---|
| l2b_manual_001 | exact_lookup | answer | completed | no | yes | l2:federal_register:2025-10610 | n/a | answer_contract_not_applicable_in_dry_run |
| l2b_manual_002 | exact_lookup | answer | completed | no | yes | l2:federal_register:2025-14506 | n/a | answer_contract_not_applicable_in_dry_run |
| l2b_manual_003 | exact_lookup | answer | completed | no | yes | l2:federal_register:2025-15899 | n/a | answer_contract_not_applicable_in_dry_run |
