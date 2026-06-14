from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.fusion import monotone_temporal_fusion
from benchmarks.layer2_crossdomain.evaluate_retrieval_only import score_case
from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import (
    AdaptedChronoEvidence,
    _normalize,
    _temporal_weight,
    prepare_chronorag_context,
)
from benchmarks.layer2_crossdomain.methods.chronorag_full.finalization import (
    AblationConfig,
    _apply_exact_valid_time_cleanup,
    _apply_source_metric_adjustments,
    _apply_transaction_role_cleanup,
    _row_matches_constraint_valid_time,
    _single_positive_exact_constraint,
    finalize_chronorag_evidence,
)
from benchmarks.layer2_crossdomain.methods.chronorag_full.slot_assembler import (
    _slot_match_score,
    classify_query_intent,
)
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase, load_corpus, load_questions
from benchmarks.layer2_crossdomain.temporal_precision import (
    extract_temporal_constraints,
    has_negative_exact_temporal_match,
)
from core.retrieval.lexical_bm25 import bm25_search


TRACE_COLUMNS = [
    "query_id",
    "query_text",
    "candidate_evidence_id",
    "rank_before_finalization",
    "rank_after_finalization",
    "selected",
    "expected",
    "forbidden",
    "source_family",
    "metric",
    "valid_time",
    "transaction_time",
    "semantic_score",
    "bm25_score",
    "dense_score",
    "temporal_precision_score",
    "valid_time_fit",
    "interval_overlap_score",
    "transaction_time_penalty",
    "forbidden_time_penalty",
    "source_metric_score",
    "slot_score",
    "fusion_score",
    "final_score",
    "category_primary_relevant",
    "reason_or_notes",
]


def main() -> None:
    args = parse_args()
    questions = load_questions(args.questions)
    corpus = load_corpus(args.corpus)
    selected_questions = select_representative_questions(questions, args.limit_queries)
    if not selected_questions:
        raise SystemExit("No representative Layer 2A queries found.")

    prepared = prepare_chronorag_context(corpus)
    rows: list[dict[str, Any]] = []
    for case in selected_questions:
        rows.extend(trace_case(case, prepared.adapted_chunks, args.candidate_limit, args.top_k))

    write_jsonl(args.output_jsonl, rows)
    write_csv(args.output_csv, rows)
    print(f"Exported {len(rows)} candidate trace rows for {len(selected_questions)} queries.")
    print("Traced query IDs:")
    for case in selected_questions:
        print(f"- {case.id}")
    numeric_fields = sorted({key for row in rows for key in numeric_trace_fields(row)})
    print("Numeric trace fields:")
    for field in numeric_fields:
        print(f"- {field}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export retrieval-only candidate traces for Figure 9.")
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--limit-queries", type=int, default=3)
    parser.add_argument("--candidate-limit", type=int, default=15)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def select_representative_questions(questions: list[QuestionCase], limit: int) -> list[QuestionCase]:
    preferred_ids = [
        "l2q:0000:exact_valid_time_retrieval",
        "l2q:0020:same_entity_wrong_time_trap",
        "l2q:0040:valid_time_vs_transaction_time",
    ]
    by_id = {case.id: case for case in questions}
    selected = [by_id[case_id] for case_id in preferred_ids if case_id in by_id]
    if len(selected) < limit:
        selected_ids = {case.id for case in selected}
        for case in questions:
            if case.id in selected_ids:
                continue
            if case.forbidden_evidence_ids and case.category in {
                "same_entity_wrong_time_trap",
                "valid_time_vs_transaction_time",
                "exact_vs_broad_temporal_preference",
            }:
                selected.append(case)
                selected_ids.add(case.id)
            if len(selected) >= limit:
                break
    return selected[: max(0, limit)]


