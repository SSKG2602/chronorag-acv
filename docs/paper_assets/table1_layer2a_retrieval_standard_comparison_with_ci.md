# Layer 2A retrieval-only standard comparison with Wilson 95% CI

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---|---|---|---|---|---|
| BM25 | 200 | 0.7750 (155/200; 95% CI 0.7123-0.8274) | 0.9350 (187/200; 95% CI 0.8920-0.9616) | 0.8467 | 0.7600 (152/200; 95% CI 0.6963-0.8139) | 0.5750 (115/200; 95% CI 0.5057-0.6415) |
| Dense-only | 200 | 0.3850 (77/200; 95% CI 0.3203-0.4540) | 0.6100 (122/200; 95% CI 0.5409-0.6749) | 0.4710 | 0.7950 (159/200; 95% CI 0.7337-0.8451) | 0.3000 (60/200; 95% CI 0.2407-0.3668) |
| Date-filter RAG | 200 | 0.7750 (155/200; 95% CI 0.7123-0.8274) | 0.9350 (187/200; 95% CI 0.8920-0.9616) | 0.8475 | 0.7650 (153/200; 95% CI 0.7016-0.8184) | 0.6000 (120/200; 95% CI 0.5308-0.6654) |
| Metadata Temporal RAG | 200 | 0.6900 (138/200; 95% CI 0.6228-0.7500) | 0.8600 (172/200; 95% CI 0.8051-0.9013) | 0.7678 | 0.6950 (139/200; 95% CI 0.6280-0.7546) | 0.4813 (96/200; 95% CI 0.4118-0.5490) |
| ChronoRAG Full | 200 | 0.8250 (165/200; 95% CI 0.7664-0.8714) | 0.8950 (179/200; 95% CI 0.8448-0.9303) | 0.8554 | 0.9950 (199/200; 95% CI 0.9722-0.9991) | 0.9625 (192/200; 95% CI 0.9231-0.9796) |

Notes:
- Extracted from existing Layer 2A standard-comparison artifact; no retrieval or model rerun.
- Top-k: 5. Benchmark: Layer 2A 200-case retrieval-only comparison.
- Metrics are scored over selected evidence IDs.
- BM25 and Date-filter RAG have higher broad Hit@5, but ChronoRAG Full has stronger Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass.
- This supports temporal-validity retrieval, not generic retrieval superiority.
- Forbidden Absent@5 and Category Primary Pass complement Hit@k and MRR@5 by measuring temporal-invalidity exclusion and source/category correctness.
- Wilson 95% confidence intervals are shown for proportion metrics only; counts are inferred from ratio times cases where needed.
