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
- Persistent vector database abstraction
- BM25 lexical retrieval
- Vector retrieval
- Temporal filtering
- Monotone temporal fusion
- Optional reranking
- ChronoSanity conflict detection
- Answer generation or evidence-only fallback
- Attribution card generation

## 4. Retrieval Pipeline

The retrieval pipeline first gathers candidate passages using lexical and vector
search. Candidates are then checked against requested valid-time windows.
Time-aligned evidence receives priority before answer synthesis.

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

The benchmark is a small 3-query sanity check over world-economy style sample
data. It is not an external benchmark and should not be presented as SOTA.

The observed result is that non-temporal retrieval can find relevant
source/topic/unit evidence, but fails valid-window correctness. Adding temporal
filtering and fusion improves Window Hit@5 from 0.00 to 1.00 on the current
sanity benchmark.

## 9. Metrics

Window Hit@5: whether the top five results contain evidence from the expected
valid-time window.

Source Hit@5: whether the top five results contain the expected source/document.

Unit Hit@5: whether the top five results contain the expected unit signal.

Text Hit@5: whether the top five results contain expected textual clues such as
year, GDP, or per-capita wording.

Latency ms: wall-clock runtime for the method.

## 10. Limitations

- The benchmark has only three cases.
- Temporal metadata extraction is partly heuristic.
- The strongest tested path is world-economy style data.
- Full LLM mode depends on local or provider model availability.
- CI currently validates light mode, not full model-backed generation.
- ChronoSanity quality depends on passage granularity and metadata quality.
- The system is not production-hardened for authentication, multi-tenancy,
  monitoring, or deployment.

## 11. Reproducibility

Run in light mode:

```bash
export CHRONORAG_LIGHT=1
python -m cli.chronorag_cli ingest \
  data/sample/docs/aihistory1.txt \
  data/sample/docs/aihistory2.txt \
  data/sample/docs/aihistory3.txt

python -m benchmarks.run_ablation \
  --cases benchmarks/temporal_qa_sample.jsonl \
  --top-k 5 \
  --candidate-k 150
```
