# ChronoRAG Smoke Retrieval Diagnostic

This file is the small smoke/diagnostic ablation result. It was generated from
the earlier tiny benchmark path and should not be presented as the public hard
benchmark. It is useful for checking that retrieval stages run, not for broad
claims.

Generated with:

```bash
CHRONORAG_LIGHT=1 python -m benchmarks.run_ablation \
  --cases benchmarks/temporal_qa_sample.jsonl \
  --top-k 5 \
  --candidate-k 150 \
  --out benchmarks/results/ablation_results.json
```

| Method | Window Hit@5 | Source Hit@5 | Unit Hit@5 | Text Hit@5 | Latency ms |
|---|---:|---:|---:|---:|---:|
| BM25 only | 0.00 | 1.00 | 1.00 | 1.00 | 163.7 |
| Vector only | 0.00 | 1.00 | 0.67 | 0.00 | 240.2 |
| Hybrid without temporal filter | 0.00 | 1.00 | 1.00 | 0.67 | 163.2 |
| Hybrid with temporal filter | 1.00 | 1.00 | 1.00 | 1.00 | 239.3 |
| Hybrid + temporal fusion | 1.00 | 1.00 | 1.00 | 1.00 | 164.8 |
| Hybrid + temporal fusion + rerank | 1.00 | 1.00 | 1.00 | 1.00 | 228.7 |
