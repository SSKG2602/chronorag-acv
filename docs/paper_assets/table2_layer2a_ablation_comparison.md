# Layer 2A ablation comparison

| Method | Cases | Hit@1 | Hit@5 | MRR@5 | Forbidden Absent@5 | Category Primary Pass |
|---|---|---|---|---|---|---|
| ChronoRAG Full | 200 | 0.8250 | 0.8950 | n/a | 0.9950 | 0.9625 |
| Metadata Temporal RAG | 200 | 0.6900 | 0.8600 | n/a | 0.6950 | 0.4813 |
| No Temporal Precision | 200 | 0.7500 | 0.8500 | n/a | 0.9450 | 0.7500 |
| No Slot Assembler | 200 | 0.8300 | 0.8900 | n/a | 0.8150 | 0.7750 |
| Score-only | 200 | 0.8150 | 0.9850 | n/a | 0.6500 | 0.5625 |
| No TCC | 200 | 0.8350 | 0.8950 | n/a | 0.9950 | 0.9625 |
| No Transaction Role | 200 | 0.8250 | 0.8950 | n/a | 0.9950 | 0.9625 |
| No Source/Metric Adjustment | 200 | 0.8300 | 0.8900 | n/a | 1.0000 | 0.9688 |

Notes:
- Extracted from existing Layer 2A ablation artifact; no retrieval, model, validator, or judge rerun.
- MRR@5 is n/a because this ablation artifact does not contain MRR values.
- Rows include the requested ablations plus other clearly named variants present in the artifact.
- The Score-only ablation achieved the highest raw Hit@5 at 0.9850, but Forbidden Absent@5 fell to 0.6500 and Category Primary Pass fell to 0.5625.
- ChronoRAG Full achieved lower broad Hit@5 at 0.8950 but much stronger Forbidden Absent@5 at 0.9950 and Category Primary Pass at 0.9625.
