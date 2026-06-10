# Layer 2B Manual 50 QA Seed Dataset

## Purpose

This file summarizes the manually generated Layer 2B natural-language temporal
QA set. The dataset was used for the full-50 answer-synthesis and judge
evaluation, not for retrieval-only scoring.

## Source Corpus Boundary

All expected evidence IDs are validated against the selected 5,000-row Layer 2 evaluation corpus:

`benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl`

The larger raw/provenance pool is not used as the benchmark corpus for this Layer 2B seed set.

## Dataset Size

- Questions: 50
- Dataset artifact: `benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl`
- Validator: `benchmarks/layer2_crossdomain/validate_layer2b_manual_qa.py`

## Source Family Distribution

| Source family | Questions |
| --- | ---: |
| federal_register | 10 |
| github_releases | 7 |
| macro_fred | 15 |
| market_index | 8 |
| sec_submissions | 10 |

## Question Type Distribution

| Question type | Questions |
| --- | ---: |
| ambiguous_time | 4 |
| broad_window_trap | 4 |
| chronology | 5 |
| comparison | 9 |
| exact_lookup | 15 |
| partial_or_insufficient | 3 |
| transaction_valid_time_trap | 3 |
| wrong_time_trap | 7 |

## Answer Behavior Distribution

| Answer behavior | Questions |
| --- | ---: |
| answer | 34 |
| compare | 10 |
| partial | 6 |

## Final Evaluation Artifacts

- Answer result: `benchmarks/layer2_crossdomain/results/layer2b_chronorag_full_layer2b_full50_vertex_final_results.md`
- LLM judge result: `benchmarks/layer2_crossdomain/results/layer2b_judge_layer2b_full50_judge_final_results.md`
- Manual audit: `benchmarks/layer2_crossdomain/results/layer2b_full50_manual_audit.md`

## Boundary

This is the manually generated Layer 2B QA dataset summary. It is separate from
the answer result, LLM judge result, and manual audit note. Expected evidence
was available where needed in the Layer 2B answer-synthesis path, so Layer 2B
does not report retrieval quality; retrieval quality is reported in Layer 2A.
