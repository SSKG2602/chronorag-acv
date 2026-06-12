# Paper Figure Index

## Figure 1: ChronoRAG Framework

Path: `docs/paper_assets/chronorag_framework.svg`

Caption: Overall ChronoRAG framework showing temporal contextual chunking,
valid-time and transaction-time separation, temporal precision scoring, temporal
fusion, forbidden-time handling, evidence finalization, ChronoSanity,
attribution cards, and answer-contract validation.

## Figure 2: Cross-Domain Retrieval Benchmark Results

Path: `docs/paper_assets/layer2a_retrieval_comparison.png`

Caption: Cross-domain retrieval results comparing the proposed ChronoRAG method
against the temporal metadata baseline across Generic Hit@1, Generic Hit@5,
Forbidden Absent@5, and Category Primary Pass.

## Figure 3: Ablation Study

Path: `docs/paper_assets/layer2a_ablation_study.png`

Caption: Ablation results showing the effect of temporal precision, slot-aware
assembly, and scoring-only evidence selection on final temporal retrieval
quality.

## Figure 4: Natural-Language Temporal QA Validation

Path: `docs/paper_assets/layer2b_answer_validation.png`

Caption: Natural-language temporal QA validation results under deterministic
hard-contract, LLM judge semantic, strict combined, and manual-audited
acceptable criteria.

## Figure 5: Evidence Finalization Schematic

Path: `docs/paper_assets/evidence_finalization_schematic.svg`

Caption: Schematic view of how temporal-role constraints, forbidden-time
handling, source and metric anchors, and slot-aware assembly refine a generic
candidate evidence list into a temporally valid final evidence set.

## Figure 6: Temporal Scoring Heatmap

Path: `docs/paper_assets/temporal_scoring_heatmap.png`

Caption: Illustrative temporal scoring heatmap showing how semantic relevance
and temporal fit jointly affect candidate evidence ranking. This figure is a
schematic visualization of the scoring concept, not a new experimental result.
