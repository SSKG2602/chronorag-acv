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
- active methods: `chronorag_full` and `metadata_temporal_rag`
- no Vertex calls
- no LLM answer generation or answer-quality scoring

This is the final public Layer 2A comparison artifact.

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
- expected evidence available where needed, so this is not a retrieval-quality
  result

Layer 2B final scores:

| Metric | Score |
|---|---:|
| Deterministic hard-contract pass | 38 / 50 = 76% |
| LLM judge semantic pass | 38 / 50 = 76% |
| Strict combined pass | 35 / 50 = 70% |
| Manually accepted validator-strictness cases | 3 |
| Manual-audited acceptable pass | 41 / 50 = 82% |

The strict combined score remains the conservative score. The manual-audited
score is a secondary interpretation after manual review and does not replace
the strict score.

## Final V3 Ablation

Files:

- `layer2_ablation_v3_ablation200.md`
- `layer2_ablation_v3_ablation200.json`

Scope:

- same 200 v3 questions
- same retrieval-only evaluator
- ChronoRAG component ablations plus the metadata-oriented baseline
- component behavior measured only in the tested setting

## Blocked Conflict Data Contract

Files:

- `conflict_data_contract_blocked_v3.md`
- `conflict_data_contract_blocked_v3.json`

Layer 2A v3 does not score `conflict_detection` because real two-sided
conflict evidence pairs are absent from the current corpus. The blocked note is
part of the public result boundary, not an omitted score.

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
