# Future Research Direction

## Technical Limitations

### Temporal Expression Parsing

ChronoRAG currently relies on explicit or reliably extractable temporal
expressions. More robust handling of relative, implicit, underspecified, and
fuzzy temporal references remains an important technical extension.

### Rule-Weighted Temporal Fusion

The current temporal fusion layer uses explicitly designed scoring signals. A
learned temporal reranker could adapt the relative importance of semantic
relevance, valid-time fit, transaction-time role, interval overlap, and
forbidden-time penalties across different domains.

### Multi-Hop Temporal Reasoning

ChronoRAG focuses on temporally valid evidence selection and slot-aware
assembly. Extending the framework to multi-hop temporal reasoning, where
answers require ordered chains of evidence across multiple events or intervals,
remains future work.

### Temporal Contradiction Modeling

ChronoSanity detects temporally inconsistent or role-conflicting evidence in
retrieved candidates. Future work should extend this into explicit temporal
contradiction modeling, including contradiction type classification and
contradiction severity scoring.

### Temporal Confidence Calibration

The current framework exposes confidence and attribution metadata, but
calibrated uncertainty estimation for temporal fit, conflict likelihood, and
answer validity remains an open extension.

### Joint Optimization of Evidence Finalization

Source-aware, metric-aware, and slot-aware finalization are implemented as
modular retrieval-time controls. A future version can investigate whether these
controls can be jointly optimized through learning-based evidence selection.

### Interpretability Visualization

The current repository reports numerical retrieval and ablation results.
Additional visual analysis, such as score heatmaps, temporal-ranking traces,
and before/after evidence finalization diagrams, would improve interpretability
of the temporal retrieval process.

## Future Work

Future work will focus on strengthening the temporal modeling layer rather than
changing the core motivation of the framework.

1. Robust temporal expression normalization for relative, fuzzy, implicit, and
   underspecified dates.
2. Learned temporal reranking over semantic relevance, valid-time fit,
   transaction-time role, interval overlap, and forbidden-time penalties.
3. Multi-hop temporal reasoning over ordered evidence chains.
4. Explicit temporal contradiction modeling with contradiction type and
   severity classification.
5. Calibrated temporal confidence estimation for evidence fit, conflict
   likelihood, and answer validity.
6. Joint optimization of temporal fusion and source-aware, metric-aware, and
   slot-aware evidence finalization.
7. Interpretability tools such as temporal score heatmaps, evidence-ranking
   traces, attribution-flow graphs, and before/after finalization
   visualizations.
8. Advanced slot-aware evidence planning for comparison, aggregation, and
   multi-entity temporal queries.
9. Automatic extraction of valid-time and transaction-time roles from raw
   documents.
10. Harder temporal benchmark cases focused on reasoning patterns,
    contradiction, temporal ordering, and interval logic.
