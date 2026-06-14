# Table 2. Ablation Comparison

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

| Method | Cases | Hit At 1 | Hit At 5 | Forbidden Absent At 5 | Category Primary Pass |
|---|---|---|---|---|---|
| ChronoRAG Full | 200 | 0.825 | 0.895 | 0.995 | 0.9625 |
| Metadata Temporal RAG | 200 | 0.69 | 0.86 | 0.695 | 0.48125 |
| No Temporal Precision | 200 | 0.75 | 0.85 | 0.945 | 0.75 |
| No Slot Assembler | 200 | 0.83 | 0.89 | 0.815 | 0.775 |
| Score-only | 200 | 0.815 | 0.985 | 0.65 | 0.5625 |
| No TCC | 200 | 0.835 | 0.895 | 0.995 | 0.9625 |
| No Transaction Role | 200 | 0.825 | 0.895 | 0.995 | 0.9625 |
| No Source/Metric Adjustment | 200 | 0.83 | 0.89 | 1.0 | 0.96875 |

Interpretation: Direct ablation table. Score-only retrieval improves broad Hit@5 but weakens forbidden-evidence exclusion and category-primary behavior.

Result type: generated from existing result artifacts; no new experiment was run.
