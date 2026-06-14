# ChronoRAG Technical Report

## Abstract

ChronoRAG is a temporal retrieval and grounded answer-validation RAG framework.
It treats validity windows, transaction/publication times, source provenance,
temporal precision, and grounded citation checks as first-class system
contracts.

The stored benchmarks provide controlled evidence for temporal retrieval
behavior under the datasets and validators described in this report. The
evaluation layers separate temporal retrieval, evidence selection,
answer-contract validation, and component ablation behavior so each result can
be interpreted through its own measurement contract.

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

The 5,000-row corpus is generated benchmark data. The public repository
contains builders, validators, tracked samples, question definitions, final
result artifacts, and commands that distinguish sample files from generated
execution data.

Active methods in the paper-ready standard comparison:

- BM25
- Dense-only
- Date-filter RAG
- Metadata Temporal RAG
- ChronoRAG Full

Final public result files:

- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md`
- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json`

Layer 2A v3 retrieval-only standard comparison:

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 200 | 0.7750 | 0.9350 | 0.8467 | 0.7600 | 0.5750 |
| Dense-only | 200 | 0.3850 | 0.6100 | 0.4710 | 0.7950 | 0.3000 |
| Date-filter RAG | 200 | 0.7750 | 0.9350 | 0.8475 | 0.7650 | 0.6000 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | 0.7678 | 0.6950 | 0.4813 |
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | 0.8554 | 0.9950 | 0.9625 |

The category-primary score is the more meaningful Layer 2A metric because some
categories require slot coverage, forbidden-evidence avoidance, or
source/metric/time constraints rather than generic Hit@k alone. BM25 and
Date-filter RAG have higher broad Hit@5 than ChronoRAG Full, but ChronoRAG Full
has stronger Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass. This
supports temporal-validity retrieval, not generic retrieval superiority.

Metric definitions:

- Hit@k is the fraction of cases where at least one expected or acceptable
  evidence ID appears in the top-k selected evidence set.
- MRR@5 is the mean reciprocal rank of the first expected or acceptable
  evidence ID within top-5.
- Forbidden Absent@5 is the fraction of cases where forbidden evidence IDs are
  absent from top-5.
- Category Primary Pass is the category-specific diagnostic for temporal,
  source/metric, slot, forbidden-evidence, or insufficiency behavior.

Forbidden Absent@5 and Category Primary Pass are constraint-sensitive
diagnostics for temporal-validity retrieval. They are not intended to replace
standard IR metrics; they complement Hit@k and MRR@5 by measuring
temporal-invalidity exclusion and source/category correctness.

Annotation and baseline fairness: the current artifact records benchmark
labels as fixed JSONL fields. The labels are author-created and treated as
fixed before method scoring. Large-scale independent annotation is not included
in this version and is listed as a limitation. Standard retrieval baselines use
the same corpus, same queries, same top-k=5, same evaluator, and same candidate
corpus where applicable, and they do not use ChronoRAG's Temporal Contextual
Chunking, valid-time / transaction-time separation, temporal fusion,
forbidden-time suppression, or finalization logic.

## 9. Benchmark Correction And Failure Analysis

Several public-branch corrections were made before treating Layer 2A v3 as the
current retrieval-only result:

- Earlier broad-window style questions were reframed because vague year-only
  wording cannot fairly require a hidden exact date.
- Earlier conflict-detection questions were removed from scored v3 categories
  because real paired contradiction rows were absent in the current corpus.
- Earlier intermediate Layer 2 Vertex and judge artifacts were archived because
  they were not the final Layer 2A retrieval-only result.
- The v3 benchmark aligns question wording, expected evidence, and available
  corpus rows more strictly.
- The correction improved benchmark validity rather than hiding failures.

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
- Score-only ranking can improve broad recall while degrading temporal
  validity.
- Several ablations remain strong on explicitly anchored categories; those
  categories should be interpreted as controlled checks of the corresponding
  category contracts.

### Retrieval Score Optimization Degrades Temporal Validity

The Score-only ablation achieved the highest raw Hit@5 at 0.9850, but
Forbidden Absent@5 fell to 0.6500 and Category Primary Pass fell to 0.5625.
ChronoRAG Full achieved lower broad Hit@5 at 0.8950 but much stronger
Forbidden Absent@5 at 0.9950 and Category Primary Pass at 0.9625. This
demonstrates that unconstrained retrieval score optimization and
temporal-validity retrieval are different objectives.

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
| LLM judge overall pass | 38 / 50 = 76% |
| LLM judge semantic pass | 48 / 50 = 96% |
| Strict combined pass | 35 / 50 = 70% |
| Manually accepted validator-strictness cases | 3 |
| Manual-audited acceptable pass | 41 / 50 = 82% |

The strict combined score, `35 / 50 = 70%`, remains the primary conservative
Layer 2B result because it requires both hard validation and LLM judge pass. The
manual-audited acceptable score, `41 / 50 = 82%`, is a secondary interpretation
after accepting 3 validator-strictness cases reviewed by the judge and a human
audit. It does not replace the strict combined score.

Layer 2B evaluates answer synthesis and answer validation. Retrieval-quality
behavior is evaluated separately in Layer 2A through selected-evidence metrics,
forbidden-evidence checks, source/metric constraints, and slot-coverage
criteria.

### LLM Post-Filtering Does Not Replace Retrieval-Layer Temporal Grounding

