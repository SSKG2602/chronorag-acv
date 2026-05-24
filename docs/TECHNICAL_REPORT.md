# ChronoRAG Technical Report

## Abstract

ChronoRAG is a temporal retrieval-augmented generation research scaffold for
time-sensitive question answering. It treats validity windows, transaction
windows, provenance, and temporal alignment as first-class retrieval
constraints. The current implementation is a reproducible prototype, not a
production service and not a state-of-the-art claim.

## 1. Problem Statement

Standard RAG systems usually rank evidence by lexical or semantic relevance.
This is insufficient when the answer depends on when a claim was valid. A
passage can be topically relevant but temporally wrong.

ChronoRAG studies this failure mode by separating ordinary relevance from
temporal correctness.

## 2. Temporal Model

ChronoRAG separates three time dimensions:

- Valid time: when the claim is true in the real world.
- Transaction time: when the system observed or stored the claim.
- Query time: the time window requested by the user.

This separation lets the system reject evidence that is semantically relevant
but invalid for the requested period.

## 3. System Architecture

The system is organized into:

- Ingestion layer
- Temporal Contextual Chunking layer
- Persistent vector database abstraction
- BM25 lexical retrieval
- Vector retrieval
- Temporal filtering
- Monotone temporal fusion
- Optional reranking
- ChronoSanity conflict detection
- Optional provider-backed answer synthesis or evidence-only fallback
- Attribution card generation

## 4. Retrieval Pipeline

Before retrieval, ChronoRAG needs chunk records that carry both searchable
context and trustworthy temporal metadata. Temporal Contextual Chunking is
ChronoRAG's chunking strategy, inspired by contextual retrieval but extended for
valid-time retrieval, transaction-time tracking, temporal fusion, ChronoSanity,
and attribution.

The method separates unchanged `raw_text` from `retrieval_text`. `raw_text`
remains the quoteable evidence used for attribution and answer grounding.
`retrieval_text` may add a short context prefix with document title, section,
unit, entity, region, and temporal scope. This improves BM25/vector recall
without letting generated context overwrite the source evidence.

Temporal Contextual Chunking also separates claim-valid time from transaction
time. A publication year can be stored as `tx_start`, but it must not become
`valid_from` unless the source explicitly supports that interpretation. This
prevents a 2006 publication date from being mistaken as the valid year for an
1870 GDP claim.

This layer is needed before temporal filtering and fusion because broad windows
such as `1000-01-01` to `2006-12-31` are weak for exact-year retrieval. Exact
chunk-level or row-level valid-time evidence should outrank broad section or
document windows when the query asks for a specific year.

After chunking, the retrieval pipeline gathers candidate passages using lexical
and vector search. Candidates are then checked against requested valid-time
windows. Time-aligned evidence receives priority before answer synthesis.

Provider-backed synthesis is optional and occurs only after retrieval has
selected evidence. Light mode keeps synthesis deterministic by returning an
evidence digest, while provider mode can use Vertex AI Gemini to turn retrieved
evidence into a grounded answer.

## 5. Monotone Temporal Fusion

Monotone temporal fusion combines relevance, temporal alignment, authority,
transaction-time mismatch, and age penalty. The key design constraint is that
worse temporal compliance must not improve the final score.

This makes time alignment part of ranking, not a post-hoc display field.

## 6. ChronoSanity Conflict Detection

ChronoSanity is a conflict-checking layer. It examines overlapping evidence
windows and incompatible claims. When conflict risk is high or grounding is
weak, the system should degrade to evidence-only output instead of producing
unsupported confidence.

## 7. Attribution Card

The attribution card exposes source URI, valid window, authority signal,
confidence, and alternative/counterfactual windows where available. Its purpose
is auditability.

## 8. Ablation Study

The current ablation compares:

- BM25 only
- Vector only
- Hybrid without temporal filter
- Hybrid with temporal filter
- Hybrid + temporal fusion
- Hybrid + temporal fusion + rerank

The internal `benchmarks/temporal_qa_15.jsonl` benchmark is a smoke benchmark.
It validates that the pipeline runs over a small local dataset. It should not be
used as the public claim benchmark.

The public controlled benchmark is `benchmarks/temporal_qa_hard_15.jsonl`. It is
designed to test temporal retrieval behavior, not broad open-domain QA. It has
five categories:

- exact valid-time lookup
- same entity across different years
- broad-window distractor demotion
- conflict/ChronoSanity visibility
- expected partial, ambiguous, or insufficient-evidence cases

Expected failure cases are included deliberately. They test whether the system
can avoid treating publication time as valid time, avoid overclaiming missing
evidence, and surface ambiguity. These cases are not counted as ordinary
retrieval successes in the method summary.

Current hard benchmark result:

| Method | Top1 Window | Window Hit@5 | Source Hit@5 | Unit Hit@5 | Text Hit@5 | Latency ms | Eval n |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 only | 0.54 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Vector only | 0.38 | 1.00 | 1.00 | 0.85 | 1.00 | 0.3 | 13 |
| Hybrid without temporal filter | 0.62 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Hybrid with temporal filter | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Hybrid + temporal fusion | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.3 | 13 |
| Hybrid + temporal fusion + rerank | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.4 | 13 |

This is a controlled benchmark, not an external benchmark and not a
state-of-the-art claim.

The retrieval ablation is independent of provider mode. It evaluates whether
retrieval returns temporally correct evidence; it does not evaluate LLM writing
quality.

## 9. Metrics

Window Hit@5: whether the top five results contain evidence from the expected
valid-time window.

Top1 Window: whether the first result is from the expected valid-time window.
This is more discriminative than Hit@5 on small controlled corpora.

Source Hit@5: whether the top five results contain the expected source/document.

Unit Hit@5: whether the top five results contain the expected unit signal.

Text Hit@5: whether the top five results contain expected textual clues such as
year, GDP, or per-capita wording.

Latency ms: wall-clock runtime for the method.

## 10. Limitations

- The smoke benchmark is easy by design.
- The hard benchmark has only 15 controlled cases.
- Temporal metadata extraction is partly heuristic.
- The strongest tested path is world-economy style data.
- Full LLM mode depends on local or provider model availability.
- Vertex AI Gemini provider mode is validated as a smoke demo unless a separate
  answer-quality evaluation is added.
- CI currently validates light mode, not full model-backed generation.
- ChronoSanity quality depends on passage granularity and metadata quality.
- The system is not production-hardened for authentication, multi-tenancy,
  monitoring, or deployment.

## 11. Reproducibility

Run in light mode:

```bash
export CHRONORAG_LIGHT=1
python -m cli.chronorag_cli ingest data/sample/smoke/*

python -m benchmarks.run_ablation \
  --cases benchmarks/temporal_qa_15.jsonl \
  --top-k 5 \
  --candidate-k 50

python -m cli.chronorag_cli purge
python -m cli.chronorag_cli ingest data/sample/hard_temporal/*

python -m benchmarks.run_ablation \
  --cases benchmarks/temporal_qa_hard_15.jsonl \
  --top-k 5 \
  --candidate-k 50 \
  --out benchmarks/results/temporal_qa_hard_15_results.json
```

Optional Vertex provider smoke mode:

```bash
export CHRONORAG_LIGHT=0
export CHRONORAG_PROVIDER=vertex
export GOOGLE_CLOUD_PROJECT=ginkgo-2026
export GOOGLE_CLOUD_LOCATION=us-central1
export VERTEX_MODEL_ID=gemini-2.5-flash
python -m benchmarks.run_provider_smoke
```
