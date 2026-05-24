# ChronoRAG Repo Polish Audit

## Current Status

ChronoRAG now has a consistent public quickstart, verified light-mode demo path,
and committed demo assets under `assets/demo/`. The repository should still be
presented as a temporal-RAG research scaffold, not as a production service.

## Completed Polish Items

- README now includes an honest "what works / what does not work" section.
- Demo screenshots exist in `assets/demo/`.
- `howtorunme.md` run commands have been corrected.
- Demo ingest commands use the small smoke dataset by default:
  `data/sample/smoke/*`. The larger `data/sample/docs/aihistory*.txt` files
  are optional full-demo inputs.
- The API quickstart uses the actual runner command:
  `python -m app.uvicorn_runner`.
- Light mode avoids heavyweight LLM loading and returns a deterministic evidence
  digest for smoke demos.
- The verified demo path includes API health, CLI ingest, CLI answer,
  attribution card, and controller stats.
- Temporal Contextual Chunking is documented as ChronoRAG's intended chunking
  strategy for separating raw evidence from retrieval context and temporal
  metadata.

## Remaining Gaps

- No benchmark table or reproducible evaluation report is committed yet.
- No ablation study is committed yet.
- No production deployment layer, migration path, or external observability stack
  is committed yet.
- No public hosted demo URL is documented.
- Temporal Contextual Chunking is not fully implemented or evaluated yet.
- The CLI output is verbose for large ingests and should eventually support a
  concise demo mode.
- The light-mode answer screenshot is a smoke-mode evidence digest, not a
  full-quality model-backed answer.

## Next Priority

### P1: Benchmark Proof

Add a small sanity benchmark for temporal retrieval correctness:

```text
benchmarks/
├── temporal_qa_sample.jsonl
├── run_benchmark.py
└── results/
    └── light_mode_baseline.json
```

Minimum reported metrics:

- `temporal_window_hit_rate`
- `source_hit_rate`
- `unit_hit_rate`
- `evidence_recall_at_5`
- `fallback_rate`
- `latency_ms`

### P2: Ablation Study

Add an ablation script comparing:

- BM25 only
- Vector only
- Hybrid without temporal filter
- Hybrid with temporal filter
- Hybrid plus temporal fusion
- Hybrid plus temporal fusion plus rerank
