# Comparison Metrics

Layer 2A reports retrieval-only metrics separately from answer/judge metrics.
Retrieval-only evaluation does not call Vertex and should be run before any
provider-backed answer synthesis.

Retrieval-only metrics:

| Metric | Meaning |
|---|---|
| Hit@1 | First selected evidence is expected or acceptable. |
| Hit@5 | Any top-5 selected evidence is expected or acceptable. |
| forbidden_evidence_absent@5 | No forbidden evidence appears in top 5. |
| category breakdown | The same metrics grouped by temporal query category. |

Answer/judge metrics remain separate: overall pass, evidence correctness,
valid-time correctness, transaction-time trap avoidance, conflict warning
correctness, partial/refusal correctness, clarification correctness, provider
output-contract failures, and judge infrastructure status.

Minimum retrieval target before a full Vertex rerun:

| Metric | Target |
|---|---:|
| `chronorag_gsm` overall Hit@5 | > 0.70 |
| `chronorag_gsm` forbidden_absent@5 | > 0.90 |
| transaction_time_vs_valid_time forbidden_absent@5 | > 0.80 |
| same_entity_wrong_year_trap forbidden_absent@5 | > 0.80 |
| exact_valid_time_retrieval Hit@5 | 1.00 |

Strong retrieval target:

| Metric | Target |
|---|---:|
| overall Hit@5 | >= 0.80 |
| forbidden_absent@5 | >= 0.95 |

Recommended embedding metadata to report with every result:

| Mode | Model | Dim |
|---|---|---:|
| low-memory | `BAAI/bge-small-en-v1.5` | 384 |
| recommended Layer 2A cloud retrieval | `BAAI/bge-base-en-v1.5` | 768 |

No SOTA or public benchmark proof should be claimed from these internal
retrieval or answer-judge results.
