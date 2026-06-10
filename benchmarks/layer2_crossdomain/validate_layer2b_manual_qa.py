"""Validator for the Layer 2B manual QA seed file.

The validator checks that each manual question references corpus evidence
consistently before answer generation or judging. It protects the benchmark
input contract; it does not score model answers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
DEFAULT_QA = ROOT / "benchmarks/layer2_crossdomain/data/layer2b_manual_50_qa.jsonl"

ID_FIELDS = ("id", "row_id", "evidence_id", "doc_id", "source_id")
REQUIRED_FIELDS = {
    "question_id",
    "question",
    "reference_answer",
    "expected_evidence_ids",
    "expected_valid_time",
    "source_family",
    "question_type",
    "answer_behavior",
    "difficulty",
    "why_this_is_a_good_temporal_case",
}
ALLOWED_QUESTION_TYPES = {
    "exact_lookup",
    "comparison",
    "wrong_time_trap",
    "transaction_valid_time_trap",
    "broad_window_trap",
    "conflict",
    "partial_or_insufficient",
    "ambiguous_time",
    "chronology",
}
ALLOWED_ANSWER_BEHAVIORS = {
    "answer",
    "compare",
    "warn_conflict",
    "partial",
    "refuse_or_clarify",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}

EVIDENCE_ID_RE = re.compile(r"\bl2:[A-Za-z0-9_:-]+\b")
EXPECTED_QUESTION_IDS = [f"l2b_manual_{idx:03d}" for idx in range(1, 51)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the Layer 2B manual QA seed dataset.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--qa", default=str(DEFAULT_QA))
    args = parser.parse_args()

    errors: list[str] = []
    case_errors: dict[str, list[str]] = defaultdict(list)
    missing_evidence: dict[str, set[str]] = defaultdict(set)

    corpus_path = Path(args.corpus)
    qa_path = Path(args.qa)
    corpus_rows = _load_jsonl(corpus_path, "corpus", errors)
    cases = _load_jsonl(qa_path, "qa", errors)
    evidence_ids = _build_evidence_id_set(corpus_rows)

    _validate_global_case_contract(cases, errors)
    for index, case in enumerate(cases, start=1):
        _validate_case(index, case, evidence_ids, case_errors, missing_evidence)

    failed_case_ids = sorted(case_errors)
    passed_cases = max(0, len(cases) - len(failed_case_ids))
    failed_cases = len(failed_case_ids)

    print("Layer 2B manual QA validation summary")
    print(f"  total cases: {len(cases)}")
    print(f"  passed cases: {passed_cases}")
    print(f"  failed cases: {failed_cases}")
    if missing_evidence:
        print("  missing evidence IDs:")
        for evidence_id in sorted(missing_evidence):
            question_ids = ", ".join(sorted(missing_evidence[evidence_id]))
            print(f"    - {evidence_id}: {question_ids}")
    else:
        print("  missing evidence IDs: none")

    if errors or case_errors:
        print("\nValidation failures:")
        for error in errors:
            print(f"  - {error}")
        for question_id in failed_case_ids:
            for error in case_errors[question_id]:
                print(f"  - {question_id}: {error}")
        sys.exit(1)

    print("  result: pass")


def _load_jsonl(path: Path, label: str, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        errors.append(f"Missing {label} file: {path}")
        return rows

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"{label} line {line_number} is invalid JSON: {exc}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{label} line {line_number} is not a JSON object.")
                continue
            rows.append(row)
    return rows


def _build_evidence_id_set(rows: list[dict[str, Any]]) -> set[str]:
    evidence_ids: set[str] = set()
    for row in rows:
        _collect_id_fields(row, evidence_ids)
        metadata = row.get("metadata")
        if isinstance(metadata, dict):
            _collect_id_fields(metadata, evidence_ids)
    return evidence_ids


def _collect_id_fields(row: dict[str, Any], evidence_ids: set[str]) -> None:
    for field in ID_FIELDS:
        value = row.get(field)
        if isinstance(value, str) and value:
            evidence_ids.add(value)


def _validate_global_case_contract(cases: list[dict[str, Any]], errors: list[str]) -> None:
    if len(cases) != 50:
        errors.append(f"QA file has {len(cases)} cases, expected exactly 50.")

    question_ids = [case.get("question_id") for case in cases]
    if len(question_ids) != len(set(question_ids)):
        errors.append("QA file contains duplicate question IDs.")

    if question_ids != EXPECTED_QUESTION_IDS:
        errors.append("Question IDs must be exactly l2b_manual_001 through l2b_manual_050 in order.")


def _validate_case(
    index: int,
    case: dict[str, Any],
    evidence_ids: set[str],
    case_errors: dict[str, list[str]],
    missing_evidence: dict[str, set[str]],
) -> None:
    question_id = str(case.get("question_id") or f"line_{index}")

    missing_fields = sorted(REQUIRED_FIELDS - set(case))
    if missing_fields:
        case_errors[question_id].append(f"Missing required fields: {', '.join(missing_fields)}")

    _validate_non_empty_string(case, "question", question_id, case_errors)
    _validate_non_empty_string(case, "reference_answer", question_id, case_errors)
    _validate_non_empty_string(case, "expected_valid_time", question_id, case_errors)
    _validate_non_empty_string(case, "source_family", question_id, case_errors)
    _validate_non_empty_string(case, "why_this_is_a_good_temporal_case", question_id, case_errors)

    _validate_enum(case, "question_type", ALLOWED_QUESTION_TYPES, question_id, case_errors)
    _validate_enum(case, "answer_behavior", ALLOWED_ANSWER_BEHAVIORS, question_id, case_errors)
    _validate_enum(case, "difficulty", ALLOWED_DIFFICULTIES, question_id, case_errors)

    expected_ids = case.get("expected_evidence_ids")
    if not isinstance(expected_ids, list) or not expected_ids or not all(isinstance(item, str) and item for item in expected_ids):
        case_errors[question_id].append("expected_evidence_ids must be a non-empty list of strings.")
        expected_ids = []

    for evidence_id in expected_ids:
        if evidence_id not in evidence_ids:
            case_errors[question_id].append(f"Missing evidence ID in corpus: {evidence_id}")
            missing_evidence[evidence_id].add(question_id)

    reference_answer = case.get("reference_answer")
    if isinstance(reference_answer, str):
        if "Evidence:" not in reference_answer:
            case_errors[question_id].append("reference_answer must contain an 'Evidence:' citation.")
        else:
            cited_ids = EVIDENCE_ID_RE.findall(reference_answer.split("Evidence:", 1)[1])
            if not cited_ids:
                case_errors[question_id].append("Evidence citation does not contain any l2: evidence IDs.")
            elif cited_ids != expected_ids:
                case_errors[question_id].append(
                    "Evidence citation IDs do not match expected_evidence_ids: "
                    f"cited={cited_ids}, expected={expected_ids}"
                )


def _validate_non_empty_string(
    case: dict[str, Any],
    field: str,
    question_id: str,
    case_errors: dict[str, list[str]],
) -> None:
    value = case.get(field)
    if not isinstance(value, str) or not value.strip():
        case_errors[question_id].append(f"{field} must be a non-empty string.")


def _validate_enum(
    case: dict[str, Any],
    field: str,
    allowed_values: set[str],
    question_id: str,
    case_errors: dict[str, list[str]],
) -> None:
    value = case.get(field)
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        case_errors[question_id].append(f"{field} has invalid value {value!r}; allowed values: {allowed}.")


if __name__ == "__main__":
    main()
