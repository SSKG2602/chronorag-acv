# ChronoRAG QA50 Extracted Values

Extracted from existing artifacts only. No model, retriever, validator, or judge rerun was performed.

| Metric | Value | Count | Field path / derivation |
|---|---:|---:|---|
| `cases` | 1.0 | 50/50 | judge rows |
| `answer_rows` | 1.0 | 50/50 | answer rows |
| `strict_combined_pass` | 0.7000 | 35/50 | judge row combined_pass |
| `deterministic_hard_contract_pass` | 0.7600 | 38/50 | judge row deterministic_overall_contract_pass |
| `judge_overall_pass` | 0.7600 | 38/50 | judge_validation.overall_judge_pass |
| `judge_semantic_pass` | 0.9600 | 48/50 | judge_validation.semantic_answer_correct |
| `expected_evidence_cited` | 0.9800 | 49/50 | deterministic_validation.expected_evidence_cited |
| `valid_time_correct` | 0.8400 | 42/50 | judge_validation.valid_time_correct |
| `valid_time_present` | 0.8200 | 41/50 | deterministic_validation.valid_time_present |
| `expected_evidence_retrieved_pre_injection_any` | 0.7400 | 37/50 | expected_evidence_ids ∩ retrieval_metadata.retrieved_evidence_ids_before_injection |
| `expected_evidence_retrieved_pre_injection_all` | 0.6400 | 32/50 | retrieval_metadata.expected_evidence_retrieved_before_injection |
| `expected_evidence_available_after_injection` | 1.0000 | 50/50 | retrieval_metadata.expected_evidence_available_to_model |
| `expected_evidence_injected` | 0.3600 | 18/50 | retrieval_metadata.expected_evidence_injected |

Notes:
- Values extracted from existing ChronoRAG QA50 answer and judge artifacts only.
- Pre-injection any expected evidence is computed from expected_evidence_ids intersecting retrieval_metadata.retrieved_evidence_ids_before_injection.
- Pre-injection all expected evidence uses retrieval_metadata.expected_evidence_retrieved_before_injection when present; this field is all-expected coverage in the existing runner.
- Post-injection availability uses retrieval_metadata.expected_evidence_available_to_model with validation.expected_evidence_available_to_model as fallback.
