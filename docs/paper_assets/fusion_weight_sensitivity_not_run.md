# Fusion-Weight Sensitivity Not Run

Status: `not_run`

Reason: No safe existing CLI/config switch exposes semantic/temporal fusion weights.

Evidence:
- benchmarks/layer2_crossdomain/methods/chronorag_full/adapter.py calls monotone_temporal_fusion with hardcoded weights.
- Changing those weights would require code surgery in core retrieval-path code, which is outside this validation scope.

Future work: Expose fusion weights through a documented retrieval-only experiment flag.
