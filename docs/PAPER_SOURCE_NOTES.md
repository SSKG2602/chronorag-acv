# Paper Source Notes

## Title

ChronoRAG: Temporal Retrieval and Grounded Answer Validation for RAG Systems

## Author

Shreyas Gowda S

Email: mynameisshreyasshashi@gmail.com

## Repository

https://github.com/SSKG2602/chronorag

## Paper Framing

ChronoRAG is a temporal evidence selection and answer-validation framework for
retrieval-augmented generation systems where factual correctness depends on
valid-time grounding rather than topical relevance alone.

## Repository-to-Paper Naming Map

| Repository name | Paper-facing name |
|---|---|
| Layer 1A | Controlled Temporal Retrieval Evaluation |
| Layer 1B | Temporal Answer-Contract Validation |
| Layer 2A | Cross-Domain Retrieval Benchmark |
| Layer 2B | Natural-Language Temporal QA Evaluation |
| Light Mode | Deterministic evaluation mode |
| Vertex Mode | Provider-backed answer generation setting |
| ChronoRAG Full | Proposed method |
| Metadata Temporal RAG | Temporal metadata baseline |
| BM25 | Standard lexical retrieval baseline |
| Dense-only | Standard embedding retrieval baseline |
| Date-filter RAG | Naive string date-filter baseline |
| Score Only | Scoring-only ablation |
| No Temporal Precision | Temporal precision ablation |
| No Slot Assembler | Slot-assembly ablation |

## Core Contributions

1. Valid-time and transaction-time separation for temporal RAG evidence selection.
2. Temporal precision scoring across year, month, day, timestamp, quarter,
   range, and fuzzy range matches.
3. Temporal fusion combining semantic relevance, valid-time fit, interval
   overlap, as-of preference, and transaction-role penalties.
4. Negative and forbidden-time handling to prevent excluded dates from entering
   final evidence.
5. Source-aware, metric-aware, and slot-aware evidence finalization.
6. ChronoSanity conflict checks for temporally inconsistent or role-conflicting
   evidence.
7. Answer-contract validation for citation behavior, valid-time correctness,
   transaction-time role, grounding, and output shape.
8. Retrieval metrics that expose temporal evidence validity beyond generic Hit@k.

## Applications

ChronoRAG is useful in time-dependent retrieval settings where the answer must
be supported by evidence valid at the requested time. Relevant applications
include financial and macroeconomic question answering, SEC filing and
corporate-event retrieval, regulatory and legal temporal search, software
release and version-history question answering, audit and compliance evidence
retrieval, historical statistical datasets, and enterprise knowledge bases with
changing policies.

## Dataset and Evaluation Summary

| Item | Repository fact | Source |
|---|---|---|
| Layer 1A case count | 15 controlled temporal retrieval cases. | `docs/BENCHMARK_TEMPORAL_EVAL_V2.md`; `benchmarks/results/temporal_eval_v2_results.md` |
| Layer 1A corpus | 191 rows across 6 source families in the stored result. | `benchmarks/results/temporal_eval_v2_results.md` |
| Layer 1A source families | `maddison_project_2023`, `owid_maddison_gdppc`, `owid_maddison_gdp`, `owid_global_gdp_long_run`, `oecd_world_economy_pdf`, `synthetic_temporal_traps`. | `docs/BENCHMARK_TEMPORAL_EVAL_V2.md`; `benchmarks/results/temporal_eval_v2_results.md` |
| Layer 1B case count | 15 answer-validation cases. | `docs/ANSWER_VALIDATION_BENCHMARK_V2.md`; `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md` |
| Layer 2A raw pool | About 46,503 detected rows/items across five source families. | `README.md`; `docs/TECHNICAL_REPORT.md`; `benchmarks/layer2_crossdomain/assets/corpus_scale.md`; `benchmarks/layer2_crossdomain/data/README.md` |
| Layer 2A selected corpus | 5,000 selected cross-domain corpus rows. | `README.md`; `docs/TECHNICAL_REPORT.md`; `benchmarks/layer2_crossdomain/README.md` |
| Layer 2A question count | 200 v3 aligned temporal questions. | `README.md`; `docs/TECHNICAL_REPORT.md`; `benchmarks/layer2_crossdomain/README.md` |
| Layer 2A source families | FRED macro, market/index, SEC submissions, Federal Register, and GitHub releases. | `README.md`; `docs/TECHNICAL_REPORT.md`; `benchmarks/layer2_crossdomain/README.md` |
| Layer 2A categories | Exact valid-time retrieval, same-entity wrong-time trap, valid-time versus transaction-time, cross-domain temporal comparison, source-specific exact time, metric-specific exact time, exact-vs-broad temporal preference, multi-slot temporal coverage, partial/insufficient evidence, and ambiguous-time query. | `benchmarks/layer2_crossdomain/README.md`; `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md` |
| Layer 2B case count | 50 manually designed natural-language temporal QA cases. | `benchmarks/layer2_crossdomain/results/layer2b_manual_50_qa_summary.md`; `docs/TECHNICAL_REPORT.md` |
| Layer 2B evaluation path | ChronoRAG answer synthesis with Vertex, dynamic top-k evidence selection, deterministic hard-contract validation, LLM judge scoring, and manual audit. | `docs/TECHNICAL_REPORT.md`; `benchmarks/layer2_crossdomain/results/README.md` |

