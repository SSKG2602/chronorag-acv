# ChronoRAG Technical Report

## Abstract

ChronoRAG is a temporal retrieval and grounded answer-validation RAG framework.
It treats validity windows, transaction/publication times, source provenance,
temporal precision, and grounded citation checks as first-class system
contracts.

The stored benchmarks provide controlled evidence for temporal retrieval
behavior under explicitly scoped datasets and validators. The claims are limited
to the tested settings: temporal retrieval, evidence selection, answer-contract
validation, and component ablation behavior. The project does not generalize
these results beyond the benchmark conditions without additional evaluation.

## 1. Problem Statement

Temporal QA fails when a system retrieves topically relevant but temporally
wrong evidence. Common failures include wrong-year rows, broad historical
windows, publication time used as valid time, negated dates treated as targets,
and comparison questions where one slot dominates the retrieved context.

ChronoRAG studies these failures as retrieval and grounding problems before
asking an LLM to write an answer.

## 2. Temporal Model

ChronoRAG separates:

- `valid_time`: when a claim is true in the world.
- `transaction_time`: when the claim was observed, filed, published, released,
  ingested, or otherwise entered the system.
- Query time: the temporal target requested by the user or benchmark question.

This separation is enforced in retrieval scoring, answer prompts, and answer
validation. A publication or filing timestamp is not treated as valid time
unless the question explicitly asks for publication, filing, release, or
transaction timing.

## 3. Retrieval Architecture

The current public path is:

1. Ingest rows/documents with provenance and temporal metadata.
2. Build Temporal Contextual Chunks.
3. Store raw evidence separately from retrieval text.
4. Retrieve candidates with lexical/vector-compatible surfaces.
5. Score temporal precision at year, month, day, timestamp, range, quarter, and
   fuzzy granularities.
6. Apply polarity-aware temporal constraints, including negative dates.
7. Fuse relevance, temporal alignment, authority, and transaction-role
   penalties with monotone temporal fusion.
8. Finalize selected evidence with source/metric and slot-aware policies.
9. Optionally synthesize a grounded answer.
10. Validate citations, temporal role use, provider contract, and behavior.

Temporal Contextual Chunking is the evidence representation layer. It preserves
unchanged `raw_text` for attribution while creating `retrieval_text` with
document title, section, entity, unit, region, source, and temporal context.

Temporal precision scoring is separate from embedding similarity. Stronger
embeddings can improve candidate quality, but exact-date and transaction-role
behavior are symbolic contracts.

## 4. Evidence Finalization

Layer 2A exposed that ranking alone is not enough for hard temporal retrieval.
ChronoRAG therefore applies a final evidence-selection pass after temporal
fusion. The pass:

- prefers exact valid-time evidence over broad windows when exact evidence is
  available;
- keeps valid-time evidence separate from transaction-time-only evidence;
- respects local negative temporal constraints such as `not 1990-03-28`;
- applies source and metric/form constraints;
- assembles comparison and multi-slot evidence so all required slots can appear
  in top-k.

This is retrieval behavior, not answer-generation behavior.

## 5. Evaluation Layers

| Layer | Scope | Evaluated Behavior | Boundary |
|---|---|---|---|
| Layer 1A | Temporal Eval v2 retrieval | Evidence selection, window alignment, distractor avoidance, proxy behavior. | Retrieval-focused benchmark. |
| Layer 1B | Temporal answer validation | Cited evidence, valid-time correctness, transaction-time trap avoidance, provider/output contract. | Answer-contract validation in a controlled setting. |
| Layer 2A | Cross-domain retrieval-only | Selected evidence IDs across 5,000 corpus rows and 200 v3 questions. | No generated natural-language answer scoring. |
| Layer 2B | Natural-language temporal QA | ChronoRAG answer synthesis, hard-contract validation, LLM judge scoring, and manual audit. | Answer synthesis and validation with expected evidence available where needed; retrieval quality remains Layer 2A. |

## 6. Layer 1A: Temporal Eval v2

Layer 1A is the controlled temporal retrieval benchmark.

Files:

- `benchmarks/run_temporal_eval_v2.py`
- `benchmarks/temporal_eval_v2_15.jsonl`
- `data/sample/temporal_eval_v2/`
- `benchmarks/results/temporal_eval_v2_results.md`
- `benchmarks/results/temporal_eval_v2_results.json`

Stored light-mode result:

| Method | Hit@5 Evidence | Top1 Window | Hit@5 Window | Source Family Hit@5 | Distractor Avoidance | Proxy Behavior Correct |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid + temporal fusion + rerank | 0.80 | 0.80 | 0.93 | 0.87 | 0.93 | 0.80 |

