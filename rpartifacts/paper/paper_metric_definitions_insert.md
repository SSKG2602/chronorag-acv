# Paper Metric Definitions Insert

- Hit@k: Fraction of cases where expected or acceptable evidence appears in the top-k selected evidence.
- MRR@5: Mean reciprocal rank of the first expected or acceptable evidence item within top-5.
- Forbidden Absent@5: Fraction of cases where forbidden evidence is absent from the top-5 selected evidence.
- Category Primary Pass: Category-specific temporal-validity diagnostic such as forbidden exclusion, source/metric fit, or slot coverage.
- Strict Combined Pass: Answer-level pass requiring both deterministic hard-contract validation and LLM judge pass.
- Hard-Contract Pass: Rule-based answer-contract validation over citations, evidence availability, valid-time use, and schema/grounding constraints.
- Judge Semantic Pass: LLM judge semantic answer-correctness signal.
- Valid Time Correct: Answer-level check that the response uses the requested valid time rather than transaction/publication/filing time.

Forbidden Absent@5 and Category Primary Pass are constraint-sensitive diagnostics for temporal-validity retrieval. They complement, rather than replace, Hit@k and MRR@5.
