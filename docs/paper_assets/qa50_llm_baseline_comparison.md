# QA50 LLM Baseline Comparison

This is baseline retrieval plus Vertex/Gemini answer generation and Layer 2B validation. It is not retrieval-only.

QA: `benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl` (50 cases)
Corpus: `benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl` (5000 rows)
Top-k: 5
Model: `gemini-2.5-flash`
Temperature: 0.0
Judge enabled: True

| Method | Cases | Retrieval Hit@1 | Retrieval Hit@5 | Retrieval MRR@5 | Hard Contract Pass | Judge Semantic Pass | Strict Combined Pass | Evidence Cited | Valid Time Correct | Provider Errors | Judge Errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 + LLM | 50 | 0.3600 | 0.6400 | 0.4607 | 0.4200 | 0.7800 | 0.4000 | 0.5600 | 0.4600 | 0 | 7 |
| Dense-only + LLM | 50 | 0.4000 | 0.5200 | 0.4423 | 0.3400 | 0.8200 | 0.3200 | 0.4400 | 0.4400 | 0 | 3 |
| Date-filter RAG + LLM | 50 | 0.4000 | 0.6600 | 0.5007 | 0.4400 | 0.9000 | 0.4000 | 0.5800 | 0.4600 | 0 | 0 |

Notes:
- BM25, Dense-only, and Date-filter RAG use the same 50 QA cases, same 5,000-row corpus, same top-k=5, same Gemini 2.5 Flash model, same temperature 0.0, same prompt template, and same validator/judge settings.
- The prompt explicitly instructs the model to distinguish valid time from transaction time.
- Gold expected evidence IDs were not included in prompts.
- Baseline methods are evaluated without evidence injection.
- Despite explicit instructions to distinguish valid time from transaction time, BM25 + LLM, Dense-only + LLM, and Date-filter RAG + LLM reached strict combined pass of 0.4000, 0.3200, and 0.4000 respectively.
- `transaction_time_used_as_valid_time` is not a separate field in the existing Layer 2B answer schema, so valid-time correctness is reported instead.
