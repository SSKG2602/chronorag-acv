# One-Query Trace

This is a real Layer 2A retrieval-only benchmark case extracted from existing artifacts.

- Requested short ID in artifact prompt: `l2q:0000:exact_valid`
- Stored case ID used: `l2q:0000:exact_valid_time_retrieval`
- Category: `exact_valid_time_retrieval`
- Question: Retrieve Federal Funds Rate effective federal funds rate on 1954-10-01.
- Expected evidence: `l2:macro_fred:fedfunds:1954-10-01`
- Forbidden evidence: `l2:macro_fred:fedfunds:1956-02-01, l2:macro_fred:fedfunds:1957-06-01, l2:macro_fred:fedfunds:1958-10-01`
- BM25 selected examples: `l2:macro_fred:fedfunds:1958-10-01, l2:macro_fred:fedfunds:1962-10-01, l2:macro_fred:fedfunds:1973-07-01`
- ChronoRAG selected: `l2:macro_fred:fedfunds:1954-10-01`

## Source Artifacts Used

- `chronorag/stdcomp/results/stdcomp_layer2a_comparison.json`
- `chronorag/stdcomp/results/bm25_ranked_outputs.json`
- `benchmarks/layer2_crossdomain/data/layer2_questions.jsonl` for benchmark question provenance

## Trace Availability

- Case type: real artifact-extracted benchmark trace.
- Exact BM25 candidate scores: available in `bm25_ranked_outputs.json`.
- ChronoRAG selected evidence IDs and pass/fail behavior: available in `stdcomp_layer2a_comparison.json`.
- Candidate-level temporal feature scores for Figure 9: available in `rpartifacts/data/temporal_feature_trace.jsonl` and `.csv`.

This trace summarizes selected evidence IDs and pass/fail behavior from stored result artifacts. The separate Figure 9 trace export records the available retrieval-time numeric fields for representative cases.

Interpretation: the baseline retrieves expected evidence but also includes forbidden wrong-time evidence; ChronoRAG keeps the expected evidence while excluding the forbidden rows.
