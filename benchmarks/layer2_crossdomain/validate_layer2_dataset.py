from __future__ import annotations

import argparse
import datetime as dt
import importlib
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.schemas import load_corpus, load_questions

ACTIVE_RETRIEVAL_METHODS = {"metadata_temporal_rag", "chronorag_full"}
DEFAULT_METHODS = sorted(ACTIVE_RETRIEVAL_METHODS)
WRONG_TIME_RE = re.compile(
    r"\b(?:for|in|on)\s+(?P<target>\d{4}(?:-\d{2}-\d{2})?)\b.*?\bnot\s+(?:for|in|on\s+)?(?P<forbidden>\d{4}(?:-\d{2}-\d{2})?)\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
VERSION_RE = re.compile(r"\bv\d+\.\d+(?:\.\d+)?(?:[-.]?(?:alpha|beta|rc)\.?\d+)?\b", re.IGNORECASE)

DEFAULT_CORPUS = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
DEFAULT_QUESTIONS = Path("benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")
LAYER2_ROOT = ROOT / "benchmarks/layer2_crossdomain"
LAYER2_DOCS = (ROOT / "docs/ROADMAP.md", ROOT / "docs/TECHNICAL_REPORT.md")
DETACHED_METHOD_LABEL = "".join(["g", "s", "m"])
DETACHED_METHOD_RE = re.compile(rf"\b{DETACHED_METHOD_LABEL}\b|chronorag_{DETACHED_METHOD_LABEL}", re.IGNORECASE)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the generated Layer 2 dataset.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--expected-corpus-rows", type=int, default=5000)
    parser.add_argument("--expected-questions", type=int, default=200)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=DEFAULT_METHODS,
        help="Active retrieval methods that must be importable before a full run.",
    )
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    questions_path = Path(args.questions)
    errors: list[str] = []
    # Validation checks the public retrieval boundary before a run: active
    # methods must import, but no retrieval, Vertex, or scoring logic executes.
    _check_active_methods(args.methods, errors)
    _check_no_detached_method_references(errors)
    if not corpus_path.exists():
        errors.append(f"Missing corpus file: {corpus_path}")
    if not questions_path.exists():
        errors.append(f"Missing question file: {questions_path}")
    if errors:
        _finish(errors)

    corpus = load_corpus(corpus_path)
    questions = load_questions(questions_path)
    corpus_ids = {row.id for row in corpus}
    corpus_by_id = {row.id: row for row in corpus}

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

    errors.extend(validate_question_contracts(questions, corpus_by_id))

    domain_counts = Counter(row.domain for row in corpus)
    category_counts = Counter(case.category for case in questions)
    _expect(len(domain_counts) >= 5, errors, "Corpus domain distribution collapsed below five domains.")
    _expect(len(category_counts) >= 8, errors, "Question category distribution collapsed below eight categories.")

    _finish(errors, domain_counts, category_counts)

def validate_question_contracts(questions: list[Any], corpus_by_id: dict[str, Any]) -> list[str]:
    """Validate that every Layer 2A answer key is recoverable from the question."""
    errors: list[str] = []
    corpus_ids = set(corpus_by_id)
    for case in questions:
        _check_question_integrity(case, corpus_by_id, corpus_ids, errors)
    return errors


def _check_active_methods(methods: list[str], errors: list[str]) -> None:
    for method in methods:
        if method not in ACTIVE_RETRIEVAL_METHODS:
            errors.append(f"Inactive or unknown Layer 2A method requested: {method}")
            continue
        try:
            # Import only the runner module. This catches broken registry paths
            # without running retrieval or calling Vertex.
            importlib.import_module(f"benchmarks.layer2_crossdomain.methods.{method}.runner")
        except Exception as exc:  # pragma: no cover - message is what matters.
            errors.append(f"Cannot import Layer 2A method {method}: {exc}")


def _check_question_integrity(case, corpus_by_id: dict[str, Any], corpus_ids: set[str], errors: list[str]) -> None:
    expected = set(case.expected_evidence_ids)
    acceptable = set(case.acceptable_evidence_ids)
    forbidden = set(case.forbidden_evidence_ids)
    all_ids = case.expected_evidence_ids + case.acceptable_evidence_ids + case.forbidden_evidence_ids

    for evidence_id in all_ids:
        if evidence_id not in corpus_ids:
            errors.append(f"{case.id} references missing evidence ID: {evidence_id}")
        if evidence_id.startswith("synthetic:"):
            errors.append(f"{case.id} references synthetic evidence ID not present in corpus: {evidence_id}")

    for evidence_id in getattr(case, "synthetic_evidence_ids", []):
        if evidence_id not in corpus_ids:
            errors.append(f"{case.id} synthetic_evidence_ids references missing corpus ID: {evidence_id}")

    expected_forbidden_overlap = sorted(expected & forbidden)
    acceptable_forbidden_overlap = sorted(acceptable & forbidden)
    _expect(
        not expected_forbidden_overlap,
        errors,
        f"{case.id} has evidence both expected and forbidden: {', '.join(expected_forbidden_overlap)}",
    )
    _expect(
        not acceptable_forbidden_overlap,
        errors,
        f"{case.id} has evidence both acceptable and forbidden: {', '.join(acceptable_forbidden_overlap)}",
    )

    for token in ("expected_evidence_ids", "required_facts", "forbidden_facts", "acceptable_evidence_ids"):
        _expect(token not in case.question, errors, f"{case.id} leaks answer-key token in question text: {token}")

    if case.category in {"same_entity_wrong_year_trap", "same_entity_wrong_time_trap"}:
        _expect(
            not _has_malformed_wrong_time_wording(case.question),
            errors,
            f"{case.id} has malformed wrong-time wording: target time and forbidden time are identical or only repeat the same year.",
        )

    _check_recoverable_evidence_contract(case, corpus_by_id, errors)

    if case.expected_behavior in {"answer", "compare", "prefer_exact", "conflict_warning"}:
        _expect(bool(case.required_facts), errors, f"{case.id} answerable case has empty required_facts.")
    if "partial" in case.category or "insufficient" in case.category:
        _expect(case.expected_behavior in {"partial", "refuse", "clarify"}, errors, f"{case.id} partial category has wrong behavior.")