## Evaluation Split Names

- Layer 1A: Controlled Temporal Retrieval Evaluation.
- Layer 1B: Temporal Answer-Contract Validation.
- Layer 2A: Cross-Domain Retrieval Benchmark.
- Layer 2B: Natural-Language Temporal QA Evaluation.

## Result Artifact Paths

- Controlled temporal retrieval: `benchmarks/results/temporal_eval_v2_results.md`.
- Temporal answer-contract validation: `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`.
- Cross-domain retrieval benchmark: `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md`.
- Paper-ready standard retrieval comparison: `docs/paper_assets/table1_layer2a_retrieval_standard_comparison.md`.
- Natural-language temporal QA: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.md`, `benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.md`, and `benchmarks/layer2_crossdomain/results/layer2b_full50_manual_audit.md`.
- Ablation study: `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`.
- Paper table index: `docs/paper_assets/chrono_tables_index.md`.

## Benchmark Command Paths

- Layer 1A retrieval runner: `benchmarks/run_temporal_eval_v2.py`.
- Layer 1B answer-validation runner: `benchmarks/run_temporal_answer_validation_v2.py`.
- Layer 2A comparison runner: `benchmarks/layer2_crossdomain/run_layer2_comparison.py`.
- Layer 2A retrieval evaluator: `benchmarks/layer2_crossdomain/evaluate_retrieval_only.py`.
- Layer 2A ablation runner: `benchmarks/layer2_crossdomain/run_layer2_ablations.py`.
- Layer 2B manual QA runner: `benchmarks/layer2_crossdomain/run_layer2b_manual_qa.py`.
- Layer 2B judge runner: `benchmarks/layer2_crossdomain/run_layer2b_judge.py`.

## Model and Configuration Details

| Item | Located detail | Source |
|---|---|---|
| Embedding model | Final Layer 2A result reports `BAAI/bge-small-en-v1.5 / 384` for both ChronoRAG Full and Metadata Temporal RAG. | `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md` |
| Embedding defaults | `CHRONORAG_EMBED_MODEL` defaults to `BAAI/bge-small-en-v1.5`; `CHRONORAG_EMBED_DIM` defaults to `384`. | `benchmarks/layer2_crossdomain/methods/chronorag_full/adapter.py`; `benchmarks/layer2_crossdomain/methods/metadata_temporal_rag/runner.py`; `core/retrieval/vector_ann.py` |
| Reranker model | Cross-encoder reranker default is `bge-reranker-base`. | `app/deps.py`; `core/retrieval/reranker_ce.py` |
| LLM/provider | Vertex AI Gemini provider; default `VERTEX_MODEL_ID` is `gemini-2.5-flash`. | `core/generator/vertex_provider.py`; `docs/PROVIDER_MODE.md` |
| Vertex location | Default `GOOGLE_CLOUD_LOCATION` is `us-central1`. | `core/generator/vertex_provider.py`; `docs/PROVIDER_MODE.md` |
| Top-k values | Layer 1A, Layer 1B, Layer 2A, and Layer 2B cited commands/results use base top-k 5. | `README.md`; `docs/TECHNICAL_REPORT.md`; `benchmarks/layer2_crossdomain/results/README.md` |
| Dynamic top-k | Layer 2B run supports top-k progression `[5, 10, 20, 30]`; full-50 JSONL records dynamic top-k metadata. | `benchmarks/layer2_crossdomain/layer2b_qa.py`; `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl` |
| Temperature | Answer generation uses temperature `0.0` in the Vertex provider and benchmark answer scripts. | `core/generator/vertex_provider.py`; `benchmarks/run_temporal_answer_validation_v2.py`; `benchmarks/layer2_crossdomain/run_layer2b_manual_qa.py` |
| Layer 1B output tokens | Stored top-k 5 Vertex command uses `--max-output-tokens 2048`. | `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md` |
| Layer 2B output tokens | Layer 2B manual QA runner default is `--max-output-tokens 5000`; judge runner default is `--judge-max-output-tokens 5000`. | `benchmarks/layer2_crossdomain/run_layer2b_manual_qa.py`; `benchmarks/layer2_crossdomain/run_layer2b_judge.py` |
| Deterministic mode settings | Light mode is the deterministic evaluation path; `CHRONORAG_LIGHT=1` is documented for local deterministic runs. | `README.md`; `docs/ANSWER_VALIDATION_BENCHMARK_V2.md`; `benchmarks/results/temporal_answer_validation_v2_light_results.md` |
| Provider mode settings | Provider-backed runs use Vertex mode with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `VERTEX_MODEL_ID`. | `docs/PROVIDER_MODE.md`; `benchmarks/run_temporal_answer_validation_v2.py` |
| Hardware/runtime | Not located in current repository documentation. | Repository documentation scan |

## Results Available for Paper

### Controlled Temporal Retrieval

Source: `benchmarks/results/temporal_eval_v2_results.md`

| Method | Hit@5 Evidence | Top1 Window | Hit@5 Window | Source Family Hit@5 | Distractor Avoidance | Proxy Behavior Correct |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid + temporal fusion + rerank | 0.73 | 0.80 | 0.87 | 0.93 | 1.00 | 0.73 |

### Temporal Answer-Contract Validation

Source: `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`

| Run | Overall Pass | Expected Evidence | Valid-Time Correct | Provider Contract | Grounding | Temporal Rules |
|---|---:|---:|---:|---:|---:|---:|
| Vertex top-k 5 | 0.80 | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 |

### Cross-Domain Retrieval Benchmark

Sources: `docs/paper_assets/table1_layer2a_retrieval_standard_comparison.md`,
`docs/paper_assets/table1_layer2a_retrieval_standard_comparison_with_ci.md`,
and `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md`

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 200 | 0.7750 | 0.9350 | 0.8467 | 0.7600 | 0.5750 |
| Dense-only | 200 | 0.3850 | 0.6100 | 0.4710 | 0.7950 | 0.3000 |
| Date-filter RAG | 200 | 0.7750 | 0.9350 | 0.8475 | 0.7650 | 0.6000 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | 0.7678 | 0.6950 | 0.4813 |
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | 0.8554 | 0.9950 | 0.9625 |

ChronoRAG does not maximize broad Hit@5. BM25 and Date-filter RAG have higher
Hit@5, but ChronoRAG Full has stronger Hit@1, MRR@5, Forbidden Absent@5, and
Category Primary Pass. This supports temporal-validity retrieval, not generic
retrieval superiority. Broad retrieval recall is not temporal validity.

Metric definitions: Hit@k is any expected or acceptable evidence in top-k;
MRR@5 is reciprocal rank of the first expected or acceptable evidence in top-5;
Forbidden Absent@5 checks that forbidden evidence is absent from top-5; and
Category Primary Pass is the category-specific temporal, source/metric, slot,
forbidden-evidence, or insufficiency diagnostic. Forbidden Absent@5 and
Category Primary Pass are constraint-sensitive diagnostics that complement
standard IR metrics.

### Natural-Language Temporal QA

Sources: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.md`, `benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.md`, `benchmarks/layer2_crossdomain/results/layer2b_full50_manual_audit.md`

