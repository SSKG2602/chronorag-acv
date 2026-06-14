# Layer 2 Cross-Domain Results

This directory contains final public Layer 2 cross-domain retrieval and answer
validation outputs, plus audit notes. Layer 2A artifacts score selected
evidence IDs under the v3 benchmark contracts. Layer 2B artifacts score
answer synthesis and answer validation over the 50 manual temporal QA cases.

## Final V3 Retrieval Comparison

Files:

- `layer2_retrieval_only_v3_200_eval.md`
- `layer2_retrieval_only_v3_200_eval.json`

Scope:

- dry-run retrieval-only evaluation
- 200 v3 aligned questions
- selected 5,000-row corpus
- top-k 5 evidence selection
- active methods and baselines: BM25, Dense-only, Date-filter RAG,
  Metadata Temporal RAG, and ChronoRAG Full
- no Vertex calls
- no LLM answer generation or answer-quality scoring

This is the final public Layer 2A comparison boundary. The paper-ready standard
comparison table adds BM25, Dense-only, Date-filter RAG, MRR@5, Wilson
confidence-interval variants, and sensitivity notes under
`docs/paper_assets/chrono_tables_index.md`.

Layer 2A retrieval-only standard comparison:

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 200 | 0.7750 | 0.9350 | 0.8467 | 0.7600 | 0.5750 |
| Dense-only | 200 | 0.3850 | 0.6100 | 0.4710 | 0.7950 | 0.3000 |
| Date-filter RAG | 200 | 0.7750 | 0.9350 | 0.8475 | 0.7650 | 0.6000 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | 0.7678 | 0.6950 | 0.4813 |
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | 0.8554 | 0.9950 | 0.9625 |

ChronoRAG does not maximize broad Hit@5. BM25 and Date-filter RAG have higher
Hit@5, but ChronoRAG Full has stronger Hit@1, MRR@5, Forbidden Absent@5, and
Category Primary Pass. The result supports temporal-validity retrieval, not
generic retrieval superiority.

Forbidden Absent@5 and Category Primary Pass are constraint-sensitive
diagnostics for temporal-validity retrieval. They are not intended to replace
standard IR metrics; they complement Hit@k and MRR@5 by measuring
temporal-invalidity exclusion and source/category correctness.

## Final Layer 2B Full-50 Answer Validation

Files:

- `layer2b_manual_50_qa_summary.md`
- `layer2b_chronorag_full_layer2b_full50_vertex_final_results.md`
- `layer2b_judge_layer2b_full50_judge_final_results.md`
- `layer2b_full50_manual_audit.md`

Scope:

- 50 manually designed temporal QA cases
- ChronoRAG answer synthesis with Vertex
- deterministic hard-contract validation
- LLM judge semantic validation
- human manual audit of validator-strictness cases
- answer synthesis and answer-validation scoring over the manual QA cases

Layer 2B final scores:

| Metric | Score |
|---|---:|
| Deterministic hard-contract pass | 38 / 50 = 76% |
| LLM judge overall pass | 38 / 50 = 76% |
| LLM judge semantic pass | 48 / 50 = 96% |
| Strict combined pass | 35 / 50 = 70% |
| Manually accepted validator-strictness cases | 3 |
| Manual-audited acceptable pass | 41 / 50 = 82% |

The strict combined score remains the conservative score. The manual-audited
score is a secondary interpretation after manual review and does not replace
the strict score.

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

### QA50 LLM Post-Filtering Baseline Comparison

| Method | Cases | Retrieval Hit@5 | Strict Combined Pass | Hit@5 + Pass | Hit@5 + Fail | No Hit@5 + Fail | No Hit@5 + Pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 + LLM | 50 | 32/50 = 0.6400 | 20/50 = 0.4000 | 20 | 12 | 18 | 0 |
| Dense-only + LLM | 50 | 26/50 = 0.5200 | 16/50 = 0.3200 | 16 | 10 | 24 | 0 |
| Date-filter RAG + LLM | 50 | 33/50 = 0.6600 | 20/50 = 0.4000 | 20 | 13 | 17 | 0 |

These baselines test whether standard retrieval followed by an LLM explicitly
prompted to distinguish valid time from transaction time can replace
retrieval-layer temporal grounding. The results show two failure modes. First,
valid evidence is often absent from the retrieved top-k set, so the LLM cannot
recover it. Second, even when valid evidence is present, the LLM still fails
strict temporal contract validation in 10–13 cases depending on the retriever.
This supports the claim that temporal grounding cannot be treated only as a
downstream prompting problem.

