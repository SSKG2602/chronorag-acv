# Technical Limitations

ChronoRAG should be presented honestly as a temporal-RAG research scaffold, not a finished production system.

## Current Limitations

1. **No public hosted deployment**
   - The repo documents local and notebook workflows, not a live production URL.

2. **Benchmark coverage is still limited**
   - The project has a controlled diagnostic benchmark, but broader validation
     requires a larger multi-source, multi-domain temporal QA benchmark.

3. **Domain coverage is uneven**
   - World-economy/Maddison-style data appears to be the strongest path.
   - Other domains need dedicated schemas, policy sets, tests, and evaluation.

4. **Temporal extraction is partly heuristic**
   - Valid windows, entities, regions, and units depend on structured input quality or pattern detection.
   - Temporal Contextual Chunking is implemented and wired into ingestion, but
     it still needs broader external validation before claiming general behavior.

5. **Storage is not production-hardened yet**
   - A robust production path needs Postgres/pgvector migrations, tenant isolation, indexing strategy, backups, and migration tests.

6. **No complete observability stack**
   - Controller stats exist as response metadata, but dashboards/exporters are not documented.

7. **No security layer**
   - Authentication, authorization, rate limiting, audit permissions, and tenant boundaries are not complete.

8. **No polished UI**
   - Current demo path is CLI/API-first.

9. **Full model mode may be heavy**
   - Sentence transformers, cross-encoders, LLM generation, and llama.cpp dependencies can be slow or difficult on low-memory systems.

10. **Claim discipline required**
   - The project should not claim enterprise readiness until deployment, monitoring, benchmarks, and security are added.

## Correct Public Framing

Use:

```text
Temporal RAG research scaffold with Temporal Contextual Chunking architecture, auditable evidence windows, hybrid retrieval, temporal fusion, and conflict-aware answer generation.
```

Avoid:

```text
Production-ready enterprise temporal intelligence platform.
```