BM25 + LLM, Dense-only + LLM, and Date-filter RAG + LLM were evaluated with
the same 50 QA cases, same corpus, same top-k=5, same Gemini 2.5 Flash model,
same temperature 0.0, same prompt template, and same validator/judge settings.
Despite explicit instructions to distinguish valid time from transaction time,
these baselines reached only 0.4000, 0.3200, and 0.4000 strict combined pass
respectively. ChronoRAG Full's prior answer-level result reached 0.7000 strict
combined pass, 0.7600 hard-contract pass, 0.9600 judge semantic pass, 0.9800
expected evidence citation, and 0.8400 valid-time correctness.

Baseline methods are evaluated without evidence injection. ChronoRAG
pre-injection evidence availability is the fair retrieval-availability
comparison point. ChronoRAG post-injection answer-level results are reported
separately to show performance when expected evidence is available to the
generator. In the extracted QA50 artifacts, pre-injection any expected evidence
is 0.7400 (37/50), pre-injection all expected evidence is 0.6400 (32/50), and
post-injection evidence available is 1.0000 (50/50).

Strict Combined Pass requires both deterministic hard-contract validation and
judge pass. Deterministic Hard-Contract Pass is the rule-based answer-contract
validation signal. Judge Semantic Pass is the LLM judge semantic
answer-correctness signal. Valid Time Correct checks whether the answer uses
the requested valid time rather than an unrelated transaction, publication,
filing, release, or ingestion time.

## 12. Related-Work Positioning

Temporal databases provide foundational valid-time / transaction-time
distinctions. ChronoRAG operationalizes this distinction for RAG evidence
selection over messy unstructured or semi-structured corpora. Temporal QA
datasets such as SituatedQA and TimeQA study temporally conditioned question
answering, but ChronoRAG focuses on retrieval-layer temporal role separation.
Temporal IR and temporal summarization work study time-sensitive retrieval and
summarization, but ChronoRAG focuses on multi-role temporal evidence selection
for downstream RAG.

## 13. Reproducibility Commands

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

## 14. Paper Preparation Assets

Paper-facing source notes, qualitative case extracts, and figure captions are
available in:

- `docs/PAPER_SOURCE_NOTES.md`
- `docs/PAPER_QUALITATIVE_CASES.md`
- `docs/PAPER_FIGURE_INDEX.md`
- `docs/paper_assets/`
- `docs/paper_assets/chrono_tables_index.md`

## 15. Technical Limitations

### Temporal Expression Parsing

ChronoRAG currently relies on explicit or reliably extractable temporal
expressions. More robust handling of relative, implicit, underspecified, and
fuzzy temporal references remains an important technical extension.

### Rule-Weighted Temporal Fusion

The current temporal fusion layer uses explicitly designed scoring signals. A
learned temporal reranker could adapt the relative importance of semantic
relevance, valid-time fit, transaction-time role, interval overlap, and
forbidden-time penalties across different domains.

### Multi-Hop Temporal Reasoning

ChronoRAG focuses on temporally valid evidence selection and slot-aware
assembly. Extending the framework to multi-hop temporal reasoning, where
answers require ordered chains of evidence across multiple events or intervals,
remains future work.

### Temporal Contradiction Modeling

ChronoSanity detects temporally inconsistent or role-conflicting evidence in
retrieved candidates. Future work should extend this into explicit temporal
contradiction modeling, including contradiction type classification and
contradiction severity scoring.

### Temporal Confidence Calibration

The current framework exposes confidence and attribution metadata, but
calibrated uncertainty estimation for temporal fit, conflict likelihood, and
answer validity remains an open extension.

### Joint Optimization of Evidence Finalization

Source-aware, metric-aware, and slot-aware finalization are implemented as
modular retrieval-time controls. A future version can investigate whether these
controls can be jointly optimized through learning-based evidence selection.

### Interpretability Visualization

The repository includes numerical retrieval tables, ablation results, a
retrieval-only temporal feature heatmap, and a one-query trace. Broader
interpretability coverage, such as more per-category traces and before/after
evidence finalization diagrams, remains future work.

### Evaluation Threats To Validity

The 50-case answer-level evaluation is directional and should be scaled.
Forbidden Absent@5 and Category Primary Pass are custom metrics and depend on
benchmark label quality. Labels are author-created unless independent
annotation evidence exists. The corpus is controlled and cross-domain but not a
public temporal QA benchmark. Fusion-weight sensitivity and reranker isolation
were not run because no safe runtime switches exist. Generalization beyond
financial, regulatory, macroeconomic, market, and software-release evidence is
future work. ChronoRAG depends on temporal extraction quality.

## 16. Future Work

Future work will focus on strengthening the temporal modeling layer rather than
changing the core motivation of the framework.

1. Robust temporal expression normalization for relative, fuzzy, implicit, and
   underspecified dates.
2. Learned temporal reranking over semantic relevance, valid-time fit,
   transaction-time role, interval overlap, and forbidden-time penalties.
3. Multi-hop temporal reasoning over ordered evidence chains.
4. Explicit temporal contradiction modeling with contradiction type and
   severity classification.
5. Calibrated temporal confidence estimation for evidence fit, conflict
   likelihood, and answer validity.
6. Joint optimization of temporal fusion and source-aware, metric-aware, and
   slot-aware evidence finalization.
7. Broader interpretability tools such as additional temporal score heatmaps,
   evidence-ranking traces, attribution-flow graphs, and before/after
   finalization visualizations.
8. Advanced slot-aware evidence planning for comparison, aggregation, and
   multi-entity temporal queries.
9. Automatic extraction of valid-time and transaction-time roles from raw
   documents.
10. Harder temporal benchmark cases focused on reasoning patterns,
    contradiction, temporal ordering, and interval logic.