### QA50 ChronoRAG Answer-Level Extracted Values

| Metric | Value |
|---|---:|
| Strict combined pass | 0.7000, 35/50 |
| Deterministic hard-contract pass | 0.7600, 38/50 |
| Judge overall pass | 0.7600, 38/50 |
| Judge semantic pass | 0.9600, 48/50 |
| Expected evidence cited | 0.9800, 49/50 |
| Valid time correct | 0.8400, 42/50 |
| Pre-injection retrieval, any expected evidence | 0.7400, 37/50 |
| Pre-injection retrieval, all expected evidence | 0.6400, 32/50 |
| Post-injection evidence available | 1.0000, 50/50 |

Baseline methods are evaluated without evidence injection. ChronoRAG
pre-injection evidence availability is the fair retrieval-availability
comparison point. ChronoRAG post-injection answer-level results are reported
separately to show performance when expected evidence is available to the
generator. Layer 2A remains the primary retrieval-quality benchmark; Layer
2B/QA50 measures answer synthesis and temporal answer-contract behavior.

### QA50 Answer-Level Comparison

| Method | Evidence Available / Retrieval Hit@5 | Strict Combined Pass | Hard-Contract Pass | Judge Semantic Pass | Expected Evidence Cited | Valid Time Correct |
|---|---:|---:|---:|---:|---:|---:|
| BM25 + LLM | 0.6400 | 0.4000 | 0.4200 | 0.7800 | 0.5600 | 0.4600 |
| Dense-only + LLM | 0.5200 | 0.3200 | 0.3400 | 0.8200 | 0.4400 | 0.4400 |
| Date-filter RAG + LLM | 0.6600 | 0.4000 | 0.4400 | 0.9000 | 0.5800 | 0.4600 |
| ChronoRAG Full — pre-injection retrieval | 0.7400 any / 0.6400 all | n/a | n/a | n/a | n/a | n/a |
| ChronoRAG Full — post-injection answer setting | 1.0000 | 0.7000 | 0.7600 | 0.9600 | 0.9800 | 0.8400 |

The answer-level comparison shows that standard retrieval plus LLM temporal
post-filtering does not recover ChronoRAG-level strict temporal QA performance.
BM25 + LLM and Date-filter RAG + LLM reach 0.4000 strict combined pass,
Dense-only + LLM reaches 0.3200, while ChronoRAG Full reaches 0.7000 in the
prior post-injection answer setting. The pre-injection retrieval row is
reported separately to keep the retrieval-availability comparison fair.

## Final V3 Ablation

Files:

- `layer2_ablation_v3_ablation200.md`
- `layer2_ablation_v3_ablation200.json`

Scope:

- same 200 v3 questions
- same retrieval-only evaluator
- ChronoRAG component ablations plus the metadata-oriented baseline
- component behavior measured only in the tested setting

Retrieval Score Optimization Degrades Temporal Validity: The Score-only
ablation achieved the highest raw Hit@5 at 0.9850, but Forbidden Absent@5 fell
to 0.6500 and Category Primary Pass fell to 0.5625. ChronoRAG Full achieved
lower broad Hit@5 at 0.8950 but much stronger Forbidden Absent@5 at 0.9950 and
Category Primary Pass at 0.9625. This demonstrates that unconstrained retrieval
score optimization and temporal-validity retrieval are different objectives.

The current artifact records benchmark labels as fixed JSONL fields. The
labels are author-created and treated as fixed before method scoring.
Large-scale independent annotation is not included in this version and is
listed as a limitation.

## Archive

`archive/` contains intermediate and historical Layer 2 artifacts, including
older category-aware retrieval diagnostics, debug runs, Vertex smokes, and
answer-contract pilots. They are preserved for audit history but are not the
final public Layer 2A v3 retrieval-only result set or the final Layer 2B
full-50 answer-validation result set.

When citing Layer 2A, use the final v3 retrieval comparison and final v3
ablation files above. Treat archived Vertex or judge artifacts as superseded
intermediate work for this layer.

When citing Layer 2B, use the full-50 answer result, full-50 judge result, and
manual audit note above. Treat smoke and retry artifacts as intermediate run
history unless a separate audit explicitly says otherwise.