def _check_recoverable_evidence_contract(case: Any, corpus_by_id: dict[str, Any], errors: list[str]) -> None:
    question = case.question or ""
    question_norm = _normalize(question)
    question_dates = set(DATE_RE.findall(question))
    question_years = set(YEAR_RE.findall(question))
    expected_rows = [corpus_by_id[evidence_id] for evidence_id in case.expected_evidence_ids if evidence_id in corpus_by_id]

    for row in expected_rows:
        valid_from = getattr(row, "valid_from", None)
        # V3 exact-date cases must expose the date they expect. This prevents a
        # year-only question from silently requiring a hidden exact evidence row.
        if _is_exact_dated_row(row) and valid_from and valid_from not in question_dates:
            errors.append(f"{case.id} expects exact-date row {row.id} but question omits {valid_from}.")
        if (
            len(expected_rows) == 1
            and _is_exact_dated_row(row)
            and valid_from
            and valid_from not in question_dates
            and valid_from[:4] in question_years
        ):
            errors.append(f"{case.id} is year-only but has one hidden exact-date expected ID: {row.id}.")

        for version in _version_tokens_for_row(row):
            if version.lower() not in question.lower():
                errors.append(f"{case.id} expects version row {row.id} but question omits version {version}.")

    if case.category == "source_specific_exact_time":
        for row in expected_rows:
            anchors = _source_anchors(row)
            if not any(_normalize(anchor) and _normalize(anchor) in question_norm for anchor in anchors):
                errors.append(f"{case.id} source-specific question omits source anchor for {row.id}.")

    if case.category == "metric_specific_exact_time":
        for row in expected_rows:
            metric = getattr(row, "metric_or_claim", "")
            if _normalize(metric) not in question_norm and not (_version_tokens_for_row(row) & {item.lower() for item in VERSION_RE.findall(question)}):
                errors.append(f"{case.id} metric-specific question omits metric/version for {row.id}.")

    if case.category in {"cross_domain_temporal_comparison", "multi_slot_temporal_coverage"}:
        if len(expected_rows) < 2:
            errors.append(f"{case.id} {case.category} must include at least two expected slot rows.")
        for row in expected_rows:
            valid_from = getattr(row, "valid_from", None)
            if valid_from and valid_from not in question_dates:
                errors.append(f"{case.id} slot question omits date {valid_from} for {row.id}.")
            if _normalize(getattr(row, "entity", "")) not in question_norm:
                errors.append(f"{case.id} slot question omits entity for {row.id}.")
            if _normalize(getattr(row, "metric_or_claim", "")) not in question_norm:
                errors.append(f"{case.id} slot question omits metric for {row.id}.")


def _is_exact_dated_row(row: Any) -> bool:
    return getattr(row, "temporal_type", None) in {"valid_time_exact", "revision"} and bool(getattr(row, "valid_from", None))


def _version_tokens_for_row(row: Any) -> set[str]:
    text = " ".join(
        str(value or "")
        for value in (
            getattr(row, "metric_or_claim", ""),
            getattr(row, "value", ""),
        )
    )
    return {item.lower() for item in VERSION_RE.findall(text)}


def _source_anchors(row: Any) -> set[str]:
    metadata = getattr(row, "metadata", {}) or {}
    anchors = {
        getattr(row, "source_family", ""),
        getattr(row, "source_file", ""),
        getattr(row, "source_kind", ""),
        metadata.get("source_id", ""),
        metadata.get("source_name", ""),
        metadata.get("source_path", ""),
    }
    return {str(anchor) for anchor in anchors if anchor}


def _normalize(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _has_malformed_wrong_time_wording(question: str) -> bool:
    match = WRONG_TIME_RE.search(question)
    if not match:
        return False
    target = match.group("target")
    forbidden = match.group("forbidden")
    if target == forbidden:
        return True
    # Same-year traps are valid only when the wording gives full different dates.
    # Year-only repeats such as "for 1968, not 1968" are ambiguous and invalid.
    return len(target) == 4 and len(forbidden) == 4 and target == forbidden


def _check_no_detached_method_references(errors: list[str]) -> None:
    paths: list[Path] = []
    for suffix in ("*.py", "*.md"):
        paths.extend(path for path in LAYER2_ROOT.rglob(suffix) if "results" not in path.parts)
    paths.extend(path for path in LAYER2_DOCS if path.exists())
    for path in sorted(set(paths)):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if DETACHED_METHOD_RE.search(text):
            errors.append(
                f"Layer 2A active docs/code reference {DETACHED_METHOD_LABEL.upper()}: {path.relative_to(ROOT)}"
            )


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
