from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.schemas import load_corpus, load_questions

DEFAULT_CORPUS = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
DEFAULT_QUESTIONS = Path("benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the generated Layer 2 dataset.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--expected-corpus-rows", type=int, default=5000)
    parser.add_argument("--expected-questions", type=int, default=200)
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    questions_path = Path(args.questions)
    errors: list[str] = []
    if not corpus_path.exists():
        errors.append(f"Missing corpus file: {corpus_path}")
    if not questions_path.exists():
        errors.append(f"Missing question file: {questions_path}")
    if errors:
        _finish(errors)

    corpus = load_corpus(corpus_path)
    questions = load_questions(questions_path)
    corpus_ids = {row.id for row in corpus}
    synthetic_ids = {
        evidence_id
        for question in questions
        for evidence_id in getattr(question, "synthetic_evidence_ids", [])
    }

    _expect(len(corpus) == args.expected_corpus_rows, errors, f"Corpus has {len(corpus)} rows, expected {args.expected_corpus_rows}.")
    _expect(len(questions) == args.expected_questions, errors, f"Questions has {len(questions)} rows, expected {args.expected_questions}.")
    _expect(len(corpus_ids) == len(corpus), errors, "Duplicate evidence IDs found.")
    _expect(len({case.id for case in questions}) == len(questions), errors, "Duplicate question IDs found.")

    for row in corpus:
        _check_date(row.valid_from, errors, f"{row.id}.valid_from")
        _check_date(row.valid_to, errors, f"{row.id}.valid_to")
        _check_date(row.transaction_time, errors, f"{row.id}.transaction_time")
        if row.temporal_type == "transaction_time_only":
            _expect(not row.valid_from and not row.valid_to, errors, f"{row.id} is transaction_time_only but has valid-time fields.")

    for case in questions:
        all_ids = case.expected_evidence_ids + case.acceptable_evidence_ids + case.forbidden_evidence_ids
        for evidence_id in all_ids:
            if evidence_id not in corpus_ids and evidence_id not in synthetic_ids and not evidence_id.startswith("synthetic:"):
                errors.append(f"{case.id} references missing evidence ID: {evidence_id}")
        for token in ("expected_evidence_ids", "required_facts", "forbidden_facts", "acceptable_evidence_ids"):
            _expect(token not in case.question, errors, f"{case.id} leaks answer-key token in question text: {token}")
        if case.expected_behavior in {"answer", "compare", "prefer_exact", "conflict_warning"}:
            _expect(bool(case.required_facts), errors, f"{case.id} answerable case has empty required_facts.")
        if "partial" in case.category or "insufficient" in case.category:
            _expect(case.expected_behavior in {"partial", "refuse", "clarify"}, errors, f"{case.id} partial category has wrong behavior.")

    domain_counts = Counter(row.domain for row in corpus)
    category_counts = Counter(case.category for case in questions)
    _expect(len(domain_counts) >= 5, errors, "Corpus domain distribution collapsed below five domains.")
    _expect(len(category_counts) >= 8, errors, "Question category distribution collapsed below eight categories.")

    _finish(errors, domain_counts, category_counts)


def _check_date(value: str | None, errors: list[str], label: str) -> None:
    if not value:
        return
    try:
        dt.date.fromisoformat(value[:10])
    except ValueError:
        errors.append(f"Invalid date for {label}: {value}")


def _expect(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def _finish(errors: list[str], domain_counts: Counter | None = None, category_counts: Counter | None = None) -> None:
    if errors:
        print("Layer 2 dataset validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Layer 2 dataset validation passed.")
    if domain_counts is not None:
        print("Domain distribution:")
        for domain, count in sorted(domain_counts.items()):
            print(f"- {domain}: {count}")
    if category_counts is not None:
        print("Category distribution:")
        for category, count in sorted(category_counts.items()):
            print(f"- {category}: {count}")


if __name__ == "__main__":
    main()
