from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.schemas import CorpusRow, load_corpus

DEFAULT_CORPUS = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")
DEFAULT_OUT = Path("benchmarks/layer2_crossdomain/data/layer2_questions.jsonl")
CATEGORY_ORDER = [
    "exact_valid_time_retrieval",
    "same_entity_wrong_year_trap",
    "broad_window_distractor",
    "transaction_time_vs_valid_time",
    "conflict_detection",
    "partial_or_insufficient_evidence",
    "cross_domain_temporal_comparison",
    "source_specific_temporal_query",
    "metric_specific_query",
    "ambiguous_time_query",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic Layer 2 benchmark questions from corpus rows.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--target-questions", type=int, default=200)
    args = parser.parse_args()

    corpus = load_corpus(args.corpus)
    questions = build_questions(corpus, args.target_questions)
    _write_jsonl(Path(args.out), questions)
    print(f"Wrote {len(questions)} questions to {args.out}")
    print("Category distribution:")
    for category in CATEGORY_ORDER:
        print(f"- {category}: {sum(1 for row in questions if row['category'] == category)}")


def build_questions(corpus: list[CorpusRow], target: int) -> list[dict[str, Any]]:
    by_domain = _by(corpus, lambda row: row.domain)
    exact_rows = [row for row in corpus if row.temporal_type in {"valid_time_exact", "revision"} and row.valid_from]
    tx_rows = [row for row in corpus if row.temporal_type == "transaction_time_only" and row.transaction_time]
    questions: list[dict[str, Any]] = []
    per_category = target // len(CATEGORY_ORDER)
    remainder = target % len(CATEGORY_ORDER)
    for idx, category in enumerate(CATEGORY_ORDER):
        count = per_category + (1 if idx < remainder else 0)
        builder = CATEGORY_BUILDERS[category]
        questions.extend(builder(corpus, exact_rows, tx_rows, by_domain, count, len(questions)))
    if len(questions) != target:
        raise SystemExit(f"Built {len(questions)} questions, expected {target}.")
    return questions


def _build_exact(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    rows = _sample(exact_rows, count)
    return [
        _question(
            offset + idx,
            "exact_valid_time_retrieval",
            row.domain,
            f"What was {row.entity} {row.metric_or_claim} on {row.valid_from}?",
            "answer",
            [row.id],
            [],
            _wrong_year_ids(row, exact_rows),
            _required(row),
            _forbidden_wrong_year(row, exact_rows),
            [row.valid_from[:4]],
            "Exact valid-time retrieval from source-backed row.",
        )
        for idx, row in enumerate(rows)
    ]


def _build_wrong_year(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    pairs = _same_entity_pairs(exact_rows)
    rows = _sample(pairs, count)
    questions = []
    for idx, (row, wrong) in enumerate(rows):
        questions.append(
            _question(
                offset + idx,
                "same_entity_wrong_year_trap",
                row.domain,
                f"For {row.entity}, answer {row.metric_or_claim} for {row.valid_from[:4]}, not {wrong.valid_from[:4]}.",
                "answer",
                [row.id],
                [],
                [wrong.id],
                _required(row),
                _required(wrong),
                [row.valid_from[:4]],
                "Same entity wrong-year trap.",
            )
        )
    return questions


def _build_broad(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    rows = _sample(exact_rows, count)
    questions = []
    for idx, row in enumerate(rows):
        questions.append(
            _question(
                offset + idx,
                "broad_window_distractor",
                row.domain,
                f"Should broad background evidence outrank exact {row.valid_from[:4]} evidence for {row.entity} {row.metric_or_claim}?",
                "prefer_exact",
                [row.id],
                [],
                [],
                ["exact", row.valid_from[:4]],
                [],
                [row.valid_from[:4]],
                "Exact evidence should be preferred over broad context.",
            )
        )
    return questions


def _build_tx(_corpus, exact_rows, tx_rows, _by_domain, count, offset):
    pairs = _pair_tx_with_exact(tx_rows, exact_rows)
    questions = []
    for idx, (tx, exact) in enumerate(_sample(pairs, count)):
        questions.append(
            _question(
                offset + idx,
                "transaction_time_vs_valid_time",
                exact.domain,
                f"{tx.entity} has a publication or filing record on {tx.transaction_time}; what valid-time evidence answers {exact.metric_or_claim} for {exact.valid_from[:4]}?",
                "answer",
                [exact.id],
                [],
                [tx.id],
                _required(exact),
                [tx.transaction_time[:4]],
                [exact.valid_from[:4]],
                "Publication, filing, or release time must not be treated as valid time.",
            )
        )
    return questions


def _build_conflict(corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    candidates = [row for row in exact_rows if row.value is not None]
    rows = _sample(candidates, count)
    questions = []
    for idx, row in enumerate(rows):
        conflict_id = f"synthetic:conflict:{row.id}"
        questions.append(
            _question(
                offset + idx,
                "conflict_detection",
                row.domain,
                f"Two sources disagree about {row.entity} {row.metric_or_claim} for {row.valid_from[:4]}. What should the answer do?",
                "conflict_warning",
                [row.id],
                [conflict_id],
                [],
                [str(row.value), "conflict"],
                [],
                [row.valid_from[:4]],
                "Synthetic conflict marker is intentionally allowed for validator coverage.",
                synthetic_ids=[conflict_id],
            )
        )
    return questions


def _build_partial(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    rows = _sample(exact_rows, count)
    questions = []
    for idx, row in enumerate(rows):
        missing_year = str(int(row.valid_from[:4]) - 1)
        questions.append(
            _question(
                offset + idx,
                "partial_or_insufficient_evidence",
                row.domain,
                f"What was {row.entity} {row.metric_or_claim} in {missing_year}? If exact evidence is missing, do not answer confidently.",
                "partial",
                [],
                [row.id],
                [],
                ["insufficient"],
                [],
                [missing_year],
                "Expected partial/refusal because exact adjacent-year evidence is not guaranteed.",
            )
        )
    return questions


def _build_cross(corpus, exact_rows, _tx_rows, by_domain, count, offset):
    domains = [domain for domain, rows in by_domain.items() if rows]
    pairs = []
    for idx, domain in enumerate(domains):
        left = _first_exact(by_domain[domain])
        right = _first_exact(by_domain[domains[(idx + 1) % len(domains)]])
        if left and right and left.domain != right.domain:
            pairs.append((left, right))
    questions = []
    for idx, (left, right) in enumerate(_sample(pairs, count)):
        questions.append(
            _question(
                offset + idx,
                "cross_domain_temporal_comparison",
                left.domain,
                f"Compare {left.entity} {left.metric_or_claim} in {left.valid_from[:4]} with {right.entity} {right.metric_or_claim} in {right.valid_from[:4]}.",
                "compare",
                [left.id, right.id],
                [],
                [],
                [str(left.value), str(right.value)],
                [],
                [left.valid_from[:4], right.valid_from[:4]],
                "Cross-domain temporal comparison.",
            )
        )
    return questions


def _build_source_specific(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    rows = _sample(exact_rows, count)
    return [
        _question(
            offset + idx,
            "source_specific_temporal_query",
            row.domain,
            f"Using {row.source_family} evidence, what does it say about {row.entity} {row.metric_or_claim} for {row.valid_from[:4]}?",
            "answer",
            [row.id],
            [],
            [],
            _required(row),
            [],
            [row.valid_from[:4]],
            "Source-specific temporal query.",
        )
        for idx, row in enumerate(rows)
    ]


def _build_metric_specific(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    rows = _sample(exact_rows, count)
    questions = []
    for idx, row in enumerate(rows):
        questions.append(
            _question(
                offset + idx,
                "metric_specific_query",
                row.domain,
                f"For {row.entity} in {row.valid_from[:4]}, answer only the metric {row.metric_or_claim}.",
                "answer",
                [row.id],
                [],
                _same_entity_different_metric(row, exact_rows),
                _required(row),
                [],
                [row.valid_from[:4]],
                "Metric-specific query.",
            )
        )
    return questions


def _build_ambiguous(_corpus, exact_rows, _tx_rows, _by_domain, count, offset):
    rows = _sample(exact_rows, count)
    return [
        _question(
            offset + idx,
            "ambiguous_time_query",
            row.domain,
            f"Around the recent period, what was {row.entity} {row.metric_or_claim}?",
            "clarify",
            [],
            [row.id],
            [],
            ["ambiguous"],
            [],
            [],
            "Temporal target is intentionally ambiguous.",
        )
        for idx, row in enumerate(rows)
    ]


CATEGORY_BUILDERS = {
    "exact_valid_time_retrieval": _build_exact,
    "same_entity_wrong_year_trap": _build_wrong_year,
    "broad_window_distractor": _build_broad,
    "transaction_time_vs_valid_time": _build_tx,
    "conflict_detection": _build_conflict,
    "partial_or_insufficient_evidence": _build_partial,
    "cross_domain_temporal_comparison": _build_cross,
    "source_specific_temporal_query": _build_source_specific,
    "metric_specific_query": _build_metric_specific,
    "ambiguous_time_query": _build_ambiguous,
}


def _question(
    idx: int,
    category: str,
    domain: str,
    question: str,
    behavior: str,
    expected: list[str],
    acceptable: list[str],
    forbidden: list[str],
    required_facts: list[str],
    forbidden_facts: list[str],
    expected_valid_time: list[str],
    notes: str,
    synthetic_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"l2q:{idx:04d}:{category}",
        "domain": domain,
        "question": question,
        "category": category,
        "expected_behavior": behavior,
        "expected_evidence_ids": expected,
        "acceptable_evidence_ids": acceptable,
        "forbidden_evidence_ids": forbidden,
        "required_facts": [str(item) for item in required_facts if item not in {None, ""}],
        "forbidden_facts": [str(item) for item in forbidden_facts if item not in {None, ""}],
        "expected_valid_time": expected_valid_time,
        "notes": notes,
        "synthetic_evidence_ids": synthetic_ids or [],
    }


def _required(row: CorpusRow) -> list[str]:
    facts = [row.entity, row.valid_from[:4] if row.valid_from else "", str(row.value) if row.value is not None else ""]
    return [fact for fact in facts if fact]


def _wrong_year_ids(row: CorpusRow, rows: list[CorpusRow]) -> list[str]:
    return [other.id for other in rows if other.entity == row.entity and other.id != row.id and other.valid_from != row.valid_from][:3]


def _forbidden_wrong_year(row: CorpusRow, rows: list[CorpusRow]) -> list[str]:
    ids = set(_wrong_year_ids(row, rows))
    return [str(other.value) for other in rows if other.id in ids and other.value is not None]


def _same_entity_pairs(rows: list[CorpusRow]) -> list[tuple[CorpusRow, CorpusRow]]:
    by_entity = _by(rows, lambda row: f"{row.domain}:{row.entity}:{row.metric_or_claim}")
    pairs = []
    for group in by_entity.values():
        group = sorted(group, key=lambda row: row.valid_from or "")
        for idx in range(1, len(group)):
            pairs.append((group[idx], group[idx - 1]))
    return pairs


def _pair_tx_with_exact(tx_rows: list[CorpusRow], exact_rows: list[CorpusRow]) -> list[tuple[CorpusRow, CorpusRow]]:
    pairs = []
    for tx in tx_rows:
        exact = next((row for row in exact_rows if row.domain == tx.domain or row.entity == tx.entity), None)
        if exact:
            pairs.append((tx, exact))
    return pairs


def _same_entity_different_metric(row: CorpusRow, rows: list[CorpusRow]) -> list[str]:
    return [
        other.id
        for other in rows
        if other.entity == row.entity and other.metric_or_claim != row.metric_or_claim and other.valid_from == row.valid_from
    ][:3]


def _first_exact(rows: list[CorpusRow]) -> CorpusRow | None:
    return next((row for row in rows if row.temporal_type in {"valid_time_exact", "revision"} and row.valid_from), None)


def _by(rows: list[CorpusRow], key_fn) -> dict[str, list[CorpusRow]]:
    grouped: dict[str, list[CorpusRow]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    return grouped


def _sample(items: list[Any], count: int) -> list[Any]:
    if not items:
        raise SystemExit("Not enough corpus support to build requested Layer 2 questions.")
    if len(items) >= count:
        return [items[round(idx * (len(items) - 1) / max(1, count - 1))] for idx in range(count)]
    output = []
    for idx in range(count):
        output.append(items[idx % len(items)])
    return output


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
