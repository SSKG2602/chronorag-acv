# QA50 answer-level comparison

| Method | Cases | Retrieval Hit@5 / Evidence Available | Strict Combined Pass | Deterministic Hard-Contract Pass | LLM Judge Overall Pass | LLM Judge Semantic Pass | Expected Evidence Cited | Valid Time Used Correct | Notes |
|---|---|---|---|---|---|---|---|---|---|
| BM25 + LLM | 50 | 0.6400 (32/50) | 0.4000 (20/50) | 0.4200 (21/50) | 0.6800 (34/50) | 0.7800 (39/50) | 0.5600 (28/50) | 0.4600 (23/50) | Standard retrieval top-k=5; LLM prompt handles temporal filtering. |
| Dense-only + LLM | 50 | 0.5200 (26/50) | 0.3200 (16/50) | 0.3400 (17/50) | 0.6800 (34/50) | 0.8200 (41/50) | 0.4400 (22/50) | 0.4400 (22/50) | Standard retrieval top-k=5; LLM prompt handles temporal filtering. |
| Date-filter RAG + LLM | 50 | 0.6600 (33/50) | 0.4000 (20/50) | 0.4400 (22/50) | 0.7600 (38/50) | 0.9000 (45/50) | 0.5800 (29/50) | 0.4600 (23/50) | Standard retrieval top-k=5; LLM prompt handles temporal filtering. |
| ChronoRAG Full - pre-injection retrieval | 50 | 0.7400 (37/50) | n/a | n/a | n/a | n/a | n/a | n/a | Fair retrieval availability comparison; no complete-evidence injection. |
| ChronoRAG Full - post-injection answer setting | 50 | 1.0000 (50/50) | 0.7000 (35/50) | 0.7600 (38/50) | 0.7600 (38/50) | 0.9600 (48/50) | 0.9800 (49/50) | 0.8400 (42/50) | Prior L2B complete-evidence answer setting; not rerun. |

Notes:
- Answer-level QA50 comparison extracted from existing artifacts; no model, retriever, validator, or judge rerun.
- ChronoRAG Full result is an existing prior L2B result and was not rerun.
- Standard retrieval + LLM baselines were run with the same LLM model and validator where possible.
- ChronoRAG used retrieval-layer temporal grounding; standard baselines used normal retrieval and relied on the LLM prompt to distinguish valid time from transaction time.
- Baseline methods are evaluated without evidence injection. ChronoRAG pre-injection evidence availability is the fair retrieval-availability comparison point. ChronoRAG post-injection answer-level results are reported separately to show performance when expected evidence is available to the generator.
- ChronoRAG pre-injection any expected evidence is 0.7400 (37/50), pre-injection all expected evidence is 0.6400 (32/50), and post-injection evidence available is 1.0000 (50/50).
