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
| `direct_llm_full_context` | Deprecated for serious 5,000-row Layer 2A comparison. It is not a retrieval baseline and can truncate heavily; keep only for historical/small-context diagnostics. |
| `metadata_temporal_rag` | Independent metadata/time-aware RAG baseline. It uses raw text plus metadata scoring, but no ChronoRAG TCC `retrieval_text`, temporal fusion, or ChronoSanity code. |
| `chronorag_full` | Adapter around the existing ChronoRAG framework. The fixture adapter maps Layer 2 rows through ChronoRAG TCC and monotone temporal fusion utilities without creating a second ChronoRAG implementation. |
| `chronorag_gsm` | ChronoRAG full plus Guided Semantic Mode, a deterministic temporal intent planner for hard temporal queries before evidence selection. |

ChronoRAG should be evaluated on valid-time correctness, transaction-time trap
avoidance, conflict/refusal behavior, and grounding, not only generic answer
accuracy.

The same processed corpus, same question set, same Gemini/Vertex model, and same
validator must be used for every provider-backed method. The active Layer
2A diagnostic comparison is `metadata_temporal_rag` vs `chronorag_full`. Direct
full-context is excluded from the default comparison because it is not
retrieval-based and the 5,000-row corpus can exceed practical prompt limits.

## Results Table

No final Layer 2 results exist yet. This table is a placeholder for the
5,000-row / 200-question benchmark run.

| Method | Corpus | Questions | Mode | Overall | Evidence | Valid-time | Transaction trap | Conflict | Refusal/partial | Status |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| Metadata temporal RAG | pending | pending | pending | pending | pending | pending | pending | pending | pending | framework ready |
| ChronoRAG full | pending | pending | pending | pending | pending | pending | pending | pending | pending | framework ready |
| ChronoRAG-GSM | pending | pending | pending | pending | pending | pending | pending | pending | pending | retrieval planner ready |

## Temporal Precision Repair

A limited Vertex pilot was diagnostic only, but it exposed a real retrieval
issue in the ChronoRAG adapter on dense daily FRED series. The adapter was
scoring expected time at year granularity, so exact-date queries such as
`1962-08-15` could retrieve same-year wrong-date rows. Adapter-side precision
fixed the ChronoRAG-only pilot from 2/5 to 5/5. The reusable parser now lives in
`core/ingestion/temporal_precision.py`, and
`benchmarks/layer2_crossdomain/temporal_precision.py` is a compatibility wrapper
for Layer 2 scoring.

Supported retrieval precision includes year, month, day, hour, minute, second,
ranges, fuzzy ranges, quarters, dayparts, and phrases such as `early 2024` or
`around 2024-10-23`. Valid time and transaction/publication/filing/release time
remain separate. Exact-time precision is not delegated only to embeddings.

`config/models.yaml` documents optional retrieval profiles. `light` keeps
`BAAI/bge-small-en-v1.5` at 384 dimensions for laptop-friendly runs. For Layer
2A cloud retrieval runs, prefer `BAAI/bge-base-en-v1.5` at 768 dimensions via:

```bash
export CHRONORAG_EMBED_MODEL=BAAI/bge-base-en-v1.5
export CHRONORAG_EMBED_DIM=768
```

The runner records embedding model and dimension in result metadata. Persisted
indexes fail clearly on model or dimension mismatch; purge and reingest before
mixing 384-dim and 768-dim embeddings. Stronger embeddings improve semantic
candidate quality, but exact-time precision remains symbolic.


## Retrieval-only evaluator status

Layer 2 retrieval-only evaluation is diagnostic and category-aware. Generic
Hit@1/Hit@5 is still reported, but it is not the primary truth for all
categories. Wrong-year traps, transaction-time traps, broad-window distractors,
conflict questions, source-specific questions, metric-specific questions,
cross-domain comparisons, ambiguous queries, and partial/refusal cases have
different scoring semantics.

The evaluator therefore reports:

- total benchmark cases, result rows, evaluated cases, skipped cases, and skip
  reasons per method;
- generic retrieval diagnostics: Hit@1, Hit@5, and forbidden evidence absent@5;
- category-specific diagnostics such as valid-time hit, wrong-year forbidden
  absence, broad-window forbidden absence, conflict-side coverage, source/metric
  constraint checks, and both-side comparison coverage;
- same-case pairwise comparison for two methods: both hit, left-only,
  right-only, neither, per-category deltas, forbidden evidence comparison, and
  malformed/skipped warnings.

Behavior-target categories are not treated as retrieval wins just because any
evidence was retrieved. `partial_or_insufficient_evidence` is primarily an
answer-behavior/refusal target. `ambiguous_time_query` is primarily a
clarification target. Retrieval hits for those categories are diagnostics only.

This evaluator does not call Vertex, does not rerun retrieval, and does not
prove SOTA or publication-grade performance. It audits existing result JSONs so
retrieval policy and benchmark-question fixes can be decided after the scoring
semantics are clean.

## Guided Semantic Mode

GSM is part of ChronoRAG's retrieval path. It is activated for hard temporal
queries such as wrong-year traps, transaction-time vs valid-time traps,
conflict/disagreement questions, source-specific questions, metric/form-specific
questions, cross-domain comparisons, missing-exact-evidence questions, and
ambiguous temporal language. GSM is deterministic and does not use an LLM
planner.

TCC solves temporal evidence representation. GSM is an experimental retrieval-planning branch, not the next Layer 2A direction. Current evaluator repair focuses on `metadata_temporal_rag` vs `chronorag_full` before any retrieval-policy change.

