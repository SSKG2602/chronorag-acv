# Layer 2A Cross-Domain Results

These artifacts are controlled retrieval-only benchmark outputs.

They do not claim SOTA, production readiness, or answer-generation quality.

## Final Layer 2A v3 Retrieval Comparison

- `layer2_retrieval_only_v3_200_eval.md`
- `layer2_retrieval_only_v3_200_eval.json`

Compares:
- `chronorag_full`
- `metadata_temporal_rag`

Mode:
- dry_run
- 200 questions
- 5,000 corpus rows
- top-k 5
- no Vertex
- no LLM answer generation

## Final Layer 2A v3 Ablation

- `layer2_ablation_v3_ablation200.md`
- `layer2_ablation_v3_ablation200.json`

Evaluates ChronoRAG component ablations on the same Layer 2A v3 questions.

## Notes

Diagnostic categories such as partial/insufficient and ambiguous-time cases are not scored as category-primary retrieval cases.

Conflict detection is documented as data-contract blocked because real conflict-pair evidence rows are not present in the current corpus.
