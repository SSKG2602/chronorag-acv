from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase, load_corpus
from benchmarks.layer2_crossdomain.validate_layer2_dataset import validate_question_contracts

DEFAULT_CORPUS = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
DEFAULT_OUT = Path("benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")
DEFAULT_CONFLICT_JSON = Path("benchmarks/layer2_crossdomain/results/conflict_data_contract_blocked_v3.json")
DEFAULT_CONFLICT_MD = Path("benchmarks/layer2_crossdomain/results/conflict_data_contract_blocked_v3.md")
QUESTIONS_PER_CATEGORY = 20
VERSION_RE = re.compile(r"\bv\d+\.\d+(?:\.\d+)?(?:[-.]?(?:alpha|beta|rc)\.?\d+)?\b", re.IGNORECASE)

CATEGORY_ORDER = [
    "exact_valid_time_retrieval",
    "same_entity_wrong_time_trap",
    "valid_time_vs_transaction_time",
    "cross_domain_temporal_comparison",
    "source_specific_exact_time",
    "metric_specific_exact_time",
    "exact_vs_broad_temporal_preference",
    "multi_slot_temporal_coverage",
    "partial_or_insufficient_evidence",
    "ambiguous_time_query",
]


@dataclass(frozen=True)
class CorpusIndexes:
    by_id: dict[str, CorpusRow]
    by_entity: dict[str, list[CorpusRow]]
    by_metric: dict[str, list[CorpusRow]]
    by_source_family: dict[str, list[CorpusRow]]
    by_source_ref: dict[str, list[CorpusRow]]
    by_valid_date: dict[str, list[CorpusRow]]
    by_valid_year: dict[str, list[CorpusRow]]
    by_transaction_time: dict[str, list[CorpusRow]]
    by_domain: dict[str, list[CorpusRow]]
    by_neighborhood: dict[tuple[str, str, str], list[CorpusRow]]
    exact_rows: list[CorpusRow]
    transaction_rows: list[CorpusRow]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Layer 2A v3 question/evidence contracts.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--conflict-json", default=str(DEFAULT_CONFLICT_JSON))
    parser.add_argument("--conflict-md", default=str(DEFAULT_CONFLICT_MD))
    args = parser.parse_args()

    corpus = load_corpus(args.corpus)
    indexes = build_indexes(corpus)
    questions = generate_questions(indexes)
    _validate_generated(questions, indexes)
    _write_jsonl(Path(args.out), questions)
    _write_conflict_blocked_artifact(corpus, Path(args.conflict_json), Path(args.conflict_md))

    print(f"Wrote {len(questions)} questions to {args.out}")
    print("Category distribution:")
    for category in CATEGORY_ORDER:
        count = sum(1 for row in questions if row["category"] == category)
        print(f"- {category}: {count}")


def build_indexes(corpus: list[CorpusRow]) -> CorpusIndexes:
    by_id = {row.id: row for row in corpus}
    by_entity = _group(corpus, lambda row: _key(row.entity))
    by_metric = _group(corpus, lambda row: _key(row.metric_or_claim))
    by_source_family = _group(corpus, lambda row: _key(row.source_family))
    by_source_ref: dict[str, list[CorpusRow]] = defaultdict(list)
    by_valid_date: dict[str, list[CorpusRow]] = defaultdict(list)
    by_valid_year: dict[str, list[CorpusRow]] = defaultdict(list)
    by_transaction_time: dict[str, list[CorpusRow]] = defaultdict(list)
    by_domain = _group(corpus, lambda row: _key(row.domain))
    by_neighborhood = _group(corpus, _neighborhood)

    for row in corpus:
        for source_ref in _source_refs(row):
            by_source_ref[_key(source_ref)].append(row)
        if row.valid_from:
            by_valid_date[row.valid_from].append(row)
            by_valid_year[row.valid_from[:4]].append(row)
        if row.transaction_time:
            by_transaction_time[row.transaction_time].append(row)

    exact_rows = sorted(
        [
            row
            for row in corpus
            if row.temporal_type == "valid_time_exact"
            and row.valid_from
            and row.valid_to == row.valid_from
        ],
        key=_row_sort_key,
    )
    transaction_rows = sorted(
        [row for row in corpus if row.temporal_type == "transaction_time_only" and row.transaction_time],
        key=_row_sort_key,
    )
    return CorpusIndexes(
        by_id=by_id,
        by_entity=dict(by_entity),
        by_metric=dict(by_metric),
        by_source_family=dict(by_source_family),
        by_source_ref=dict(by_source_ref),
        by_valid_date=dict(by_valid_date),
        by_valid_year=dict(by_valid_year),
        by_transaction_time=dict(by_transaction_time),
        by_domain=dict(by_domain),
        by_neighborhood=dict(by_neighborhood),
        exact_rows=exact_rows,
        transaction_rows=transaction_rows,
    )


