# Table 4. QA50 Answer-Level Comparison

Source artifact: `docs/paper_assets/table4_qa50_answer_level_comparison.csv`

Metric definitions:
- Hit@k: Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.
- MRR@5: Mean reciprocal rank of the first expected or acceptable evidence item within top-5.
- Forbidden Absent@5: Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.
- Category Primary Pass: Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.
- Strict Combined Pass: Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.
- Hard-Contract Pass: Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.
- Judge Semantic Pass: LLM judge semantic answer-correctness signal.
- Valid Time Correct: Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.

| Method | Cases | Retrieval Hit5 Or Evidence Available | Strict Combined Pass | Deterministic Hard Contract Pass | Llm Judge Semantic Pass | Expected Evidence Cited | Valid Time Used Correct |
|---|---|---|---|---|---|---|---|
| BM25 + LLM | 50 | 0.64 | 0.4 | 0.42 | 0.78 | 0.56 | 0.46 |
| Dense-only + LLM | 50 | 0.52 | 0.32 | 0.34 | 0.82 | 0.44 | 0.44 |
| Date-filter RAG + LLM | 50 | 0.66 | 0.4 | 0.44 | 0.9 | 0.58 | 0.46 |
| ChronoRAG Full - pre-injection retrieval | 50 | 0.74 | n/a | n/a | n/a | n/a | n/a |
| ChronoRAG Full - post-injection answer setting | 50 | 1.0 | 0.7 | 0.76 | 0.96 | 0.98 | 0.84 |

Interpretation: Extracted result table. Pre-injection retrieval availability and post-injection answer behavior are reported separately.

Result type: generated from existing result artifacts; no new experiment was run.
