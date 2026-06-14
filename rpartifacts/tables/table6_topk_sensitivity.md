# Table 6. Top-k Sensitivity

Source artifact: `docs/paper_assets/topk_sensitivity.csv`

Metric definitions:
- Hit@k: Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.
- MRR@5: Mean reciprocal rank of the first expected or acceptable evidence item within top-5.
- Forbidden Absent@5: Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.
- Category Primary Pass: Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.
- Strict Combined Pass: Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.
- Hard-Contract Pass: Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.
- Judge Semantic Pass: LLM judge semantic answer-correctness signal.
- Valid Time Correct: Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.

| Method Label | K | Cases | Hit At K | Mrr At K | Forbidden Absent At K | Category Primary Pass |
|---|---|---|---|---|---|---|
| ChronoRAG Full | 1 | 200 | 0.825 | 0.825 | 1.0 | 0.70625 |
| ChronoRAG Full | 3 | 200 | 0.89 | 0.8541666666666669 | 0.995 | 0.95625 |
| ChronoRAG Full | 5 | 200 | 0.895 | 0.8554166666666668 | 0.995 | 0.9625 |
| ChronoRAG Full | 10 | 200 | 0.895 | 0.8554166666666668 | 0.995 | 0.9625 |
| BM25 | 1 | 200 | 0.775 | 0.775 | 0.955 | 0.60625 |
| BM25 | 3 | 200 | 0.925 | 0.8441666666666668 | 0.815 | 0.6 |
| BM25 | 5 | 200 | 0.935 | 0.8466666666666669 | 0.76 | 0.575 |
| BM25 | 10 | 200 | 0.935 | 0.8492757936507939 | 0.76 | 0.575 |
| Date-filter RAG | 1 | 200 | 0.775 | 0.775 | 0.955 | 0.60625 |
| Date-filter RAG | 3 | 200 | 0.925 | 0.8450000000000002 | 0.83 | 0.63125 |
| Date-filter RAG | 5 | 200 | 0.935 | 0.8475000000000001 | 0.765 | 0.6 |
| Date-filter RAG | 10 | 200 | 0.935 | 0.8501785714285716 | 0.765 | 0.6 |
| Dense-only | 1 | 200 | 0.385 | 0.385 | 0.97 | 0.35625 |
| Dense-only | 3 | 200 | 0.54 | 0.4549999999999999 | 0.835 | 0.2875 |
| Dense-only | 5 | 200 | 0.61 | 0.47100000000000003 | 0.795 | 0.3 |
| Dense-only | 10 | 200 | 0.61 | 0.4799563492063493 | 0.795 | 0.3 |

Interpretation: Direct retrieval-only sensitivity table over k = 1, 3, 5, 10.

Result type: generated from existing result artifacts; no new experiment was run.
