# Table 2. Layer 2A Full Ablation Comparison

Source artifacts:

- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md`
- `benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json`
- `docs/paper_assets/table2_layer2a_ablation_comparison.csv`

| Method / Variant | Hit@1 | Hit@5 | Forbidden Absent@5 | Category Primary Pass | Interpretation / Mechanism Removed |
|---|---:|---:|---:|---:|---|
| ChronoRAG Full | 0.825 | 0.895 | 0.995 | 0.963 | Complete temporal-validity selection path. |
| No Temporal Precision | 0.750 | 0.850 | 0.945 | 0.750 | Removes temporal precision scoring. |
| No Slot Assembler | 0.830 | 0.890 | 0.815 | 0.775 | Removes required evidence slot finalization. |
| Score-only | 0.815 | **0.985** | 0.650 | 0.563 | Ranks by broad retrieval score without temporal-validity safeguards. |
| No TCC | **0.835** | 0.895 | 0.995 | 0.963 | Removes Temporal Contextual Chunking features. |
| No Source/Metric Adjustment | 0.830 | 0.890 | **1.000** | **0.969** | Removes source and metric constraint adjustment. |
| No Transaction Role | 0.825 | 0.895 | 0.995 | 0.963 | Removes transaction-role cleanup. |
| Metadata Temporal RAG | 0.690 | 0.860 | 0.695 | 0.481 | Metadata-oriented temporal retrieval baseline from the stored ablation report. |

MRR@5 was not stored for this ablation artifact.

Layer 2A ablations use the same 200-question v3 retrieval benchmark, 5,000-row
controlled corpus, top-k=5, and retrieval-only evaluation protocol. These are
existing stored artifacts; no new experiment is run for this table.