def trace_case(
    case: QuestionCase,
    adapted: list[AdaptedChronoEvidence],
    candidate_limit: int,
    top_k: int,
) -> list[dict[str, Any]]:
    constraints = extract_temporal_constraints(case.question)
    lexical_pairs = bm25_search(case.question, [(item.row.id, item.retrieval_text) for item in adapted], top_k=len(adapted))
    lexical = dict(lexical_pairs)
    lexical_values = list(lexical.values())
    config = AblationConfig()
    scored: list[AdaptedChronoEvidence] = []
    trace_by_id: dict[str, dict[str, Any]] = {}

    for item in adapted:
        row = item.row
        bm25_score = float(lexical.get(row.id, 0.0))
        relevance = _normalize(bm25_score, lexical_values)
        temporal = _temporal_weight(case, row)
        authority = 0.70 if row.source_kind in {"filing", "regulation", "guideline", "changelog"} else 0.50
        transaction_penalty = 0.60 if row.temporal_type == "transaction_time_only" else 0.0
        raw_fusion = monotone_temporal_fusion(
            relevance,
            temporal,
            authority,
            transaction_penalty,
            0.0,
            {"alpha": 0.50, "beta_time": 0.35, "gamma_authority": 0.10, "delta_age": 0.0, "tx_gamma": 0.25},
        )
        negative_exact = has_negative_exact_temporal_match(case, row, constraints)
        fusion_score = 0.0 if negative_exact else raw_fusion
        scored_item = replace(item, score=fusion_score)
        scored.append(scored_item)
        trace_by_id[row.id] = {
            "query_id": case.id,
            "query_text": case.question,
            "candidate_evidence_id": row.id,
            "source_family": row.source_family,
            "metric": row.metric_or_claim,
            "valid_time": valid_time_label(row),
            "transaction_time": row.transaction_time,
            "semantic_score": relevance,
            "bm25_score": bm25_score,
            "dense_score": None,
            "temporal_precision_score": temporal,
            "valid_time_fit": valid_time_fit(case, row, constraints),
            "interval_overlap_score": None,
            "transaction_time_penalty": transaction_penalty,
            "forbidden_time_penalty": 1.0 if negative_exact else 0.0,
            "fusion_score": fusion_score,
        }

    after_exact, _exact_count = _apply_exact_valid_time_cleanup(scored, constraints, case.question)
    after_transaction, _transaction_count = _apply_transaction_role_cleanup(after_exact, constraints, case.question)
    after_source_metric, _source_metric_count = _apply_source_metric_adjustments(after_transaction, case.question)
    selected, metadata = finalize_chronorag_evidence(scored, constraints, case.question, top_k, ablation_config=config)
    selected_ids = {item.row.id for item in selected}
    rank_before = rank_map(scored)
    rank_after = rank_map(after_source_metric)
    score_after_transaction = {item.row.id: item.score for item in after_transaction}
    final_by_id = {item.row.id: item for item in after_source_metric}
    suppression_reasons = ((metadata.get("slot_assembly_report") or {}).get("suppression_reasons") or {})
    slot_scores = compute_slot_scores(case.question, constraints, after_source_metric)

    ids_to_export = ordered_export_ids(
        after_source_metric,
        scored,
        selected_ids,
        set(case.expected_evidence_ids),
        set(case.forbidden_evidence_ids),
        candidate_limit,
    )
    rows: list[dict[str, Any]] = []
    for evidence_id in ids_to_export:
        item = final_by_id.get(evidence_id)
        if item is None:
            continue
        row = item.row
        payload = dict(trace_by_id[evidence_id])
        payload.update(
            {
                "rank_before_finalization": rank_before.get(evidence_id),
                "rank_after_finalization": rank_after.get(evidence_id),
                "selected": evidence_id in selected_ids,
                "expected": evidence_id in set(case.expected_evidence_ids),
                "forbidden": evidence_id in set(case.forbidden_evidence_ids),
                "source_metric_score": item.score - score_after_transaction.get(evidence_id, item.score),
                "slot_score": slot_scores.get(evidence_id),
                "final_score": item.score,
                "category_primary_relevant": category_primary_relevant(case, evidence_id),
                "reason_or_notes": notes_for_candidate(row, payload, suppression_reasons.get(evidence_id, []), selected_ids, case),
            }
        )
        rows.append(payload)
    return rows


