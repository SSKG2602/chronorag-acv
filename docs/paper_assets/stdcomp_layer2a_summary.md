# Layer 2A Standard Retrieval Comparison

Corpus: `benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl` (5000 rows)
Queries: `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl` (200 cases)
Top-k: 5

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 200 | 0.7750 | 0.9350 | 0.8467 | 0.7600 | 0.5750 |
| Dense-only | 200 | 0.3850 | 0.6100 | 0.4710 | 0.7950 | 0.3000 |
| Date-filter RAG | 200 | 0.7750 | 0.9350 | 0.8475 | 0.7650 | 0.6000 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | 0.7678 | 0.6950 | 0.4813 |
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | 0.8554 | 0.9950 | 0.9625 |

Notes:
- BM25, Dense-only, and Date-filter RAG are standard comparison baselines over raw evidence-row text.
- Standard baselines do not use TCC, valid-time/transaction-time separation, temporal fusion, or forbidden-time suppression.
- Metadata Temporal RAG and ChronoRAG Full values are extracted from the saved Layer 2A retrieval-only artifact.
- MRR@5 for saved methods is computed from saved top-k selected evidence IDs.