Layer 1A measures retrieval and proxy behavior over a 15-case controlled set.
It tests whether temporally correct evidence appears in top-k and whether
nearby temporal distractors are avoided.

## 7. Layer 1B: Temporal Answer Validation

Layer 1B evaluates answer behavior after temporal retrieval. It supports:

- dry-run prompts, with no provider call;
- deterministic light mode;
- Vertex mode, with grounded answer synthesis and contract validation.

Files:

- `benchmarks/run_temporal_answer_validation_v2.py`
- `benchmarks/temporal_answer_validation_v2_15.jsonl`
- `benchmarks/results/temporal_answer_validation_v2_*.md`
- `benchmarks/results/temporal_answer_validation_v2_*.json`

The primary stored Vertex top-k 5 result is
`benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`.
It reports:

| Metric | Score |
|---|---:|
| Answer Overall Pass | 0.80 |
| Required Facts Present | 0.80 |
| Expected Evidence Cited | 1.00 |
| Valid-Time Correct | 1.00 |
| Transaction-Time Trap Avoided | 1.00 |
| Provider Contract Pass | 1.00 |
| Grounding Validation Pass | 1.00 |
| Temporal Rule Validation Pass | 0.93 |

Provider JSON failures are treated as provider/output-contract failures, not as
retrieval wins or losses. A failed retry cannot overwrite a usable initial
response.

## 8. Layer 2A: Cross-Domain Retrieval-Only

Layer 2A expands retrieval evaluation to a selected cross-domain corpus:

- about 46,503 detected rows/items in the larger raw pool;
- 5,000 selected corpus rows for controlled benchmark execution;
- 200 v3 aligned temporal questions;
- FRED macro, market/index, SEC submissions, Federal Register, and GitHub
  release source families;
- retrieval-only scoring over `selected_evidence_ids`;
- no Vertex and no generated answer scoring in the public result.

The full 5,000-row corpus is generated/working benchmark data and may not be
fully tracked in Git. The public repository contains builders, validators,
tracked samples, question definitions, final result artifacts, and commands
that distinguish sample files from generated full-corpus files.

Active methods:

- `chronorag_full`
- `metadata_temporal_rag`

Final public result files:

- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md`
- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json`
- `benchmarks/layer2_crossdomain/results/conflict_data_contract_blocked_v3.md`
- `benchmarks/layer2_crossdomain/results/conflict_data_contract_blocked_v3.json`

Layer 2A v3 retrieval-only summary:

| Method | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass |
|---|---:|---:|---:|---:|---:|
| `chronorag_full` | 200 | 0.82 | 0.90 | 0.99 | 0.96 |
| `metadata_temporal_rag` | 200 | 0.69 | 0.86 | 0.69 | 0.48 |

The category-primary score is the more meaningful Layer 2A metric because some
categories require slot coverage, forbidden-evidence avoidance, or
source/metric/time constraints rather than generic Hit@k alone.

## 9. Benchmark Correction And Failure Analysis

Several public-branch corrections were made before treating Layer 2A v3 as the
current retrieval-only result:

- Earlier broad-window style questions were reframed because vague year-only
  wording cannot fairly require a hidden exact date.
- Earlier conflict-detection questions were blocked because real conflict-pair
  evidence rows were absent in the current corpus.
- Earlier intermediate Layer 2 Vertex and judge artifacts were archived because
  they were not the final Layer 2A retrieval-only result.
- The v3 benchmark aligns question wording, expected evidence, and available
  corpus rows more strictly.
- The correction improved benchmark validity rather than hiding failures.

The conflict status is documented in:

- `benchmarks/layer2_crossdomain/results/conflict_data_contract_blocked_v3.md`
- `benchmarks/layer2_crossdomain/results/conflict_data_contract_blocked_v3.json`

Synthetic conflict IDs are not used in the public v3 scoring path.

## 10. Ablation Interpretation

The public ablation file evaluates:

| Variant | Interpretation Boundary |
|---|---|
| `chronorag_full` | Full ChronoRAG retrieval and finalization path. |
| `chronorag_no_tcc` | Tests whether TCC retrieval text and temporal metadata help in this selected corpus. |
| `chronorag_no_temporal_precision` | Tests exact-time ranking, broad-window preference, and wrong-time suppression. |
| `chronorag_no_transaction_role` | Tests final valid-time versus transaction-time cleanup. |
| `chronorag_no_source_metric` | Tests source and metric/form normalization. |
| `chronorag_no_slot_assembler` | Tests comparison and multi-slot evidence coverage. |
| `chronorag_score_only` | Tests ranking without final evidence-selection components. |
| `metadata_temporal_rag` | Provides a metadata-oriented retrieval comparison point. |

