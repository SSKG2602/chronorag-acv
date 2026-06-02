# Layer 2B Manual 50 QA Seed Dataset

## Purpose

This file summarizes the initial manually generated Layer 2B natural-language temporal QA seed set. The dataset is intended for a future answer-synthesis and judge/evaluator harness, not for retrieval-only scoring.

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

## Warning

This is a manually generated Layer 2B candidate set validated against selected corpus evidence IDs. It is not a final answer-quality result, not an LLM judge result, and not a SOTA claim.
