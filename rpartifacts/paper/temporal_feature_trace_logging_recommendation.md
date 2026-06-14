# Temporal Feature Trace Logging Recommendation

Candidate-level temporal feature traces are not stored in the existing
artifacts. The current benchmark artifacts store selected evidence and
aggregate metrics, but not per-candidate scoring components. Future
retrieval-only runs should persist a per-query candidate trace with semantic
score, temporal fit, valid-time fit, transaction penalty, forbidden penalty,
source/metric fit, slot assignment, and final score.

Recommended future JSONL path:
`rpartifacts/data/candidate_trace_sample_schema.json`

This is a schema recommendation only. It is not benchmark data and contains no
synthetic candidate scores.
