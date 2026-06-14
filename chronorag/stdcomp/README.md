# ChronoRAG Standard Comparison Baselines

This package runs standard retrieval baselines for the Layer 2A 200-case
retrieval benchmark.

Required data:

- `benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl`
- `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl`
- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`

The tracked sample corpus is invalid for this comparison. The 200 Layer 2A
queries were generated against the full 5,000-row corpus, so BM25, Dense-only,
Date-filter RAG, Metadata Temporal RAG, and ChronoRAG Full must use the same
candidate universe.

## Baselines

`BM25` ranks the raw evidence-row text using BM25 only.

`Dense-only` ranks the same raw evidence-row text using normalized embeddings
from `BAAI/bge-small-en-v1.5` by default. Document embeddings are cached under
`chronorag/stdcomp/results/cache/`.

`Date-filter RAG` extracts simple date strings from the question, filters
candidate raw/source text by naive string containment, and ranks the filtered
candidates with BM25. If no candidate matches the naive date filter, it falls
back to BM25 over all candidates and records that fallback in the raw output.

These baselines deliberately do not use:

- Temporal Contextual Chunking
- valid-time / transaction-time role separation
- temporal metadata scoring
- temporal fusion
- forbidden-time suppression
- ChronoRAG finalization logic

## Run

From the repository root:

Layer 2A 200-case retrieval:

```bash
python -m chronorag.stdcomp.evaluate_stdcomp \
  --corpus benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl \
  --queries benchmarks/layer2_crossdomain/data/layer2_questions.jsonl \
  --existing-results benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json \
  --top-k 5 \
  --out-dir chronorag/stdcomp/results
```

The default command is equivalent:

```bash
python -m chronorag.stdcomp.evaluate_stdcomp --top-k 5
```

The dense baseline requires `sentence-transformers`. If the embedding model is
not already cached, loading `BAAI/bge-small-en-v1.5` may download model files.

## Outputs

The evaluator writes:

- `bm25_ranked_outputs.json`
- `bm25_metrics.json`
- `dense_only_ranked_outputs.json`
- `dense_only_metrics.json`
- `date_filter_rag_ranked_outputs.json`
- `date_filter_rag_metrics.json`
- `stdcomp_layer2a_comparison.json`
- `stdcomp_layer2a_comparison.csv`
- `stdcomp_layer2a_summary.md`

If `docs/paper_assets/` exists, it also writes:

- `docs/paper_assets/stdcomp_layer2a_summary.md`
- `docs/paper_assets/stdcomp_layer2a_summary.csv`

## Paper Tables And Reviewer-Defense Outputs

The paper-ready output index is:

- `docs/paper_assets/chrono_tables_index.md`

Main tables:

- `docs/paper_assets/table1_layer2a_retrieval_standard_comparison.md`
- `docs/paper_assets/table2_layer2a_ablation_comparison.md`
- `docs/paper_assets/table3_qa50_llm_post_filter_baselines.md`
- `docs/paper_assets/table4_qa50_answer_level_comparison.md`

Reviewer-defense supporting outputs:

- `docs/paper_assets/table1_layer2a_retrieval_standard_comparison_with_ci.md`
- `docs/paper_assets/table3_qa50_llm_post_filter_baselines_with_ci.md`
- `docs/paper_assets/table4_qa50_answer_level_comparison_with_ci.md`
- `docs/paper_assets/chronorag_qa50_extracted_values.md`
- `docs/paper_assets/topk_sensitivity.md`
- `docs/paper_assets/fusion_weight_sensitivity_not_run.md`
- `docs/paper_assets/reranker_ablation_not_run.md`

Layer 2A standard comparison at top-k=5:

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
retrieval superiority.

Forbidden Absent@5 and Category Primary Pass are constraint-sensitive
diagnostics for temporal-validity retrieval. They are not intended to replace
standard IR metrics; they complement Hit@k and MRR@5 by measuring
temporal-invalidity exclusion and source/category correctness.

## QA50 LLM Post-Filtering Baselines

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
post-injection evidence available is 1.0000 (50/50). Gold expected evidence
IDs were not included in the LLM baseline prompts.

## Sensitivity Notes

Top-k retrieval-only sensitivity ran for k=1, 3, 5, and 10 on Layer 2A. At
k=5, ChronoRAG Full has Hit@5 0.8950, MRR@5 0.8554, Forbidden Absent@5
0.9950, and Category Primary Pass 0.9625.

Fusion-weight sensitivity was not run because no safe CLI/config switch exists
and weights are hardcoded. Reranker ablation was not run because no safe
existing disable flag exists. Both are future work rather than hidden results.