def valid_time_label(row: CorpusRow) -> str | None:
    if row.valid_from and row.valid_to and row.valid_to != row.valid_from:
        return f"{row.valid_from}/{row.valid_to}"
    return row.valid_from


def valid_time_fit(case: QuestionCase, row: CorpusRow, constraints: list[Any]) -> float | None:
    constraint = _single_positive_exact_constraint(constraints)
    if constraint is None:
        return None
    return 1.0 if _row_matches_constraint_valid_time(row, constraint) else 0.0


def compute_slot_scores(query_text: str, constraints: list[Any], candidates: list[AdaptedChronoEvidence]) -> dict[str, int | None]:
    intent = classify_query_intent(query_text=query_text, constraints=constraints, candidates=candidates[:200])
    if not intent.comparison_slots:
        return {}
    scores: dict[str, int | None] = {}
    for candidate in candidates:
        scores[candidate.row.id] = max((_slot_match_score(candidate, slot) for slot in intent.comparison_slots), default=0)
    return scores


def rank_map(candidates: list[AdaptedChronoEvidence]) -> dict[str, int]:
    ranked = sorted(enumerate(candidates), key=lambda item: (-item[1].score, item[0]))
    return {item.row.id: rank for rank, (_index, item) in enumerate(ranked, start=1)}


def ordered_export_ids(
    after_finalization: list[AdaptedChronoEvidence],
    before_finalization: list[AdaptedChronoEvidence],
    selected_ids: set[str],
    expected_ids: set[str],
    forbidden_ids: set[str],
    candidate_limit: int,
) -> list[str]:
    ids: list[str] = []
    for pool in (
        sorted(enumerate(after_finalization), key=lambda item: (-item[1].score, item[0])),
        sorted(enumerate(before_finalization), key=lambda item: (-item[1].score, item[0])),
    ):
        for _index, item in pool:
            if len(ids) >= candidate_limit:
                break
            if item.row.id not in ids:
                ids.append(item.row.id)
    for evidence_id in [*selected_ids, *expected_ids, *forbidden_ids]:
        if evidence_id not in ids:
            ids.append(evidence_id)
    return ids


def category_primary_relevant(case: QuestionCase, evidence_id: str) -> bool | None:
    try:
        return bool(score_case(case, [evidence_id])["scores"].get("category_primary_pass"))
    except Exception:
        return None


def notes_for_candidate(
    row: CorpusRow,
    payload: dict[str, Any],
    suppression_reasons: list[str],
    selected_ids: set[str],
    case: QuestionCase,
) -> str:
    notes: list[str] = []
    evidence_id = row.id
    if evidence_id in selected_ids:
        notes.append("selected")
    if evidence_id in case.expected_evidence_ids:
        notes.append("expected")
    if evidence_id in case.forbidden_evidence_ids:
        notes.append("forbidden")
    if payload.get("forbidden_time_penalty"):
        notes.append("negative_exact_temporal_match")
    if row.temporal_type == "transaction_time_only":
        notes.append("transaction_time_only")
    if suppression_reasons:
        notes.append("suppressed:" + ",".join(suppression_reasons))
    return "; ".join(notes)


def numeric_trace_fields(row: dict[str, Any]) -> list[str]:
    fields = []
    for key in [
        "semantic_score",
        "bm25_score",
        "dense_score",
        "temporal_precision_score",
        "valid_time_fit",
        "interval_overlap_score",
        "transaction_time_penalty",
        "forbidden_time_penalty",
        "source_metric_score",
        "slot_score",
        "fusion_score",
        "final_score",
    ]:
        value = row.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            fields.append(key)
    return fields


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in TRACE_COLUMNS})


if __name__ == "__main__":
    main()
