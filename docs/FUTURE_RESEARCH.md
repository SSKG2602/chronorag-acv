# Future Research Direction

ChronoRAG currently has Layer 1A retrieval evaluation and Layer 1B
answer-validation evaluation over a controlled temporal corpus. The next work
should broaden evidence, domains, and baselines without claiming SOTA or
publication-grade proof prematurely.

Temporal Contextual Chunking is the current architectural center. Older helper
layers such as DHQC and GSM may still be useful for controller and heuristic
support, but they are not the main research claim of the present checkpoint.
Graph retrieval is still future work rather than an active subsystem.

## 1. Layer 2 Cross-Domain Benchmark

Build a second-domain benchmark with questions that require correct valid-time
and transaction-time reasoning outside the current historical GDP-style corpus.
The scaffold now exists under `benchmarks/layer2_crossdomain/`, with a generated
local path for the planned 5,000-row / 200-question processed corpus. The next
step is controlled provider-backed comparison and review of failure categories,
not a superiority claim.

Minimum dataset fields:

```text
question
expected_answer
valid_window_start
valid_window_end
source_uri
conflicting_source_uri
answer_unit
domain
```

Candidate domains:

- policy and regulation updates
- versioned software documentation
- company filings and earnings-call revisions
- scientific literature revisions
- medical guideline changes
- legal case history

The Layer 2 comparison target is direct Gemini full-context, an independent
metadata temporal RAG baseline, and ChronoRAG full through an adapter around the
existing TCC/retrieval framework. No result claim exists until the full
cross-domain benchmark is built and run.

A small diagnostic pilot exposed an exact-date retrieval weakness on dense FRED
daily series, where year-level scoring could retrieve wrong same-year rows.
Layer 2 now includes symbolic multi-granularity temporal precision for year,
month, day, timestamp, ranges, quarters, dayparts, and fuzzy phrases. This
precision should remain separate from embedding-model experiments: stronger
embeddings can help recall, but exact valid-time matching should not be
delegated only to semantic similarity.

Each domain needs a metadata schema, source-family disclosure, sample corpus,
expected evidence IDs, expected behavior labels, and readable expected answers.

## 2. External Baseline Comparison

Compare:

- vanilla vector RAG
- BM25 + vector hybrid RAG
- ChronoRAG without temporal pre-mask
- ChronoRAG with temporal pre-mask
- ChronoRAG with ChronoSanity fallback
- at least one existing temporal retrieval or time-aware RAG baseline, if a
  comparable implementation is available

Do not claim SOTA until this external comparison exists.

## 3. Ablation Study

Measure the effect of each major component:

| Component | Test |
|---|---|
| Temporal Contextual Chunking | Does raw-text plus retrieval-context indexing improve exact-window evidence quality? |
| Temporal pre-mask | Does retrieval avoid wrong-era evidence? |
| Monotone temporal fusion | Does ranking penalize time mismatch correctly? |
| Authority score | Does source reliability affect final answer quality? |
| Unit bias | Does numeric evidence improve answer correctness? |
| Region diversity | Does retrieval avoid over-concentrated evidence? |
| ChronoSanity | Does conflict fallback reduce hallucination? |

## 4. ChronoSanity Reliability

Evaluate conflict detection against manually labeled evidence pairs.

Metrics:

- conflict precision
- conflict recall
- false degradation rate
- missed conflict rate
- answer correctness after fallback

## 5. Storage Research

Move toward production-grade temporal storage:

- Postgres + pgvector
- valid-time indexes
- transaction-time indexes
- composite filters over domain/entity/window
- migration scripts
- backfill strategy
- source revision ledger

## 6. Human-Centered Attribution

Build attribution cards for analysts:

- source timeline
- valid vs transaction window separation
- conflict explanation
- confidence reasoning
- alternative windows
- answer provenance graph

## 7. Cost-Aware Temporal Retrieval

Add adaptive routing:

- cheap lexical-first mode
- vector-only when lexical coverage fails
- reranker only above ambiguity threshold
- LLM judge only for close conflicts
- evidence-only mode when generation adds no value
