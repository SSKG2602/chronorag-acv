# QA50 standard retrieval + LLM temporal post-filtering baselines with Wilson 95% CI

| Method | Cases | Retrieval Hit@1 | Retrieval Hit@5 | Retrieval MRR@5 | Strict Combined Pass | Deterministic Hard-Contract Pass | LLM Judge Overall Pass | LLM Judge Semantic Pass | Valid Time Used Correct | Expected Evidence Cited | Provider Errors | Judge Errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BM25 + LLM | 50 | 0.3600 (18/50; 95% CI 0.2414-0.4986) | 0.6400 (32/50; 95% CI 0.5014-0.7586) | 0.4607 | 0.4000 (20/50; 95% CI 0.2761-0.5382) | 0.4200 (21/50; 95% CI 0.2938-0.5577) | 0.6800 (34/50; 95% CI 0.5419-0.7924) | 0.7800 (39/50; 95% CI 0.6476-0.8725) | 0.4600 (23/50; 95% CI 0.3297-0.5960) | 0.5600 (28/50; 95% CI 0.4231-0.6884) | 0 | 7 |
| Dense-only + LLM | 50 | 0.4000 (20/50; 95% CI 0.2761-0.5382) | 0.5200 (26/50; 95% CI 0.3851-0.6520) | 0.4423 | 0.3200 (16/50; 95% CI 0.2076-0.4581) | 0.3400 (17/50; 95% CI 0.2244-0.4785) | 0.6800 (34/50; 95% CI 0.5419-0.7924) | 0.8200 (41/50; 95% CI 0.6920-0.9023) | 0.4400 (22/50; 95% CI 0.3116-0.5769) | 0.4400 (22/50; 95% CI 0.3116-0.5769) | 0 | 3 |
| Date-filter RAG + LLM | 50 | 0.4000 (20/50; 95% CI 0.2761-0.5382) | 0.6600 (33/50; 95% CI 0.5215-0.7756) | 0.5007 | 0.4000 (20/50; 95% CI 0.2761-0.5382) | 0.4400 (22/50; 95% CI 0.3116-0.5769) | 0.7600 (38/50; 95% CI 0.6259-0.8570) | 0.9000 (45/50; 95% CI 0.7864-0.9565) | 0.4600 (23/50; 95% CI 0.3297-0.5960) | 0.5800 (29/50; 95% CI 0.4423-0.7062) | 0 | 0 |

Notes:
- Extracted from existing QA50 LLM baseline artifacts; no retriever, Vertex/Gemini, validator, or judge rerun.
- All methods use top-k=5, Gemini 2.5 Flash, temperature 0.0, same QA50 cases, same 5,000-row corpus, same prompt template, and same validator/judge settings.
- Gold evidence IDs were not included in prompts.
- The existing Layer 2B answer schema does not expose a separate transaction_time_used_as_valid_time field; valid-time correctness is reported instead.
- Despite explicit instructions to distinguish valid time from transaction time, BM25 + LLM, Dense-only + LLM, and Date-filter RAG + LLM reached strict combined pass of 0.4000, 0.3200, and 0.4000 respectively.
- Wilson 95% confidence intervals are shown for proportion metrics only; counts are inferred from ratio times cases where needed.
