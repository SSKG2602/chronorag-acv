# Table 3. QA50 LLM Post-Filtering Baselines

Source artifact: `docs/paper_assets/table3_qa50_llm_post_filter_baselines.csv`

Metric definitions:
- Hit@k: Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.
- MRR@5: Mean reciprocal rank of the first expected or acceptable evidence item within top-5.
- Forbidden Absent@5: Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.
- Category Primary Pass: Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.
- Strict Combined Pass: Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.
- Hard-Contract Pass: Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.
- Judge Semantic Pass: LLM judge semantic answer-correctness signal.
- Valid Time Correct: Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.

| Method | Cases | Retrieval Hit At 5 | Strict Combined Pass | Deterministic Hard Contract Pass | Llm Judge Semantic Pass | Valid Time Used Correct | Expected Evidence Cited |
|---|---|---|---|---|---|---|---|
| BM25 + LLM | 50 | 0.64 | 0.4 | 0.42 | 0.78 | 0.46 | 0.56 |
| Dense-only + LLM | 50 | 0.52 | 0.32 | 0.34 | 0.82 | 0.44 | 0.44 |
| Date-filter RAG + LLM | 50 | 0.66 | 0.4 | 0.44 | 0.9 | 0.46 | 0.58 |

Interpretation: Direct result table. Standard retrieval plus LLM temporal instructions does not recover ChronoRAG-level strict temporal QA performance.

Result type: generated from existing result artifacts; no new experiment was run.