def generate_questions(indexes: CorpusIndexes) -> list[dict[str, Any]]:
    builders: dict[str, Callable[[CorpusIndexes, int], list[dict[str, Any]]]] = {
        "exact_valid_time_retrieval": _build_exact_valid_time,
        "same_entity_wrong_time_trap": _build_same_entity_wrong_time,
        "valid_time_vs_transaction_time": _build_valid_time_vs_transaction_time,
        "cross_domain_temporal_comparison": _build_cross_domain_comparison,
        "source_specific_exact_time": _build_source_specific_exact_time,
        "metric_specific_exact_time": _build_metric_specific_exact_time,
        "exact_vs_broad_temporal_preference": _build_exact_vs_broad_preference,
        "multi_slot_temporal_coverage": _build_multi_slot_temporal_coverage,
        "partial_or_insufficient_evidence": _build_partial_or_insufficient,
        "ambiguous_time_query": _build_ambiguous_time,
    }
    questions: list[dict[str, Any]] = []
    for category in CATEGORY_ORDER:
        start = len(questions)
        rows = builders[category](indexes, start)
        if len(rows) != QUESTIONS_PER_CATEGORY:
            raise SystemExit(f"{category} produced {len(rows)} questions, expected {QUESTIONS_PER_CATEGORY}.")
        questions.extend(rows)
    if len(questions) != QUESTIONS_PER_CATEGORY * len(CATEGORY_ORDER):
        raise SystemExit(f"Generated {len(questions)} questions, expected 200.")
    return questions


