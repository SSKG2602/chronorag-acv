# ChronoRAG Technical Report

## Abstract

ChronoRAG is a temporal retrieval-augmented generation research scaffold for
time-sensitive question answering. It treats validity windows, transaction
windows, provenance, and temporal alignment as first-class retrieval
constraints. The current implementation is evaluated primarily as a temporal
retrieval and grounding framework. It is a reproducible prototype, not a
production service, not a SOTA claim, and not publication-grade proof.

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

Supporting modules still exist around this main path. DHQC is an active
controller helper that plans retrieval-hop budgets from simple coverage and
authority signals. Historical experimental Layer 2A paths are outside the
current TCC plus Layer 1B checkpoint claim.

## 4. Retrieval Pipeline

Before retrieval, ChronoRAG needs chunk records that carry both searchable
context and trustworthy temporal metadata. Temporal Contextual Chunking is
ChronoRAG's chunking strategy, inspired by contextual retrieval but extended for
valid-time retrieval, transaction-time tracking, temporal fusion, ChronoSanity,
and attribution.

The method separates unchanged `raw_text` from `retrieval_text`. `raw_text`
remains the quoteable evidence used for attribution and answer grounding.
`retrieval_text` may add a short context prefix with document title, section,
unit, entity, region, and temporal scope. This gives BM25/vector retrieval more
structured context without letting generated context overwrite the source
evidence.

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
It validates that the pipeline runs over a small local dataset. The older v1
hard benchmark is archived as a diagnostic because it had only 15 cases, 19
rows/chunks, and limited source diversity.

Temporal Eval v2 is now the main controlled retrieval benchmark. It is built
from multiple source families under `data/raw/temporal_eval_v2/` and generated
into `data/sample/temporal_eval_v2/`. It has six case categories:

- exact valid-time retrieval
- same entity / wrong year traps
- broad-window distractors
- transaction-time vs valid-time traps
- conflict / ChronoSanity cases
- expected partial, refusal, or ambiguous cases

Current Temporal Eval v2 light-mode result:

| Method | Hit@5 Evidence | Top1 Window | Hit@5 Window | Source Family Hit@5 | Distractor Avoidance | Proxy Conflict Correct | Proxy Partial/Refusal Correct | Proxy Behavior Correct | Latency ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 only | 0.47 | 0.47 | 0.80 | 0.73 | 0.73 | 0.00 | 0.07 | 0.33 | 1.96 |
| Vector only | 0.47 | 0.53 | 0.80 | 0.93 | 0.73 | 0.00 | 0.07 | 0.33 | 1.93 |
| Hybrid without temporal filter | 0.53 | 0.47 | 0.80 | 0.80 | 0.73 | 0.07 | 0.07 | 0.27 | 1.94 |
| Hybrid with temporal filter | 0.67 | 0.60 | 0.93 | 0.80 | 0.73 | 0.07 | 0.13 | 0.47 | 2.00 |
| Hybrid + temporal fusion | 0.60 | 0.80 | 0.93 | 0.87 | 0.93 | 0.07 | 0.07 | 0.60 | 2.00 |
| Hybrid + temporal fusion + rerank | 0.80 | 0.80 | 0.93 | 0.87 | 0.93 | 0.07 | 0.07 | 0.80 | 2.08 |

Temporal Eval v2 is a controlled benchmark, not an external benchmark and not a
broad performance claim. It makes `Source Hit@5` more meaningful than v1 because
it includes multiple source families, but Layer 2 generalization still requires
at least one second domain and a larger natural benchmark.

The retrieval ablation is independent of provider mode. It evaluates whether
retrieval returns temporally correct evidence; it does not evaluate LLM writing
quality.

Current E2 validates temporal retrieval behavior. It does not fully validate
LLM-mediated answer decisions. Conflict and refusal are system-level behaviors
that require answer-time reasoning over retrieved evidence, evidence cards,
ChronoSanity signals, and answer validation. These belong in Layer 1B, not Layer
2.

Layer 1B is implemented as `benchmarks/run_temporal_answer_validation_v2.py`.
Light mode is deterministic and CI-safe. Vertex mode runs the ChronoRAG grounded
temporal synthesis prompt through Vertex Gemini and uses hybrid lexical + BGE
vector retrieval by default. Passing `--skip-vector` is an explicit downgrade for
machines that cannot run local embeddings.

The Layer 1B Vertex path validates the prompt contract, extracts raw/fenced or
short prose-wrapped JSON, normalizes harmless schema shape drift, validates
response schema, checks cited evidence IDs, and applies deterministic
temporal-rule validation. Provider JSON Parse Failure is treated as a
provider-output contract failure, not as temporal reasoning failure. One retry
is allowed only for provider-contract failures; grounding and temporal-rule
failures are not retried away. A failed retry cannot overwrite a usable initial
response.

