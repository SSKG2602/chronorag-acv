# ChronoRAG Reproducibility Notes

This document records the public benchmark boundary for the repository. It is a
guide to existing data, scripts, and stored artifacts; it does not introduce new
metrics or paper claims.

## Benchmark Boundaries

Layer 2A is the retrieval-only benchmark. It uses the fixed selected corpus and
the 200 aligned questions:

- Corpus: `benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl`
- Corpus size: 5,000 rows
- Corpus SHA256, from stored table/runtime artifacts:
  `fe0782eea177ccd1ac90ce21c730c8c69f65c8be388534bc141d3a01a6269287`
- Raw pool manifest: `benchmarks/layer2_crossdomain/data/raw_pool_manifest.json`
- Raw pool size recorded in the manifest: approximately 46,503 rows/items
- Questions: `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl`
- Questions: 200
- Questions SHA256, from stored table/runtime artifacts:
  `d8dcaf4e306fa7f3c8d3ccd02aeee7af5c03ce23250d2a47d470c2c7e5c98b7a`
- Retrieval cutoff: top-k=5

Layer 2B is the manual temporal QA benchmark:

- QA cases: `benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl`
- QA cases: 50
- QA SHA256, from stored QA50 table artifacts:
  `6e41ad8f6bd075060d15a14d175019316417656d8eaacd8f841999a2f9668727`
- Standard QA50 baseline artifact boundary:
  `chronorag/stdcomp/results/qa50_llm_baselines/`
- ChronoRAG answer-level artifact boundary:
  `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.jsonl`
  and
  `benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.jsonl`

## Methods

The Layer 2A retrieval comparison uses five methods:

- BM25
- Dense-only, using `BAAI/bge-small-en-v1.5`
- Date-filter RAG
- Metadata Temporal RAG
- ChronoRAG Full

The standard comparison baselines intentionally avoid ChronoRAG temporal
features. They do not use Temporal Contextual Chunking, valid-time /
transaction-time role separation, temporal fusion, forbidden-time suppression,
or ChronoRAG final evidence assembly.

## Metrics

Layer 2A reports retrieval-only metrics over selected evidence IDs:

- Hit@1
- Hit@5
- MRR@5
- Forbidden Absent@5
- Category Primary Pass

QA50 reports answer-level and retrieval-availability metrics where available:

- Retrieval Hit@5 or expected evidence availability
- Strict Combined Pass
- Deterministic Hard-Contract Pass
- LLM Judge Overall Pass
- LLM Judge Semantic Pass
- Expected Evidence Cited
- Valid Time Used Correct

ChronoRAG post-injection QA50 answer-level values are not a standard retrieval
availability claim. They show answer behavior when expected evidence is
available to the generator. Pre-injection evidence availability is the fair
retrieval-availability comparison point.

## Stored Result Boundary

Use these stored artifacts as the public result boundary:

- Layer 2A retrieval-only comparison:
  `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`
  and
  `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md`
- Layer 2A standard comparison:
  `chronorag/stdcomp/results/stdcomp_layer2a_comparison.json`
  and
  `docs/paper_assets/table1_layer2a_retrieval_standard_comparison.md`
- Layer 2A ablation:
  `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json`
  and
  `docs/paper_assets/table2_layer2a_full_ablation_comparison.md`
- Layer 2A runtime:
  `chronorag/stdcomp/results/layer2a_runtime_retrieval_200.json`
  and
  `docs/paper_assets/table_runtime_layer2a_retrieval.md`
- QA50 standard retrieval + LLM baselines:
  `chronorag/stdcomp/results/qa50_llm_baselines/`
  and
  `docs/paper_assets/table3_qa50_llm_post_filter_baselines.md`
- QA50 answer-level comparison:
  `docs/paper_assets/table4_qa50_answer_level_comparison.md`

Paper-facing table and figure indexes:

- `docs/paper_assets/chrono_tables_index.md`
- `docs/BENCHMARK_ARTIFACTS_INDEX.md`
- `rpartifacts/README.md`
- `rpartifacts/tables/table7_artifact_manifest.md`

## Runtime Environment

The stored Layer 2A runtime artifact records the local timing environment:

- OS: macOS 26.3.1 arm64
- CPU: Apple M2
- RAM: 8 GB
- Python: 3.11.1
- Dense device: `mps:0`
- GPU used for dense model: yes, via MPS
- Timing policy: wall-clock `time.perf_counter()`
- Reported runtime: warm retrieval time after setup and one warmup query
- Excluded calls: no LLM, judge, Vertex, Gemini, or answer generation

Stored warm retrieval times over the full 200-question Layer 2A benchmark:

| Method | Warm retrieval seconds |
|---|---:|
| BM25 | 1.520 |
| Dense-only | 12.884 |
| Date-filter RAG | 3.103 |
| Metadata Temporal RAG | 17.725 |
| ChronoRAG Full | 284.030 |

## Safe Local Validation

These commands are retrieval-only or local validation commands. They do not
call Vertex, Gemini, OpenAI, or any judge:

```bash
python3 benchmarks/layer2_crossdomain/validate_layer2_dataset.py
python3 -m chronorag.stdcomp.evaluate_stdcomp --help
python3 -m chronorag.stdcomp.evaluate_stdcomp --top-k 5
python3 -m py_compile chronorag/stdcomp/evaluate_stdcomp.py
```

Provider-backed QA50 answer generation and judge runs should not be rerun for
routine repository cleanup. Use the stored QA50 artifacts unless a new
experiment is explicitly planned and documented.

## Claim Boundary

The stored results support a bounded claim: temporal-validity evidence
selection and answer-contract validation reduce temporal misgrounding under the
documented benchmark settings. The repository does not claim generic
open-domain RAG superiority, SOTA performance, or that hallucination is solved.