def _build_exact_valid_time(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    rows = _sample_even(_rows_with_wrong_time(indexes.exact_rows, indexes), QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        wrong = _wrong_time_ids(row, indexes, limit=3)
        output.append(
            _question(
                offset + idx,
                "exact_valid_time_retrieval",
                row.domain,
                f"Retrieve {row.entity} {row.metric_or_claim} on {row.valid_from}.",
                "answer",
                [row.id],
                [],
                wrong,
                _required(row),
                _facts_for_ids(wrong, indexes),
                [row.valid_from],
                "Exact valid-time retrieval; the exact target date is visible in the question.",
            )
        )
    return output


def _build_same_entity_wrong_time(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    rows = _sample_even(_rows_with_wrong_time(indexes.exact_rows, indexes), QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        wrong = _wrong_time_ids(row, indexes, limit=3)
        wrong_dates = [indexes.by_id[evidence_id].valid_from for evidence_id in wrong[:2] if indexes.by_id[evidence_id].valid_from]
        not_clause = f", not {wrong_dates[0]}" if wrong_dates else ""
        output.append(
            _question(
                offset + idx,
                "same_entity_wrong_time_trap",
                row.domain,
                f"Retrieve {row.source_family} {row.entity} {row.metric_or_claim} on {row.valid_from}{not_clause}; exclude other same-entity same-metric dates.",
                "answer",
                [row.id],
                [],
                wrong,
                _required(row),
                _facts_for_ids(wrong, indexes),
                [row.valid_from],
                "Same entity/source/metric wrong-time trap with the exact target date exposed.",
            )
        )
    return output


def _build_valid_time_vs_transaction_time(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in indexes.exact_rows
        if row.transaction_time
        and row.valid_from
        and row.transaction_time != row.valid_from
        and _transaction_distractors(row, indexes)
    ]
    rows = _sample_even(candidates, QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        forbidden = _transaction_distractors(row, indexes, limit=3)
        output.append(
            _question(
                offset + idx,
                "valid_time_vs_transaction_time",
                row.domain,
                f"For {row.entity}, retrieve {row.metric_or_claim} using valid time/report date/event date {row.valid_from}, not filing/publication/transaction date {row.transaction_time}.",
                "answer",
                [row.id],
                [],
                forbidden,
                _required(row),
                _facts_for_ids(forbidden, indexes),
                [row.valid_from],
                "Valid-time row is the target; transaction-only or filing-time rows are distractors.",
            )
        )
    return output


def _build_cross_domain_comparison(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    domain_rows = _domain_exact_rows(indexes)
    domain_names = sorted(domain_rows)
    pairs = []
    for idx in range(QUESTIONS_PER_CATEGORY):
        left_domain = domain_names[idx % len(domain_names)]
        right_domain = domain_names[(idx + 1) % len(domain_names)]
        left = _sample_even(domain_rows[left_domain], QUESTIONS_PER_CATEGORY)[idx]
        right = _sample_even(domain_rows[right_domain], QUESTIONS_PER_CATEGORY)[idx]
        pairs.append((left, right))
    output = []
    for idx, (left, right) in enumerate(pairs):
        output.append(
            _question(
                offset + idx,
                "cross_domain_temporal_comparison",
                f"{left.domain}+{right.domain}",
                f"Compare {left.entity} {left.metric_or_claim} on {left.valid_from} with {right.entity} {right.metric_or_claim} on {right.valid_from}.",
                "compare",
                [left.id, right.id],
                [],
                _wrong_time_ids(left, indexes, limit=1) + _wrong_time_ids(right, indexes, limit=1),
                _required(left) + _required(right),
                [],
                [left.valid_from, right.valid_from],
                "Cross-domain comparison with both entity/metric/date slots explicit.",
            )
        )
    return output


def _build_source_specific_exact_time(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    rows = _sample_even(_rows_with_wrong_time(indexes.exact_rows, indexes), QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        wrong_source = [other.id for other in indexes.by_valid_date.get(row.valid_from, []) if other.source_family != row.source_family][:1]
        forbidden = _dedupe(wrong_source + _wrong_time_ids(row, indexes, limit=3))
        output.append(
            _question(
                offset + idx,
                "source_specific_exact_time",
                row.domain,
                f"Using source_family {row.source_family}, retrieve {row.entity} {row.metric_or_claim} on {row.valid_from}.",
                "answer",
                [row.id],
                [],
                forbidden,
                _required(row) + [row.source_family],
                _facts_for_ids(forbidden, indexes),
                [row.valid_from],
                "Source-specific exact-time query; source_family and exact date are exposed.",
            )
        )
    return output


def _build_metric_specific_exact_time(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in indexes.exact_rows
        if _version_tokens(row) and _sibling_version_ids(row, indexes)
    ]
    rows = _sample_even(candidates, QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        forbidden = _sibling_version_ids(row, indexes, limit=3)
        output.append(
            _question(
                offset + idx,
                "metric_specific_exact_time",
                row.domain,
                f"For {row.entity}, retrieve exact metric {row.metric_or_claim} on {row.valid_from}; exclude sibling release versions.",
                "answer",
                [row.id],
                [],
                forbidden,
                _required(row) + [row.metric_or_claim],
                _facts_for_ids(forbidden, indexes),
                [row.valid_from],
                "Metric/version-specific exact-time query with the exact version token exposed.",
            )
        )
    return output


def _build_exact_vs_broad_preference(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    candidates = [row for row in indexes.exact_rows if _transaction_distractors(row, indexes)]
    rows = _sample_even(candidates, QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        forbidden = _transaction_distractors(row, indexes, limit=3)
        output.append(
            _question(
                offset + idx,
                "exact_vs_broad_temporal_preference",
                row.domain,
                f"Retrieve exact valid-time evidence for {row.entity} {row.metric_or_claim} on {row.valid_from}; prefer the exact date over broad/background or transaction-only records.",
                "prefer_exact",
                [row.id],
                [],
                forbidden,
                _required(row) + ["exact valid-time"],
                _facts_for_ids(forbidden, indexes),
                [row.valid_from],
                "Exact valid-time row should outrank background or transaction-only distractors.",
            )
        )
    return output


def _build_multi_slot_temporal_coverage(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    rows = _sample_even(indexes.exact_rows, QUESTIONS_PER_CATEGORY * 3)
    output = []
    for idx in range(QUESTIONS_PER_CATEGORY):
        slot_count = 3 if idx % 5 == 0 else 2
        slots = rows[idx * 3 : idx * 3 + slot_count]
        slot_text = " and ".join(f"{row.entity} {row.metric_or_claim} on {row.valid_from}" for row in slots)
        forbidden: list[str] = []
        for row in slots:
            forbidden.extend(_wrong_time_ids(row, indexes, limit=1))
        output.append(
            _question(
                offset + idx,
                "multi_slot_temporal_coverage",
                "+".join(row.domain for row in slots),
                f"Retrieve evidence for {slot_text}.",
                "compare",
                [row.id for row in slots],
                [],
                _dedupe(forbidden),
                [fact for row in slots for fact in _required(row)],
                _facts_for_ids(forbidden, indexes),
                [row.valid_from for row in slots if row.valid_from],
                "Multi-slot temporal coverage; every slot is explicit in the question.",
            )
        )
    return output


def _build_partial_or_insufficient(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    rows = _sample_even([row for row in indexes.transaction_rows if row.domain == "federal_register"], QUESTIONS_PER_CATEGORY)
    output = []
    for idx, row in enumerate(rows):
        output.append(
            _question(
                offset + idx,
                "partial_or_insufficient_evidence",
                row.domain,
                f"What valid-time/event-date evidence exists for {row.entity} {row.metric_or_claim}? If the corpus only has the publication record on {row.transaction_time}, report partial or insufficient evidence.",
                "partial",
                [],
                [row.id],
                [],
                ["partial", "insufficient"],
                [],
                [],
                "Diagnostic partial case: no hidden exact valid-time target is assigned.",
            )
        )
    return output


def _build_ambiguous_time(indexes: CorpusIndexes, offset: int) -> list[dict[str, Any]]:
    groups = [
        sorted(group, key=_row_sort_key)
        for group in indexes.by_neighborhood.values()
        if len([row for row in group if row.valid_from and row.temporal_type == "valid_time_exact"]) >= 3
    ]
    groups = sorted(groups, key=lambda group: _row_sort_key(group[0]))
    selected_groups = _sample_even(groups, QUESTIONS_PER_CATEGORY)
    output = []
    for idx, group in enumerate(selected_groups):
        plausible = [row for row in group if row.valid_from and row.temporal_type == "valid_time_exact"][:5]
        first = plausible[0]
        output.append(
            _question(
                offset + idx,
                "ambiguous_time_query",
                first.domain,
                f"Which {first.entity} {first.metric_or_claim} record should be used for the requested period? Ask for clarification because no exact date is provided.",
                "clarify",
                [],
                [row.id for row in plausible],
                [],
                ["ambiguous", "clarification"],
                [],
                [],
                "Diagnostic ambiguity case: multiple plausible rows are acceptable and no hidden exact target is assigned.",
            )
        )
    return output


def _question(
    idx: int,
    category: str,
    domain: str,
    question: str,
    behavior: str,
    expected: list[str],
    acceptable: list[str],
    forbidden: list[str],
    required_facts: list[Any],
    forbidden_facts: list[Any],
    expected_valid_time: list[str],
    notes: str,
) -> dict[str, Any]:
    case_id = f"l2q:{idx:04d}:{category}"
    return {
        "id": case_id,
        "case_id": case_id,
        "domain": domain,
        "question": _clean(question),
        "category": category,
        "expected_behavior": behavior,
        "expected_evidence_ids": _dedupe(expected),
        "acceptable_evidence_ids": _dedupe(acceptable),
        "forbidden_evidence_ids": _dedupe([item for item in forbidden if item not in set(expected) and item not in set(acceptable)]),
        "required_facts": _clean_facts(required_facts),
        "forbidden_facts": _clean_facts(forbidden_facts),
        "expected_valid_time": _dedupe(expected_valid_time),
        "notes": notes,
        "synthetic_evidence_ids": [],
    }


def _validate_generated(questions: list[dict[str, Any]], indexes: CorpusIndexes) -> None:
    cases = [QuestionCase.from_dict(row) for row in questions]
    errors = validate_question_contracts(cases, indexes.by_id)
    category_counts = {category: sum(1 for row in questions if row["category"] == category) for category in CATEGORY_ORDER}
    for category, count in category_counts.items():
        if count != QUESTIONS_PER_CATEGORY:
            errors.append(f"{category} generated {count} questions, expected {QUESTIONS_PER_CATEGORY}.")
    if len(questions) != 200:
        errors.append(f"Generated {len(questions)} questions, expected 200.")
    if errors:
        print("Layer 2 question generation failed validation:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)


def _write_conflict_blocked_artifact(corpus: list[CorpusRow], output_json: Path, output_md: Path) -> None:
    conflict_rows = [row for row in corpus if row.temporal_type == "conflict_claim"]
    payload = {
        "status": "data_contract_blocked",
        "scored_category": "removed",
        "reason": "No real two-sided conflict pairs are present in layer2_corpus.jsonl; synthetic conflict IDs are not used in v3 questions.",
        "conflict_claim_rows": len(conflict_rows),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(
        "\n".join(
            [
                "# Conflict Data Contract Status",
                "",
                "Status: data-contract blocked.",
                "",
                "Layer 2A v3 does not include `conflict_detection` as a scored retrieval category because the corpus does not contain real two-sided conflict evidence pairs. Synthetic conflict IDs are not used.",
                f"Conflict-claim rows found: {len(conflict_rows)}.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _rows_with_wrong_time(rows: list[CorpusRow], indexes: CorpusIndexes) -> list[CorpusRow]:
    return [row for row in rows if _wrong_time_ids(row, indexes)]


def _wrong_time_ids(row: CorpusRow, indexes: CorpusIndexes, limit: int = 3) -> list[str]:
    wrong = [
        other
        for other in indexes.by_neighborhood.get(_neighborhood(row), [])
        if other.id != row.id and other.valid_from and other.valid_from != row.valid_from
    ]
    wrong = sorted(wrong, key=lambda other: (abs(_date_ordinal(other.valid_from) - _date_ordinal(row.valid_from)), other.id))
    return [other.id for other in wrong[:limit]]


def _transaction_distractors(row: CorpusRow, indexes: CorpusIndexes, limit: int = 3) -> list[str]:
    rows = [
        other
        for other in indexes.by_entity.get(_key(row.entity), [])
        if other.temporal_type == "transaction_time_only" and other.id != row.id
    ]
    rows = sorted(rows, key=_row_sort_key)
    return [other.id for other in rows[:limit]]


def _sibling_version_ids(row: CorpusRow, indexes: CorpusIndexes, limit: int = 3) -> list[str]:
    versions = _version_tokens(row)
    if not versions:
        return []
    siblings = []
    for other in indexes.by_entity.get(_key(row.entity), []):
        if other.id == row.id:
            continue
        other_versions = _version_tokens(other)
        if any(_same_major_version(left, right) for left in versions for right in other_versions):
            siblings.append(other)
    siblings = sorted(siblings, key=_row_sort_key)
    return [other.id for other in siblings[:limit]]


def _domain_exact_rows(indexes: CorpusIndexes) -> dict[str, list[CorpusRow]]:
    grouped: dict[str, list[CorpusRow]] = defaultdict(list)
    for row in indexes.exact_rows:
        grouped[row.domain].append(row)
    return {domain: rows for domain, rows in grouped.items() if rows}


def _facts_for_ids(evidence_ids: list[str], indexes: CorpusIndexes) -> list[str]:
    facts = []
    for evidence_id in evidence_ids:
        row = indexes.by_id.get(evidence_id)
        if row:
            facts.extend([row.entity, row.metric_or_claim, row.valid_from or row.transaction_time or "", str(row.value or "")])
    return _clean_facts(facts)


def _required(row: CorpusRow) -> list[str]:
    return _clean_facts([row.entity, row.metric_or_claim, row.valid_from or "", str(row.value or "")])


def _version_tokens(row: CorpusRow) -> set[str]:
    text = " ".join([row.metric_or_claim or "", str(row.value or "")])
    return {item.lower() for item in VERSION_RE.findall(text)}


def _same_major_version(left: str, right: str) -> bool:
    left_parts = left.lower().lstrip("v").split(".")
    right_parts = right.lower().lstrip("v").split(".")
    return bool(left_parts and right_parts and left_parts[0] == right_parts[0] and left != right)


def _source_refs(row: CorpusRow) -> set[str]:
    metadata = row.metadata or {}
    refs = {
        row.source_family,
        row.source_file or "",
        row.source_kind or "",
        str(metadata.get("source_id") or ""),
        str(metadata.get("source_name") or ""),
        str(metadata.get("source_path") or ""),
    }
    return {item for item in refs if item}


def _neighborhood(row: CorpusRow) -> tuple[str, str, str]:
    return (_key(row.source_family), _key(row.entity), _key(row.metric_or_claim))


def _row_sort_key(row: CorpusRow) -> tuple[str, str, str, str]:
    return (row.domain, row.entity, row.valid_from or row.transaction_time or "", row.id)


def _date_ordinal(value: str | None) -> int:
    if not value:
        return 0
    return int(value.replace("-", "")[:8])


def _sample_even(items: list[Any], count: int) -> list[Any]:
    if len(items) < count:
        raise SystemExit(f"Need {count} supported items, found {len(items)}.")
    if count == 1:
        return [items[0]]
    return [items[round(index * (len(items) - 1) / (count - 1))] for index in range(count)]


def _group(rows: list[CorpusRow], key_fn: Callable[[CorpusRow], Any]) -> dict[Any, list[CorpusRow]]:
    grouped: dict[Any, list[CorpusRow]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    return grouped


def _key(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("|", "/").split())


def _clean_facts(values: list[Any]) -> list[str]:
    return _dedupe([_clean(value) for value in values if _clean(value)])


def _dedupe(values: list[Any]) -> list[Any]:
    seen = set()
    output = []
    for value in values:
        if value in seen or value in {None, ""}:
            continue
        seen.add(value)
        output.append(value)
    return output


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