A full Vertex 15-case run has been executed. Its analysis showed
answer-completeness and provider-output contract issues rather than grounding or
temporal-rule failures. The follow-up refinement simplified the prompt, added
schema normalization, preserved usable initial output across retries, and kept
default `--top-k 5` and the embedding model unchanged while preserving the
controlled benchmark framing. Comparative runs can be stored with
`--result-suffix` without changing default result paths. The final cleanup
accepts correct q02/q11/q13 behavior via deterministic validation while keeping
grounding, valid-time, and transaction-time checks strict.

The stored primary Layer 1B result is
`benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`.
It uses top-k 5 and reports 0.80 answer overall pass, 1.00 expected evidence
citation, 1.00 valid-time correctness, 1.00 transaction-time trap avoidance,
1.00 provider-contract pass, 1.00 grounding validation pass, and 0.93 temporal
rule validation pass. The non-passing cases are q08, q11, and q14. The dynamic
top-k run is stored separately as a diagnostic result and is not the primary
benchmark claim.

Layer 2A extends the controlled setting to a generated cross-domain local
benchmark path. Its active retrieval methods are `metadata_temporal_rag` and
`chronorag_full`. Deterministic Layer 2A validation measures retrieval only. It
uses `selected_evidence_ids` and scores expected evidence Hit@1/Hit@k,
acceptable evidence Hit@k, forbidden evidence absent@k, and category-specific
temporal checks such as wrong-time/date trap avoidance, valid-time versus
transaction-time separation, exact-vs-broad preference, source/metric
constraints, cross-domain comparison coverage, and multi-slot temporal
coverage.

The Layer 2A v3 question set is generated from corpus rows and removes
hidden-target cases. If an expected row is exact-dated, the question includes
that exact date; source-specific, metric-specific, version-specific, comparison,
and multi-slot cases expose the relevant source, metric/version, entity, and
date anchors. `conflict_detection` is not scored in v3 because the current
corpus has no real two-sided conflict pairs; this is recorded as a data-contract
blocked diagnostic rather than filled with synthetic IDs.

Temporal constraints are polarity-aware in retrieval scoring. Target temporal
mentions are positive constraints. Dates or times governed by local phrases such
as `not`, `rather than`, `instead of`, `excluding`, or `as opposed to` are
negative constraints. This supports contrastive temporal queries such as `use
1990-04-20, not 1990-03-28` while keeping deterministic Layer 2A validation
focused on selected evidence IDs.

After temporal fusion, `chronorag_full` applies a small retrieval-finalization
pass for Layer 2A evidence selection. The pass cleans exact-time neighbors,
separates valid-time from transaction-time candidates, applies source/metric
aware score adjustments, and conservatively diversifies top-k evidence for
comparison or conflict-style queries. It is a final evidence-selection policy,
not an embedding retrieval patch or a generated-answer quality claim.

Layer 2A deterministic validation does not judge generated answer wording,
behavior labels, required or forbidden fact strings in the answer,
clarification/refusal/conflict-warning wording, confidence, formatting, style,
or explanation quality. Dry-run outputs are prompt-generation artifacts only;
placeholder answers such as `DRY RUN: prompt generated without provider call.`
must not be interpreted as answer-quality results. Generated answer quality is
reserved for a separate provider-backed grounded answer judge. Current Layer 2A
status is controlled benchmark/debugging, not a public performance proof.

The next planned Layer 2A step is a fresh 50-case and 200-case retrieval-only
rerun with temporal-intent and finalization handling. Active hybrid retrieval
with embeddings remains a separate future patch if the retrieval-only results
show it is needed.

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
- Temporal Eval v2 has 15 controlled cases.
- Generalization beyond controlled local benchmark/debugging data is not yet
  proven.
- Layer 2A deterministic scores are retrieval scores, not generated answer
  quality scores.
- Temporal metadata extraction is partly heuristic.
- The strongest tested path is world-economy style data.
- Full LLM mode depends on local or provider model availability.
- Vertex AI Gemini provider mode is validated as a smoke demo unless a separate
  answer-quality evaluation is added.
- CI currently validates light mode, not full model-backed generation.
- ChronoSanity quality depends on passage granularity and metadata quality.
- Graph retrieval is not implemented in the current system. The graph-path
  module is a disabled stub, so graph-based reasoning is not part of the
  current proof.
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

python benchmarks/build_temporal_eval_v2.py
python benchmarks/run_temporal_eval_v2.py --light
```

Optional Vertex provider smoke mode:

```bash
export CHRONORAG_LIGHT=0
export CHRONORAG_PROVIDER=vertex
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
export VERTEX_MODEL_ID=gemini-2.5-flash
python -m benchmarks.run_provider_smoke
```
