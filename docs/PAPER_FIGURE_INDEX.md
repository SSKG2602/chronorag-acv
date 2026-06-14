# Paper Figure Index

## Figure 1: ChronoRAG Framework

Path: `docs/paper_assets/chronorag_framework.svg`

Caption: Overall ChronoRAG framework showing temporal contextual chunking,
valid-time and transaction-time separation, temporal precision scoring, temporal
fusion, forbidden-time handling, evidence finalization, ChronoSanity,
attribution cards, and answer-contract validation.

## Figure 2: Cross-Domain Retrieval Benchmark Results

Path: `docs/paper_assets/layer2a_retrieval_comparison.png`

Caption: Cross-domain retrieval results comparing ChronoRAG against BM25,
Dense-only, Date-filter RAG, and Metadata Temporal RAG baselines. BM25 and
Date-filter RAG have higher broad Hit@5, while ChronoRAG Full has stronger
Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass, supporting
temporal-validity retrieval rather than generic retrieval superiority.

## Figure 3: Ablation Study

Path: `docs/paper_assets/layer2a_ablation_study.png`

Caption: Ablation results showing the effect of temporal precision, slot-aware
assembly, and scoring-only evidence selection on final temporal retrieval
quality.

## Figure 4: Natural-Language Temporal QA Validation

Path: `docs/paper_assets/layer2b_answer_validation.png`

Caption: Natural-language temporal QA validation results under deterministic
hard-contract, LLM judge overall, LLM judge semantic, strict combined, and
manual-audited acceptable criteria. Answer-level ChronoRAG results should be
read separately from pre-injection retrieval availability and standard
retrieval + LLM post-filtering baselines.

## Figure 5: Evidence Finalization Schematic

Path: `docs/paper_assets/evidence_finalization_schematic.svg`

Caption: Schematic view of how temporal-role constraints, forbidden-time
handling, source and metric anchors, and slot-aware assembly refine a generic
candidate evidence list into a temporally valid final evidence set.

## Figure 6: Temporal Feature Heatmap

Path: `rpartifacts/figures/fig9_temporal_feature_heatmap.png`

Caption: Retrieval-only candidate trace heatmap showing available scoring
signals for representative Layer 2A cases. Raw values are stored in
`rpartifacts/data/temporal_feature_trace.jsonl` and `.csv`; heatmap colors are
per-column min-max normalized. This is a mechanism visualization, not a
standalone performance metric.