Stored result:

- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`

Main interpretation:

- Temporal precision contributes to wrong-time suppression and exact-time
  ranking.
- Slot assembly contributes strongly to multi-slot and cross-domain coverage.
- Score-only ranking is weaker than final evidence selection in the v3 tested
  setting.
- Several ablations remain strong on explicitly anchored categories; those
  categories should be interpreted as controlled checks, not broad proof.

## 11. Layer 2B: Full-50 Answer Synthesis And Validation

Layer 2B is the completed natural-language temporal QA evaluation. It uses 50
manually designed temporal QA cases built from evidence cards in the selected
Layer 2 corpus:

- `benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl`

The completed Layer 2B path is:

1. ChronoRAG answer synthesis with Vertex.
2. Dynamic top-k evidence selection for answer context.
3. Deterministic hard-contract validation.
4. LLM judge semantic scoring.
5. Human manual audit of validator-strictness cases.

Final Layer 2B artifacts:

- `benchmarks/layer2_crossdomain/results/layer2b_manual_50_qa_summary.md`
- `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.md`
- `benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.md`
- `benchmarks/layer2_crossdomain/results/layer2b_full50_manual_audit.md`

Final Layer 2B scores:

| Metric | Score |
|---|---:|
| Deterministic hard-contract pass | 38 / 50 = 76% |
| LLM judge semantic pass | 38 / 50 = 76% |
| Strict combined pass | 35 / 50 = 70% |
| Manually accepted validator-strictness cases | 3 |
| Manual-audited acceptable pass | 41 / 50 = 82% |

The strict combined score, `35 / 50 = 70%`, remains the primary conservative
Layer 2B result because it requires both hard validation and LLM judge pass. The
manual-audited acceptable score, `41 / 50 = 82%`, is a secondary interpretation
after accepting 3 validator-strictness cases reviewed by the judge and a human
audit. It does not replace the strict combined score.

Layer 2B evaluates answer synthesis and answer validation. It does not prove
retrieval quality because expected evidence was available or injected where
needed for answer generation. Retrieval quality is evaluated separately in
Layer 2A.

## 12. Reproducibility Commands

Layer 1A:

```bash
python3 benchmarks/build_temporal_eval_v2.py
python3 benchmarks/run_temporal_eval_v2.py --light
```

Layer 1B dry-run:

```bash
python3 benchmarks/run_temporal_answer_validation_v2.py \
  --mode vertex \
  --dry-run-prompts \
  --top-k 5 \
  --result-suffix dry_run_prompts
```

Layer 1B light mode:

```bash
python3 benchmarks/run_temporal_answer_validation_v2.py \
  --mode light \
  --top-k 5
```

Layer 2A dataset validation:

```bash
python3 benchmarks/layer2_crossdomain/validate_layer2_dataset.py \
  --corpus benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl \
  --questions benchmarks/layer2_crossdomain/data/layer2_questions.jsonl
```

Layer 2A retrieval comparison:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_comparison.py \
  --method all \
  --mode dry_run \
  --dataset real \
  --limit 200 \
  --top-k 5 \
  --result-suffix v3_200

python3 benchmarks/layer2_crossdomain/evaluate_retrieval_only.py \
  --results benchmarks/layer2_crossdomain/results/layer2_chronorag_full_v3_200_results.json \
            benchmarks/layer2_crossdomain/results/layer2_metadata_temporal_rag_v3_200_results.json \
  --questions benchmarks/layer2_crossdomain/data/layer2_questions.jsonl \
  --save-json benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json \
  --save-md benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md
```

Layer 2A ablation:

```bash
python3 benchmarks/layer2_crossdomain/run_layer2_ablations.py \
  --corpus benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl \
  --questions benchmarks/layer2_crossdomain/data/layer2_questions.jsonl \
  --mode dry_run \
  --limit 200 \
  --top-k 5 \
  --result-suffix v3_ablation200
```

## 13. Limitations

- Layer 2A is retrieval-only.
- Layer 2A does not evaluate generated natural-language answer quality.
- Layer 2B evaluates answer synthesis and validation, not retrieval quality,
  because expected evidence was available where needed.
- The Layer 2B manual-audited acceptable score is secondary and does not replace
  the strict combined score.
- Layer 1B is controlled answer validation, not production reliability proof.
- Conflict detection is data-contract blocked in Layer 2A until real
  conflict-pair rows exist.
- The current service is not production-hardened for multi-tenant storage,
  authentication, observability, or deployment.
