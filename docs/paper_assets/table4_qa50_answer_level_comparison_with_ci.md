# QA50 answer-level comparison with Wilson 95% CI

| Method | Cases | Retrieval Hit@5 / Evidence Available | Strict Combined Pass | Deterministic Hard-Contract Pass | LLM Judge Overall Pass | LLM Judge Semantic Pass | Expected Evidence Cited | Valid Time Used Correct | Notes |
|---|---|---|---|---|---|---|---|---|---|
| BM25 + LLM | 50 | 0.6400 (32/50; 95% CI 0.5014-0.7586) | 0.4000 (20/50; 95% CI 0.2761-0.5382) | 0.4200 (21/50; 95% CI 0.2938-0.5577) | 0.6800 (34/50; 95% CI 0.5419-0.7924) | 0.7800 (39/50; 95% CI 0.6476-0.8725) | 0.5600 (28/50; 95% CI 0.4231-0.6884) | 0.4600 (23/50; 95% CI 0.3297-0.5960) | Standard retrieval top-k=5; LLM prompt handles temporal filtering. |
| Dense-only + LLM | 50 | 0.5200 (26/50; 95% CI 0.3851-0.6520) | 0.3200 (16/50; 95% CI 0.2076-0.4581) | 0.3400 (17/50; 95% CI 0.2244-0.4785) | 0.6800 (34/50; 95% CI 0.5419-0.7924) | 0.8200 (41/50; 95% CI 0.6920-0.9023) | 0.4400 (22/50; 95% CI 0.3116-0.5769) | 0.4400 (22/50; 95% CI 0.3116-0.5769) | Standard retrieval top-k=5; LLM prompt handles temporal filtering. |
| Date-filter RAG + LLM | 50 | 0.6600 (33/50; 95% CI 0.5215-0.7756) | 0.4000 (20/50; 95% CI 0.2761-0.5382) | 0.4400 (22/50; 95% CI 0.3116-0.5769) | 0.7600 (38/50; 95% CI 0.6259-0.8570) | 0.9000 (45/50; 95% CI 0.7864-0.9565) | 0.5800 (29/50; 95% CI 0.4423-0.7062) | 0.4600 (23/50; 95% CI 0.3297-0.5960) | Standard retrieval top-k=5; LLM prompt handles temporal filtering. |
| ChronoRAG Full - pre-injection retrieval | 50 | 0.7400 (37/50; 95% CI 0.6045-0.8413) | n/a | n/a | n/a | n/a | n/a | n/a | Fair retrieval availability comparison; no complete-evidence injection. |
| ChronoRAG Full - post-injection answer setting | 50 | 1.0000 (50/50; 95% CI 0.9287-1.0000) | 0.7000 (35/50; 95% CI 0.5625-0.8090) | 0.7600 (38/50; 95% CI 0.6259-0.8570) | 0.7600 (38/50; 95% CI 0.6259-0.8570) | 0.9600 (48/50; 95% CI 0.8654-0.9890) | 0.9800 (49/50; 95% CI 0.8950-0.9965) | 0.8400 (42/50; 95% CI 0.7149-0.9166) | Prior L2B complete-evidence answer setting; not rerun. |

Notes:
- Answer-level QA50 comparison extracted from existing artifacts; no model, retriever, validator, or judge rerun.
- ChronoRAG Full result is an existing prior L2B result and was not rerun.
- Standard retrieval + LLM baselines were run with the same LLM model and validator where possible.
- ChronoRAG used retrieval-layer temporal grounding; standard baselines used normal retrieval and relied on the LLM prompt to distinguish valid time from transaction time.
- Baseline methods are evaluated without evidence injection. ChronoRAG pre-injection evidence availability is the fair retrieval-availability comparison point. ChronoRAG post-injection answer-level results are reported separately to show performance when expected evidence is available to the generator.
- ChronoRAG pre-injection any expected evidence is 0.7400 (37/50), pre-injection all expected evidence is 0.6400 (32/50), and post-injection evidence available is 1.0000 (50/50).
- Wilson 95% confidence intervals are shown for proportion metrics only; counts are inferred from ratio times cases where needed.
