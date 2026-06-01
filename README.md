# ChronoRAG

ChronoRAG is a temporal retrieval and grounded answer-validation RAG framework. Current results are controlled benchmark results, not SOTA claims.

ChronoRAG is built for questions where **when** evidence was valid matters as much as what the evidence says. It treats time as a retrieval constraint, separates claim-valid time from publication or ingestion time, and validates grounded answers against cited evidence.

## Problem

Standard RAG often ranks passages by lexical or semantic relevance. That is not enough for temporal questions:

- A row can mention the right entity but the wrong date.
- A filing or publication date can be mistaken for the valid date of the claim.
- A broad historical range can outrank exact dated evidence.
- A query can explicitly exclude a nearby date.
- A comparison question can need evidence from multiple time slots.
- A generated answer can cite correct-looking evidence but misuse its temporal role.

ChronoRAG makes these cases explicit in retrieval, final evidence selection, and answer validation.

## Architecture

The current core path has six main pieces:

| Component | Role |
|---|---|
| Temporal Contextual Chunking | Keeps raw evidence unchanged for grounding while adding structured retrieval text with temporal, entity, unit, and source context. |
| `valid_time` vs `transaction_time` separation | Stores when a claim is true separately from when the system observed, filed, published, or released it. |
| Temporal precision scoring | Scores year, month, day, timestamp, range, fuzzy range, quarter, and daypart matches before answer synthesis. |
| Polarity and negative constraint handling | Treats targets such as `1990-04-20` differently from excluded dates such as `not 1990-03-28`. |
| Slot-aware evidence finalization | Assembles evidence for comparison and multi-slot temporal questions so one side does not dominate top-k. |
| Grounded answer validation | Checks cited evidence, valid-time use, transaction-time misuse, partial/refusal behavior, and provider-output contracts. |

Provider-backed generation is optional. Retrieval and validation can be run deterministically without Vertex.

## Benchmarks

ChronoRAG currently has three controlled benchmark layers.

### Layer 1A: Temporal Eval v2

Layer 1A is a retrieval benchmark for temporal evidence selection. It checks exact valid-time retrieval, wrong-year traps, broad-window distractors, transaction-time vs valid-time traps, conflict/proxy behavior, and partial/refusal proxy behavior.

Files:

- `benchmarks/run_temporal_eval_v2.py`
- `benchmarks/temporal_eval_v2_15.jsonl`
- `data/sample/temporal_eval_v2/`
- `benchmarks/results/temporal_eval_v2_results.md`
- `benchmarks/results/temporal_eval_v2_results.json`

Current stored light-mode result: hybrid retrieval plus temporal fusion plus rerank reaches `0.80` Hit@5 evidence and `0.93` Hit@5 window on the 15-case controlled set. This is a controlled retrieval result, not an external benchmark claim.

### Layer 1B: Temporal Answer Validation

Layer 1B evaluates grounded answer behavior over retrieved temporal evidence. It has dry-run, light, and Vertex paths:

- Dry-run prompts: prompt generation only, no provider call.
- Light mode: deterministic CI-safe answer harness.
- Vertex mode: provider-backed answer synthesis plus strict schema, grounding, and temporal-rule validation.

Files:

- `benchmarks/run_temporal_answer_validation_v2.py`
- `benchmarks/temporal_answer_validation_v2_15.jsonl`
- `benchmarks/results/temporal_answer_validation_v2_*.md`
- `benchmarks/results/temporal_answer_validation_v2_*.json`

The primary stored Vertex top-k 5 result is `benchmarks/results/temporal_answer_validation_v2_vertex_topk5_results.md`. It reports `0.80` answer overall pass, `1.00` expected evidence citation, `1.00` valid-time correctness, `1.00` transaction-time trap avoidance, and `1.00` grounding validation pass. Non-passing cases remain documented as answer-behavior limitations.

### Layer 2A: Cross-Domain Retrieval-Only

Layer 2A is a cross-domain retrieval-only benchmark:

- 5,000 processed corpus rows.
- 200 v3 aligned temporal questions.
- Domains: FRED macro, market index, SEC submissions, Federal Register, GitHub releases.
- Methods: `chronorag_full` and `metadata_temporal_rag`.
- No Vertex and no generated answer scoring.

Final public results:

- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.md`
- `benchmarks/layer2_crossdomain/results/layer2_retrieval_only_v3_200_eval.json`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json`

Current Layer 2A v3 retrieval-only summary:

| Method | Cases | Generic Hit@1 | Generic Hit@5 | Forbidden absent@5 | Category primary pass |
|---|---:|---:|---:|---:|---:|
| `chronorag_full` | 200 | 0.82 | 0.90 | 0.99 | 0.96 |
| `metadata_temporal_rag` | 200 | 0.69 | 0.86 | 0.69 | 0.48 |

These are selected-evidence metrics only. They do not evaluate natural-language answer quality.

## Layer 2A Ablations

The Layer 2A v3 ablation file compares ChronoRAG components on the same 200 questions:

- `no_tcc`
- `no_temporal_precision`
- `no_transaction_role`
- `no_source_metric`
- `no_slot_assembler`
- `score_only`
- `metadata_temporal_rag`
- `chronorag_full`

Stored result:

- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`

Key interpretation from the stored report:

- Temporal precision drives wrong-time trap handling.
- Slot assembly drives multi-slot and cross-domain coverage.
- Retrieval finalization contributes beyond score-only ranking.
- Some ablations do not drop on some categories because the v3 questions expose explicit anchors; those cases should be interpreted conservatively.

## Reproduce

Set light mode for local deterministic runs:

```bash
export CHRONORAG_LIGHT=1
```

Layer 1A retrieval benchmark:

```bash
python3 benchmarks/build_temporal_eval_v2.py
python3 benchmarks/run_temporal_eval_v2.py --light
```

Layer 1B dry-run prompts:

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

Do not run Vertex for Layer 2A unless you are explicitly evaluating a future answer-quality layer.

## Repository Map

```text
app/                         FastAPI app, routes, schemas, services
core/                        temporal retrieval, chunking, routing, generation
storage/                     local PVDB/cache persistence abstractions
benchmarks/                  Layer 1A and Layer 1B benchmark harnesses
benchmarks/layer2_crossdomain Layer 2A corpus, questions, methods, reports
docs/                        technical reports and design notes
tests/                       unit and benchmark contract tests
```

## Limitations

- No SOTA claim.
- Layer 2A is retrieval-only.
- LLM natural-language temporal QA is future Layer 2B.
- Conflict detection is currently data-contract blocked in Layer 2A because real conflict-pair rows are absent from the current corpus.
- Vertex-backed Layer 1B results are controlled benchmark results, not production reliability proof.
- ChronoRAG is not a deployed production service.
- Storage, auth, observability, and multi-tenant deployment paths are not production-hardened.

## Roadmap

Layer 2B is planned as a 50-question manually designed natural-language temporal QA benchmark using ChronoRAG + Vertex + dynamic top-k. It is intended to evaluate generated answer quality after retrieval, not just selected evidence IDs.

No metadata+LLM comparison is planned for Layer 2B. The planned focus is ChronoRAG's grounded temporal answer path.

## License

Apache-2.0.
