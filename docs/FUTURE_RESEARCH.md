# Future Research Direction

ChronoRAG currently has four completed evaluation checkpoints: Layer 1A
temporal retrieval, Layer 1B answer validation, Layer 2A cross-domain retrieval
quality, and Layer 2B answer synthesis/validation. Future work should extend
external baselines, larger corpora, conflict-pair datasets, paper drafting, and
production hardening.

Temporal Contextual Chunking is the current architectural center. Older helper
layers such as DHQC may still be useful for controller and heuristic
support, but they are not the main research claim of the present checkpoint.
Graph retrieval is still future work rather than an active subsystem.

## 1. Layer 2 Cross-Domain Extensions

Layer 2A and Layer 2B now provide public cross-domain checkpoints. The next
research step is broader coverage: larger corpora, more source families,
conflict-pair datasets, external baselines, and additional review of failure
categories. Those extensions should remain controlled benchmark work, not a
superiority claim.

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

Layer 2A currently compares an independent metadata temporal RAG baseline
against ChronoRAG full using the existing TCC/retrieval framework. Future
extensions can add more baselines and larger corpora. Direct Gemini
full-context remains deprecated for serious Layer 2A retrieval evaluation
because it is not retrieval-based and can truncate heavily.

A small diagnostic pilot exposed an exact-date retrieval weakness on dense FRED
daily series, where year-level scoring could retrieve wrong same-year rows.
Adapter-side precision fixed the ChronoRAG-only pilot from 2/5 to 5/5, and core
TCC now preserves multi-granularity temporal metadata for year, month, day,
hour, minute, second, ranges, quarters, dayparts, and fuzzy phrases. This
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