| Metric | Score |
|---|---:|
| Deterministic hard-contract pass | 38 / 50 = 76% |
| LLM judge overall pass | 38 / 50 = 76% |
| LLM judge semantic pass | 48 / 50 = 96% |
| Strict combined pass | 35 / 50 = 70% |
| Manual-audited acceptable pass | 41 / 50 = 82% |

ChronoRAG QA50 extracted values:

| Metric | Score |
|---|---:|
| Strict combined pass | 35 / 50 = 70% |
| Deterministic hard-contract pass | 38 / 50 = 76% |
| LLM judge overall pass | 38 / 50 = 76% |
| LLM judge semantic pass | 48 / 50 = 96% |
| Expected evidence cited | 49 / 50 = 98% |
| Valid time correct | 42 / 50 = 84% |
| Pre-injection any expected evidence | 37 / 50 = 74% |
| Pre-injection all expected evidence | 32 / 50 = 64% |
| Post-injection evidence available | 50 / 50 = 100% |

Baseline methods are evaluated without evidence injection. ChronoRAG
pre-injection evidence availability is the fair retrieval-availability
comparison point. ChronoRAG post-injection answer-level results are reported
separately to show performance when expected evidence is available to the
generator.

### QA50 Standard Retrieval + LLM Temporal Post-Filtering

