# Layer 2A Retrieval Runtime

| Method | Cases | top-k | Cold Total Seconds | Warm Retrieval Seconds | Mean Warm Seconds/Query | Queries/Second | Hardware | Timestamp | Notes |
|---|---|---|---|---|---|---|---|---|---|
| BM25 | 200 | 5 | 1.569 | 1.520 | 0.008 | 131.559 | Darwin; Apple M2; 8.0 GB RAM; Python 3.11.1; dense device mps:0 | 2026-06-14T16:16:38+00:00 | Raw BM25 over standard raw_text rows; setup builds BM25 index once. |
| Dense-only | 200 | 5 | 153.111 | 12.884 | 0.064 | 15.523 | Darwin; Apple M2; 8.0 GB RAM; Python 3.11.1; dense device mps:0 | 2026-06-14T16:16:38+00:00 | Dense-only BAAI/bge-small-en-v1.5 cosine retrieval; doc embedding cache hit=True; device=mps:0. |
| Date-filter RAG | 200 | 5 | 3.196 | 3.103 | 0.016 | 64.462 | Darwin; Apple M2; 8.0 GB RAM; Python 3.11.1; dense device mps:0 | 2026-06-14T16:16:38+00:00 | Naive date-string filter followed by BM25; setup builds BM25 index once. |
| Metadata Temporal RAG | 200 | 5 | 17.790 | 17.725 | 0.089 | 11.283 | Darwin; Apple M2; 8.0 GB RAM; Python 3.11.1; dense device mps:0 | 2026-06-14T16:16:38+00:00 | Existing metadata-temporal scorer over ordinary precomputed raw-text chunks; no LLM. |
| ChronoRAG Full | 200 | 5 | 287.195 | 284.030 | 1.420 | 0.704 | Darwin; Apple M2; 8.0 GB RAM; Python 3.11.1; dense device mps:0 | 2026-06-14T16:16:38+00:00 | ChronoRAG Full retrieval with prepared TCC context, temporal fusion, and finalization; no LLM. |

Note: Runtime was measured on the fixed Layer 2A 200-question retrieval-only benchmark at top-k=5. Warm retrieval time excludes one-time model/index loading where applicable. No LLM, judge, Vertex, Gemini, or answer-generation call was used.

Source JSON: `chronorag/stdcomp/results/layer2a_runtime_retrieval_200.json`
