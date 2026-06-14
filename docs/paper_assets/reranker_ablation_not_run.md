# Reranker Ablation Not Run

Status: `not_run`

Reason: No safe existing flag was found to disable a reranker/cross-encoder in the Layer 2A ChronoRAG retrieval path.

Evidence:
- The Layer 2A adapter uses BM25, monotone temporal fusion, and finalization/slot assembly.
- Existing safe ablation flags cover score-only, TCC, temporal precision, transaction role, source/metric adjustment, and slot assembler, but not a reranker toggle.

Future work: Add an explicit reranker/cross-encoder toggle if a reranker is introduced into this path.
