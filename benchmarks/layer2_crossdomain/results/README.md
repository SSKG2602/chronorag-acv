# Layer 2A Cross-Domain Results

This directory contains the final public Layer 2A controlled retrieval-only
benchmark outputs and audit notes. These artifacts score selected evidence IDs
under the v3 benchmark contracts; they do not score generated natural-language
answers.

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
final public Layer 2A v3 retrieval-only result set.

When citing Layer 2A, use the final v3 retrieval comparison and final v3
ablation files above. Treat archived Vertex or judge artifacts as superseded
intermediate work for this layer.
