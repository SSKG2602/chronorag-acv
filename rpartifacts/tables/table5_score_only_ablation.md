# Table 5. Score-Only Ablation

Source artifact: `docs/paper_assets/table2_layer2a_ablation_comparison.csv`

Metric definitions:
- Hit@k: Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.
- MRR@5: Mean reciprocal rank of the first expected or acceptable evidence item within top-5.
- Forbidden Absent@5: Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.
- Category Primary Pass: Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.
- Strict Combined Pass: Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.
- Hard-Contract Pass: Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.
- Judge Semantic Pass: LLM judge semantic answer-correctness signal.
- Valid Time Correct: Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.

| Method | Hit At 5 | Forbidden Absent At 5 | Category Primary Pass |
|---|---|---|---|
| Score-only | 0.9850 | 0.6500 | 0.5625 |
| ChronoRAG Full | 0.8950 | 0.9950 | 0.9625 |

Interpretation: Extracted ablation contrast. Score-only maximizes broad Hit@5 but damages temporal-validity metrics.

Result type: generated from existing result artifacts; no new experiment was run.
