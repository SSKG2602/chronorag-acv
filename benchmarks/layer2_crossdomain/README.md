# Layer 2A Cross-Domain Retrieval Benchmark

Layer 2A is ChronoRAG's controlled cross-domain retrieval-only benchmark. It
does not call Vertex, does not score generated answer wording, and does not
claim SOTA.

## Current v3 Scope

- 5,000 processed evidence rows.
- 200 v3 aligned temporal questions.
- 20 questions per active category.
- Domains: FRED macro, market index, SEC submissions, Federal Register, GitHub
  releases.
- Scoring input: each method's `selected_evidence_ids`.
- Active methods: `chronorag_full` and `metadata_temporal_rag`.

The v3 questions are generated so the target evidence is recoverable from the
question wording. Exact dates, source names, metric/form terms, versions, and
comparison slots are explicit. Hidden-target year-only questions are not part
of the public v3 retrieval check.

## Public Result Files

The public Layer 2A result directory should keep only:

- `results/README.md`
- `results/layer2_retrieval_only_v3_200_eval.md`
- `results/layer2_retrieval_only_v3_200_eval.json`
- `results/layer2_ablation_v3_ablation200.md`
- `results/layer2_ablation_v3_ablation200.json`
- `results/conflict_data_contract_blocked_v3.md`
- `results/conflict_data_contract_blocked_v3.json`
- `results/.gitkeep` if needed

Intermediate Vertex smokes, answer-contract pilots, and older category-aware
retrieval reports belong in `results/archive/`.

## Retrieval-Only Result

Stored report:

- [`results/layer2_retrieval_only_v3_200_eval.md`](results/layer2_retrieval_only_v3_200_eval.md)

Summary:

| Method | Benchmark cases | Result rows | Evaluated | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| `chronorag_full` | 200 | 200 | 200 | 0.82 | 0.90 | 0.99 | 0.96 |
| `metadata_temporal_rag` | 200 | 200 | 200 | 0.69 | 0.86 | 0.69 | 0.48 |

Category-primary pass is the headline Layer 2A diagnostic because some
categories require exact-time checks, source/metric constraints, forbidden
evidence avoidance, or multi-slot coverage rather than generic Hit@k alone.

## Ablation Result

Stored report:

- [`results/layer2_ablation_v3_ablation200.md`](results/layer2_ablation_v3_ablation200.md)

Ablations:

- `no_tcc`
- `no_temporal_precision`
- `no_transaction_role`
- `no_source_metric`
- `no_slot_assembler`
- `score_only`
- `metadata_temporal_rag`
- `chronorag_full`

Overall ablation summary:

| Variant | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass |
|---|---:|---:|---:|---:|---:|
| `metadata_temporal_rag` | 200 | 0.6900 | 0.8600 | 0.6950 | 0.4813 |
| `chronorag_score_only` | 200 | 0.8150 | 0.9850 | 0.6500 | 0.5625 |
| `chronorag_no_tcc` | 200 | 0.8350 | 0.8950 | 0.9950 | 0.9625 |
| `chronorag_no_temporal_precision` | 200 | 0.7500 | 0.8500 | 0.9450 | 0.7500 |
| `chronorag_no_transaction_role` | 200 | 0.8250 | 0.8950 | 0.9950 | 0.9625 |
| `chronorag_no_source_metric` | 200 | 0.8300 | 0.8900 | 1.0000 | 0.9688 |
| `chronorag_no_slot_assembler` | 200 | 0.8300 | 0.8900 | 0.8150 | 0.7750 |
| `chronorag_full` | 200 | 0.8250 | 0.8950 | 0.9950 | 0.9625 |

Interpretation should stay conservative. The v3 benchmark is controlled and
retrieval-only; it demonstrates component behavior on this corpus and question
set, not external generalization.

## Conflict Data Contract

`conflict_detection` is not a scored v3 retrieval category because the current
corpus contains no real two-sided conflict evidence pairs. The blocked status is
stored in:

- [`results/conflict_data_contract_blocked_v3.md`](results/conflict_data_contract_blocked_v3.md)
- [`results/conflict_data_contract_blocked_v3.json`](results/conflict_data_contract_blocked_v3.json)

Synthetic conflict IDs are not used in public v3 scoring.

## Reproduce

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

Do not run Vertex for Layer 2A retrieval-only reporting. Provider-backed
natural-language temporal QA belongs to future Layer 2B.