GSM does not replace TCC or temporal fusion. TCC represents evidence; GSM plans
retrieval. For simple exact valid-time questions, `chronorag_gsm` leaves the
existing exact-date ChronoRAG path intact so exact-date retrieval does not
regress. For cross-domain comparisons, GSM retrieves per slot and then merges
evidence so one domain cannot dominate global top-k.

No-Vertex retrieval check:

```bash
python3 benchmarks/layer2_crossdomain/debug_chronorag_retrieval.py --first-n 5 --top-k 5
```

## Output-Contract Hardening

Layer 2A separates semantic answer quality from provider/output infrastructure.
Incomplete answer JSON from Vertex is reported as an answer output-contract
failure, not as a ChronoRAG retrieval or reasoning failure. LLM-judge parse or
provider failures are reported as unscored judge-infrastructure cases, not as
semantic failures.

The runner uses compact prompts and higher output ceilings by default:

- `--answer-max-output-tokens 4000`
- `--judge-max-output-tokens 4000`
- `--json-retry-max-attempts 3`
- `--judge-json-retry-max-attempts 3`

The higher ceilings exist only to avoid incomplete JSON on hard cases. The
answer prompt still asks for short, complete JSON, and the judge prompt uses the
compact schema `{"scores":[1,1,1,1,1],"reason":"short reason"}`. Unscored
judge-infrastructure cases are not semantic failures. Provider output-contract
failures are reported separately from retrieval or reasoning failures.

## Commands

Smoke the default serious methods in deterministic light mode:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method all \
  --mode light \
  --limit 3 \
  --result-suffix smoke
```

No-Vertex retrieval-only run for ChronoRAG-GSM:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method chronorag_gsm \
  --mode dry_run \
  --dataset real \
  --limit 200 \
  --result-suffix retrieval_only_chronorag_gsm_bge_base \
  --embedding-model BAAI/bge-base-en-v1.5 \
  --embedding-dim 768

python3 benchmarks/layer2_crossdomain/evaluate_retrieval_only.py \
  --results benchmarks/layer2_crossdomain/results/layer2_chronorag_gsm_retrieval_only_chronorag_gsm_bge_base_results.json \
  --questions benchmarks/layer2_crossdomain/data/layer2_questions.jsonl
```

No-Vertex retrieval-only baseline:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method metadata_temporal_rag \
  --mode dry_run \
  --dataset real \
  --limit 200 \
  --result-suffix retrieval_only_metadata
```

Estimate Vertex calls without running Gemini:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method chronorag_gsm \
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
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method metadata_temporal_rag --mode vertex --limit 1 --estimate-only
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method chronorag_gsm --mode vertex --limit 1 --estimate-only
```

One-case dry-run prompt commands:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method metadata_temporal_rag --mode vertex --limit 1 --dry-run-prompts --result-suffix metadata_dryrun
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method chronorag_gsm --mode vertex --limit 1 --dry-run-prompts --result-suffix chrono_gsm_dryrun
```

Optional paid/provider-backed one-case commands:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method metadata_temporal_rag --mode vertex --limit 1 --result-suffix metadata_vertex_1
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py --method chronorag_gsm --mode vertex --limit 1 --result-suffix chrono_gsm_vertex_1
```

Recommended controlled GCP 25-case pilot with retry, resume, and traffic
shaping:

```bash
python benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method all \
  --mode vertex \
  --dataset real \
  --limit 25 \
  --result-suffix vertex_pilot25_gsm \
  --vertex-location global \
  --request-sleep-seconds 8 \
  --retry-max-attempts 6 \
  --answer-max-output-tokens 4000 \
  --json-retry-max-attempts 3 \
  --retry-base-sleep-seconds 8 \
  --retry-max-sleep-seconds 120 \
  --resume
```

Method-isolated ChronoRAG-GSM run, only after retrieval-only metrics meet the
target:

```bash
python benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method chronorag_gsm \
  --mode vertex \
  --dataset real \
  --limit 25 \
  --result-suffix vertex_chrono_gsm25 \
  --vertex-location global \
  --request-sleep-seconds 8 \
  --retry-max-attempts 6 \
  --answer-max-output-tokens 4000 \
  --json-retry-max-attempts 3 \
  --resume
```

`429 Resource Exhausted` is a capacity/rate-exhaustion signal, not a benchmark
failure. Use the global endpoint when available, keep requests sequential,
smooth traffic with `--request-sleep-seconds`, and use retry/backoff for
temporary 429/503/transport failures. JSON-format failures use a smaller
`--json-retry-max-attempts` cap so deterministic non-JSON responses do not burn
the full overload retry budget. For longer provider-backed runs, use `tmux` on
a GCP VM and keep generated result files out of commits unless they are
explicitly being published as result artifacts.

## Current Scope

Only tiny fixture data is included in smoke paths. Do not use smoke outputs as
evidence that ChronoRAG outperforms baselines. Retrieval-only metrics must be
reported separately from answer-judge metrics. Do not run full Vertex answer or
judge comparisons until retrieval-only `chronorag_gsm` improves over
`chronorag_full`; no SOTA or public benchmark proof is claimed here.

## Raw Pool

The local raw pool is expected at `data/raw/layer2_crossdomain/`. It is not
processed by this scaffold task. See
`benchmarks/layer2_crossdomain/data/raw_pool_manifest.json` for the current
downloaded scale and domain breakdown.

## Public Communication Rule

It is acceptable to say this framework compares ChronoRAG-GSM against a
metadata-aware temporal RAG baseline. It is not acceptable to claim ChronoRAG
wins until full benchmark results are produced. LinkedIn or project visuals
must use real generated result files only. The raw source pool scale can be
stated because it has been measured; final performance numbers must wait for
actual runs.
