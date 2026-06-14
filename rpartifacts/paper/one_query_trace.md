# One-Query Trace

This is a real Layer 2A retrieval-only benchmark case extracted from existing artifacts.

- Case ID: `l2q:0000:exact_valid_time_retrieval`
- Category: `exact_valid_time_retrieval`
- Question: Retrieve Federal Funds Rate effective federal funds rate on 1954-10-01.
- Expected evidence: `l2:macro_fred:fedfunds:1954-10-01`
- Forbidden evidence: `l2:macro_fred:fedfunds:1956-02-01, l2:macro_fred:fedfunds:1957-06-01, l2:macro_fred:fedfunds:1958-10-01`

| Method | Retrieval pass | Reason | Selected evidence | Forbidden overlap |
|---|---:|---|---|---|
| BM25 | False | fail: forbidden_absent_at_k | `l2:macro_fred:fedfunds:1954-10-01`<br>`l2:macro_fred:fedfunds:1958-10-01`<br>`l2:macro_fred:fedfunds:1962-10-01`<br>`l2:macro_fred:fedfunds:1973-07-01`<br>`l2:macro_fred:fedfunds:2022-12-01` | `l2:macro_fred:fedfunds:1958-10-01` |
| ChronoRAG Full | True | pass: selected evidence satisfies category retrieval checks | `l2:macro_fred:fedfunds:1954-10-01` | none |

Interpretation: the baseline retrieves expected evidence but also includes forbidden wrong-time evidence; ChronoRAG keeps the expected evidence while excluding the forbidden rows.
