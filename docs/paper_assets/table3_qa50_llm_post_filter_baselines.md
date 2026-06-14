# QA50 standard retrieval + LLM temporal post-filtering baselines

| Method | Cases | Retrieval Hit@1 | Retrieval Hit@5 | Retrieval MRR@5 | Strict Combined Pass | Deterministic Hard-Contract Pass | LLM Judge Overall Pass | LLM Judge Semantic Pass | Valid Time Used Correct | Expected Evidence Cited | Provider Errors | Judge Errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BM25 + LLM | 50 | 0.3600 (18/50) | 0.6400 (32/50) | 0.4607 | 0.4000 (20/50) | 0.4200 (21/50) | 0.6800 (34/50) | 0.7800 (39/50) | 0.4600 (23/50) | 0.5600 (28/50) | 0 | 7 |
| Dense-only + LLM | 50 | 0.4000 (20/50) | 0.5200 (26/50) | 0.4423 | 0.3200 (16/50) | 0.3400 (17/50) | 0.6800 (34/50) | 0.8200 (41/50) | 0.4400 (22/50) | 0.4400 (22/50) | 0 | 3 |
| Date-filter RAG + LLM | 50 | 0.4000 (20/50) | 0.6600 (33/50) | 0.5007 | 0.4000 (20/50) | 0.4400 (22/50) | 0.7600 (38/50) | 0.9000 (45/50) | 0.4600 (23/50) | 0.5800 (29/50) | 0 | 0 |

Notes:
- Extracted from existing QA50 LLM baseline artifacts; no retriever, Vertex/Gemini, validator, or judge rerun.
- All methods use top-k=5, Gemini 2.5 Flash, temperature 0.0, same QA50 cases, same 5,000-row corpus, same prompt template, and same validator/judge settings.
- Gold evidence IDs were not included in prompts.
- The existing Layer 2B answer schema does not expose a separate transaction_time_used_as_valid_time field; valid-time correctness is reported instead.
- Despite explicit instructions to distinguish valid time from transaction time, BM25 + LLM, Dense-only + LLM, and Date-filter RAG + LLM reached strict combined pass of 0.4000, 0.3200, and 0.4000 respectively.
