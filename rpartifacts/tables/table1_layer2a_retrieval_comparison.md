# Table 1. Layer 2A Retrieval Comparison

Source artifact: `docs/paper_assets/table1_layer2a_retrieval_standard_comparison.csv`

Metric definitions:
- Hit@k: Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.
- MRR@5: Mean reciprocal rank of the first expected or acceptable evidence item within top-5.
- Forbidden Absent@5: Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.
- Category Primary Pass: Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.
- Strict Combined Pass: Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.
- Hard-Contract Pass: Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.
- Judge Semantic Pass: LLM judge semantic answer-correctness signal.
- Valid Time Correct: Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.

| Method | Cases | Hit At 1 | Hit At 5 | Mrr At 5 | Forbidden Absent At 5 | Category Primary Pass |
|---|---|---|---|---|---|---|
| BM25 | 200 | 0.775 | 0.935 | 0.8466666666666669 | 0.76 | 0.575 |
| Dense-only | 200 | 0.385 | 0.61 | 0.47100000000000003 | 0.795 | 0.3 |
| Date-filter RAG | 200 | 0.775 | 0.935 | 0.8475000000000001 | 0.765 | 0.6 |
| Metadata Temporal RAG | 200 | 0.69 | 0.86 | 0.7678333333333334 | 0.695 | 0.48125 |
| ChronoRAG Full | 200 | 0.825 | 0.895 | 0.8554166666666668 | 0.995 | 0.9625 |

Interpretation: Direct result table. BM25 and Date-filter RAG have higher broad Hit@5, while ChronoRAG Full is strongest on temporal-validity diagnostics.

Result type: generated from existing result artifacts; no new experiment was run.
