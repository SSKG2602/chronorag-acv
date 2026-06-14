# Layer 2A retrieval-only standard comparison

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---|---|---|---|---|---|
| BM25 | 200 | 0.7750 | 0.9350 | 0.8467 | 0.7600 | 0.5750 |
| Dense-only | 200 | 0.3850 | 0.6100 | 0.4710 | 0.7950 | 0.3000 |
| Date-filter RAG | 200 | 0.7750 | 0.9350 | 0.8475 | 0.7650 | 0.6000 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | 0.7678 | 0.6950 | 0.4813 |
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | 0.8554 | 0.9950 | 0.9625 |

Notes:
- Extracted from existing Layer 2A standard-comparison artifact; no retrieval or model rerun.
- Top-k: 5. Benchmark: Layer 2A 200-case retrieval-only comparison.
- Metrics are scored over selected evidence IDs.
- BM25 and Date-filter RAG have higher broad Hit@5, but ChronoRAG Full has stronger Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass.
- This supports temporal-validity retrieval, not generic retrieval superiority.
- Forbidden Absent@5 and Category Primary Pass complement Hit@k and MRR@5 by measuring temporal-invalidity exclusion and source/category correctness.
