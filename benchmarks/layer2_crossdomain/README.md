# Layer 2 Cross-Domain Comparison Framework

Layer 2 is a comparison framework for future cross-domain temporal QA. It is
not a result claim yet. The downloaded raw pool currently has 17 files, about
7.04 MB, and 46,503 detected rows/items across FRED macro data, market/index
data, SEC submissions, Federal Register regulations, and GitHub software
releases. The generated local benchmark target is 5,000 processed evidence rows
and 200 questions. The sample fixture files remain small plumbing tests.

The framework uses the same processed corpus, the same questions, the same
Gemini/Vertex model in full mode, and the same final validator for each method.
That keeps the comparison focused on method behavior rather than data or judge
differences.

## Methods

| Method | Purpose |
|---|---|
| `direct_llm_full_context` | Gives Gemini the processed corpus directly, with no retrieval. This is a serious threat baseline because long-context models may solve small or medium corpora without RAG. |
| `metadata_temporal_rag` | Independent metadata/time-aware RAG baseline. It uses raw text plus metadata scoring, but no ChronoRAG TCC `retrieval_text`, temporal fusion, or ChronoSanity code. |
| `chronorag_full` | Adapter around the existing ChronoRAG framework. The fixture adapter maps Layer 2 rows through ChronoRAG TCC and monotone temporal fusion utilities without creating a second ChronoRAG implementation. |

ChronoRAG should be evaluated on valid-time correctness, transaction-time trap
avoidance, conflict/refusal behavior, and grounding, not only generic answer
accuracy.

The same processed corpus, same question set, same Gemini/Vertex model, and same
validator must be used for every method. Direct full-context is included because
it is a real threat baseline: if the processed corpus fits into the model
context, retrieval may not be necessary. Metadata temporal RAG is included as a
fair external-style baseline that has access to ordinary metadata and temporal
fields but not ChronoRAG TCC, temporal fusion, or ChronoSanity.

## Results Table

No final Layer 2 results exist yet. This table is a placeholder for the
5,000-row / 200-question benchmark run.

| Method | Corpus | Questions | Mode | Overall | Evidence | Valid-time | Transaction trap | Conflict | Refusal/partial | Status |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| Direct LLM full-context | pending | pending | pending | pending | pending | pending | pending | pending | pending | framework ready |
| Metadata temporal RAG | pending | pending | pending | pending | pending | pending | pending | pending | pending | framework ready |
| ChronoRAG full | pending | pending | pending | pending | pending | pending | pending | pending | pending | framework ready |

## Temporal Precision Repair

A limited Vertex pilot was diagnostic only, but it exposed a real retrieval
issue in the ChronoRAG adapter on dense daily FRED series. The adapter was
scoring expected time at year granularity, so exact-date queries such as
`1962-08-15` could retrieve same-year wrong-date rows. Layer 2 now adds
symbolic multi-granularity temporal precision in
`benchmarks/layer2_crossdomain/temporal_precision.py`.

Supported retrieval precision includes year, month, day, timestamp, ranges,
quarters, dayparts, and fuzzy phrases such as `early 2024` or `around
2024-10-23`. Valid time and transaction/publication/filing/release time remain
separate. Exact-time precision is not delegated only to embeddings.

`config/models.yaml` documents optional retrieval profiles for later
experiments: `light` keeps `BAAI/bge-small-en-v1.5`, `strong` references
`BAAI/bge-m3` plus `BAAI/bge-reranker-v2-m3`, and `experimental_heavy`
references Qwen 0.6B embedding/reranker models. These profiles are optional and
must not replace symbolic exact-time scoring.

No-Vertex retrieval check:

```bash
python3 benchmarks/layer2_crossdomain/debug_chronorag_retrieval.py --first-n 5 --top-k 5
```

## Commands

Smoke all methods in deterministic light mode:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method all \
  --mode light \
  --limit 3 \
  --result-suffix smoke
```

Estimate Vertex calls without running Gemini:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method direct_llm_full_context \
  --mode vertex \
  --limit 1 \
  --estimate-only
```

Generate provider prompts without calling Vertex:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method metadata_temporal_rag \
  --mode vertex \
  --limit 1 \
  --dry-run-prompts \
  --result-suffix dryrun
```

## Limited Compute Run Plan

Estimate-only commands:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method direct_llm_full_context --mode vertex --limit 1 --estimate-only
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method metadata_temporal_rag --mode vertex --limit 1 --estimate-only
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method chronorag_full --mode vertex --limit 1 --estimate-only
```

One-case dry-run prompt commands:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method direct_llm_full_context --mode vertex --limit 1 --dry-run-prompts --result-suffix direct_dryrun
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method metadata_temporal_rag --mode vertex --limit 1 --dry-run-prompts --result-suffix metadata_dryrun
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method chronorag_full --mode vertex --limit 1 --dry-run-prompts --result-suffix chrono_dryrun
```

Optional paid/provider-backed one-case commands:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method direct_llm_full_context --mode vertex --limit 1 --result-suffix direct_vertex_1
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method metadata_temporal_rag --mode vertex --limit 1 --result-suffix metadata_vertex_1
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method chronorag_full --mode vertex --limit 1 --result-suffix chrono_vertex_1
```

## Current Scope

Only tiny fixture data is included. Do not use these smoke outputs as evidence
that ChronoRAG outperforms baselines. The framework is designed to support a
future controlled benchmark; superiority claims require the full dataset,
completed ChronoRAG adapter, external-style baseline review, and reported
results.

## Raw Pool

The local raw pool is expected at `data/raw/layer2_crossdomain/`. It is not
processed by this scaffold task. See
`benchmarks/layer2_crossdomain/data/raw_pool_manifest.json` for the current
downloaded scale and domain breakdown.

## Public Communication Rule

It is acceptable to say this framework compares ChronoRAG against direct LLM
full-context and metadata-aware temporal RAG baselines. It is not acceptable to
claim ChronoRAG wins until full benchmark results are produced. LinkedIn or
project visuals must use real generated result files only. The raw source pool
scale can be stated because it has been measured; final performance numbers
must wait for actual runs.