Sources: `docs/paper_assets/table3_qa50_llm_post_filter_baselines.md` and
`docs/paper_assets/table4_qa50_answer_level_comparison.md`

BM25 + LLM, Dense-only + LLM, and Date-filter RAG + LLM were evaluated with
the same 50 QA cases, same corpus, same top-k=5, same Gemini 2.5 Flash model,
same temperature 0.0, same prompt template, and same validator/judge settings.
Despite explicit instructions to distinguish valid time from transaction time,
these baselines reached only 0.4000, 0.3200, and 0.4000 strict combined pass
respectively. ChronoRAG Full's prior answer-level result reached 0.7000 strict
combined pass, 0.7600 hard-contract pass, 0.9600 judge semantic pass, 0.9800
expected evidence citation, and 0.8400 valid-time correctness.

| Method | Retrieval Hit@5 | Strict Combined Pass | Hard-Contract Pass | Judge Semantic Pass | Valid Time Correct | Expected Evidence Cited |
|---|---:|---:|---:|---:|---:|---:|
| BM25 + LLM | 0.6400 | 0.4000 | 0.4200 | 0.7800 | 0.4600 | 0.5600 |
| Dense-only + LLM | 0.5200 | 0.3200 | 0.3400 | 0.8200 | 0.4400 | 0.4400 |
| Date-filter RAG + LLM | 0.6600 | 0.4000 | 0.4400 | 0.9000 | 0.4600 | 0.5800 |

### Ablation Study

Source: `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`

| Variant | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass |
|---|---:|---:|---:|---:|---:|
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | 0.9950 | 0.9625 |
| No Temporal Precision | 200 | 0.7500 | 0.8500 | 0.9450 | 0.7500 |
| No Slot Assembler | 200 | 0.8300 | 0.8900 | 0.8150 | 0.7750 |
| Score Only | 200 | 0.8150 | 0.9850 | 0.6500 | 0.5625 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | 0.6950 | 0.4813 |

The Score-only ablation achieved the highest raw Hit@5 at 0.9850, but
Forbidden Absent@5 fell to 0.6500 and Category Primary Pass fell to 0.5625.
ChronoRAG Full achieved lower broad Hit@5 at 0.8950 but much stronger
Forbidden Absent@5 at 0.9950 and Category Primary Pass at 0.9625. This
demonstrates that unconstrained retrieval score optimization and
temporal-validity retrieval are different objectives.

## Annotation, Fairness, And Threats To Validity

The current artifact records benchmark labels as fixed JSONL fields. The labels
are author-created and treated as fixed before method scoring. Large-scale
independent annotation is not included in this version and is listed as a
limitation. Standard comparisons use the same corpus, same queries, same
top-k=5, same evaluator, and same candidate corpus where applicable. Gold
expected evidence IDs were not included in LLM baseline prompts.

The 50-case answer-level evaluation is directional and should be scaled.
Forbidden Absent@5 and Category Primary Pass are custom metrics and depend on
benchmark label quality. The corpus is controlled and cross-domain but not a
public temporal QA benchmark. Fusion-weight sensitivity and reranker isolation
were not run because no safe runtime switches exist. Generalization beyond
financial, regulatory, macroeconomic, market, and software-release evidence is
future work. ChronoRAG depends on temporal extraction quality.

## Related-Work Positioning

Temporal databases provide foundational valid-time / transaction-time
distinctions. ChronoRAG operationalizes this distinction for RAG evidence
selection over messy unstructured or semi-structured corpora. Temporal QA
datasets such as SituatedQA and TimeQA study temporally conditioned question
answering, but ChronoRAG focuses on retrieval-layer temporal role separation.
Temporal IR and temporal summarization work study time-sensitive retrieval and
summarization, but ChronoRAG focuses on multi-role temporal evidence selection
for downstream RAG.
