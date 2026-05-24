# Future Research Direction

## 1. Temporal QA Benchmark

Build a benchmark with questions that require correct valid-time and transaction-time reasoning.

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

Compare:

- vanilla vector RAG
- BM25 + vector hybrid RAG
- ChronoRAG without temporal pre-mask
- ChronoRAG with temporal pre-mask
- ChronoRAG with ChronoSanity fallback

## 2. Ablation Study

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

## 3. ChronoSanity Reliability

Evaluate conflict detection against manually labeled evidence pairs.

Metrics:

- conflict precision
- conflict recall
- false degradation rate
- missed conflict rate
- answer correctness after fallback

## 4. Domain Expansion

Candidate domains:

- policy and regulation updates
- company filings and earnings calls
- scientific literature revisions
- medical guideline changes
- macroeconomic datasets
- legal case history

Each domain needs:

- metadata schema
- policy set
- sample corpus
- temporal benchmark
- failure cases

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
