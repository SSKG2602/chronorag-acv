# Layer 2 Fixture Data

This folder contains tiny fixture files for plumbing tests only. The raw Layer
2 pool lives under `data/raw/layer2_crossdomain/` and may be gitignored or
managed outside the benchmark package. The real processed Layer 2 corpus should
be built later at roughly 5,000 evidence rows and 200 questions.

`raw_pool_manifest.json` records the current downloaded raw pool scale:

- 17 files
- 7.04 MB raw
- 46,503 detected rows/items
- FRED macro, market/index, SEC submissions, Federal Register regulations, and
  GitHub software releases

Fixture rows intentionally cover multiple domains and temporal traps:

- finance exact-year facts
- software version claims
- policy valid-time ranges
- transaction-time-only publication rows
- broad-window evidence
- conflict claims
- ambiguous or missing evidence

The sample fixture rows are not final benchmark facts. Synthetic traps are
allowed only when clearly marked and should be derived from or paired with real
processed rows in the final dataset.
