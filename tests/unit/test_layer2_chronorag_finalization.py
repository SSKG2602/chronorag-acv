from __future__ import annotations

from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import AdaptedChronoEvidence
from benchmarks.layer2_crossdomain.methods.chronorag_full.finalization import finalize_chronorag_evidence
from benchmarks.layer2_crossdomain.schemas import CorpusRow
from benchmarks.layer2_crossdomain.temporal_precision import extract_temporal_constraints


def _row(
    row_id: str,
    *,
    entity: str = "Alpha Corp",
    source_family: str = "alpha_source",
    source_kind: str = "time_series",
    domain: str = "finance",
    metric: str = "revenue",
    valid_from: str | None = "2020-04-20",
    valid_to: str | None = None,
    transaction_time: str | None = None,
    temporal_type: str = "valid_time_exact",
) -> CorpusRow:
    return CorpusRow(
        id=row_id,
        domain=domain,
        source_family=source_family,
        source_file=f"{source_family}.jsonl",
        source_kind=source_kind,
        entity=entity,
        related_entities=[],
        metric_or_claim=metric,
        value="1.0",
        unit="units",
        valid_from=valid_from,
        valid_to=valid_to or valid_from,
        transaction_time=transaction_time,
        temporal_type=temporal_type,  # type: ignore[arg-type]
        raw_text=f"{entity} {metric} was 1.0 on {valid_from or transaction_time}.",
    )


def _candidate(row: CorpusRow, score: float) -> AdaptedChronoEvidence:
    return AdaptedChronoEvidence(
        row=row,
        retrieval_text=row.raw_text,
        temporal_confidence=1.0,
        temporal_source="fixture",
        temporal_metadata={},
        score=score,
    )


def _finalize(query: str, candidates: list[AdaptedChronoEvidence], top_k: int = 5) -> tuple[list[str], dict[str, object]]:
    selected, metadata = finalize_chronorag_evidence(candidates, extract_temporal_constraints(query), query, top_k)
    return [item.row.id for item in selected], metadata


def test_exact_valid_time_cleanup_demotes_same_neighborhood_wrong_time() -> None:
    query = "What was Alpha Corp revenue on 2020-04-20?"
    wrong = _candidate(_row("wrong", valid_from="2020-03-28"), 0.80)
    target = _candidate(_row("target", valid_from="2020-04-20"), 0.45)

    selected, metadata = _finalize(query, [wrong, target], top_k=2)

    assert selected[0] == "target"
    assert selected.index("target") < selected.index("wrong")
    assert metadata["exact_time_cleanup_applied_count"] == 2


def test_exact_valid_time_cleanup_does_not_collapse_comparison_queries() -> None:
    query = "Compare Alpha Corp revenue on 2020-04-20 and 2020-03-28."
    first = _candidate(_row("first", valid_from="2020-03-28"), 0.80)
    second = _candidate(_row("second", valid_from="2020-04-20"), 0.45)

    selected, metadata = _finalize(query, [first, second], top_k=2)

    assert selected == ["first", "second"]
    assert metadata["exact_time_cleanup_applied_count"] == 0
    assert metadata["diversified_selection_applied"] is True


def test_transaction_role_cleanup_prefers_valid_time_when_query_asks_valid_time() -> None:
    query = "What valid-time evidence answers 4 filing for 2017?"
    transaction = _candidate(
        _row(
            "transaction",
            metric="4 filing",
            valid_from=None,
            valid_to=None,
            transaction_time="2024-10-30",
            temporal_type="transaction_time_only",
        ),
        0.80,
    )
    valid = _candidate(_row("valid", metric="4 filing", valid_from="2017-01-01"), 0.40)

    selected, metadata = _finalize(query, [transaction, valid], top_k=2)

    assert selected[0] == "valid"
    assert metadata["transaction_role_cleanup_applied_count"] == 1


def test_transaction_role_cleanup_preserves_transaction_target_queries() -> None:
    query = "What filing was published on 2024-10-30?"
    transaction = _candidate(
        _row(
            "transaction",
            metric="4 filing",
            valid_from=None,
            valid_to=None,
            transaction_time="2024-10-30",
            temporal_type="transaction_time_only",
        ),
        0.80,
    )
    valid = _candidate(_row("valid", metric="4 filing", valid_from="2017-01-01"), 0.40)

    selected, metadata = _finalize(query, [transaction, valid], top_k=2)

    assert selected[0] == "transaction"
    assert metadata["transaction_role_cleanup_applied_count"] == 0


def test_source_adjustment_boosts_named_source_candidate() -> None:
    query = "Use alpha source evidence for revenue in 2020."
    wrong_source = _candidate(_row("wrong_source", source_family="beta_source"), 0.52)
    matching_source = _candidate(_row("matching_source", source_family="alpha_source"), 0.50)

    selected, metadata = _finalize(query, [wrong_source, matching_source], top_k=2)

    assert selected[0] == "matching_source"
    assert metadata["source_metric_adjustment_applied_count"] >= 1


def test_metric_adjustment_boosts_named_metric_candidate() -> None:
    query = "Answer only the metric operating margin."
    wrong_metric = _candidate(_row("wrong_metric", metric="revenue"), 0.52)
    matching_metric = _candidate(_row("matching_metric", metric="operating margin"), 0.50)

    selected, metadata = _finalize(query, [wrong_metric, matching_metric], top_k=2)

    assert selected[0] == "matching_metric"
    assert metadata["source_metric_adjustment_applied_count"] >= 1


def test_diversified_topk_selects_multiple_groups_for_comparison_query() -> None:
    query = "Compare Alpha Corp revenue and Beta Corp revenue in 2020."
    alpha_one = _candidate(_row("alpha_one", entity="Alpha Corp", valid_from="2020-01-01"), 0.90)
    alpha_two = _candidate(_row("alpha_two", entity="Alpha Corp", valid_from="2020-02-01"), 0.85)
    beta_one = _candidate(_row("beta_one", entity="Beta Corp", valid_from="2020-01-01"), 0.80)

    selected, metadata = _finalize(query, [alpha_one, alpha_two, beta_one], top_k=2)

    assert selected == ["alpha_one", "beta_one"]
    assert metadata["diversified_selection_applied"] is True


def test_normal_query_does_not_diversify_score_ordering() -> None:
    query = "What was Alpha Corp revenue?"
    high = _candidate(_row("high", entity="Alpha Corp"), 0.90)
    mid = _candidate(_row("mid", entity="Alpha Corp"), 0.80)
    other = _candidate(_row("other", entity="Beta Corp"), 0.70)

    selected, metadata = _finalize(query, [high, mid, other], top_k=2)

    assert selected == ["high", "mid"]
    assert metadata["diversified_selection_applied"] is False
