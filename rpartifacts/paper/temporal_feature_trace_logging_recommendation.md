# Temporal Feature Trace Logging Recommendation

The current Figure 9 trace exporter records the score fields exposed by the
retrieval pipeline. Future retrieval-only runs should keep persisting a
per-query candidate trace with semantic score, temporal fit, valid-time fit,
transaction penalty, forbidden penalty, source/metric fit, slot assignment, and
final score.

Recommended future JSONL path:
`rpartifacts/data/candidate_trace_sample_schema.json`

This recommendation file is a schema guide. The actual Figure 9 trace data is
stored separately in `rpartifacts/data/temporal_feature_trace.jsonl` and
`rpartifacts/data/temporal_feature_trace.csv`.
