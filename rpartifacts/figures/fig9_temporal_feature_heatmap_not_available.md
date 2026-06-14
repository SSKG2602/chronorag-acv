# Figure 9 Temporal Feature Heatmap Not Available

Candidate-level temporal feature traces are not stored in the existing result
artifacts. The current artifacts contain selected evidence IDs, aggregate
metrics, and case-level pass/fail diagnostics, but they do not persist
per-candidate semantic score, temporal fit, valid-time fit, transaction
penalty, forbidden penalty, source/metric fit, slot assignment, and final score
columns.

Future retrieval-only runs should persist per-candidate scoring traces if the
paper needs a true temporal feature heatmap. No synthetic numeric heatmap was
generated.
