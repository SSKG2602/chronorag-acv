from __future__ import annotations

import json

import pytest

from benchmarks.layer2_crossdomain.evaluate_retrieval_only import evaluate_result_file
from benchmarks.layer2_crossdomain.methods.chronorag_full.gsm import retrieve_with_chronorag_gsm
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase
from core.retrieval.vector_ann import resolve_embedding_config
from storage.pvdb.dao import PVDB


def _case(
    question: str,
    category: str = "same_entity_wrong_year_trap",
    domain: str = "macro_fred",
    expected: list[str] | None = None,
    acceptable: list[str] | None = None,
    forbidden: list[str] | None = None,
) -> QuestionCase:
    return QuestionCase(
        id="q1",
        domain=domain,
        question=question,
        category=category,
        expected_behavior="answer",
        expected_evidence_ids=expected or ["target"],
        acceptable_evidence_ids=acceptable or [],
        forbidden_evidence_ids=forbidden or [],
        required_facts=[],
        forbidden_facts=[],
        expected_valid_time=[],
        notes="fixture",
    )


def _row(
    row_id: str,
    *,
    domain: str = "macro_fred",
    entity: str = "United States CPI",
    metric: str = "CPI index",
    value: str = "1.0",
    valid_from: str | None = "2014-01-01",
    temporal_type: str = "valid_time_exact",
    transaction_time: str | None = None,
) -> CorpusRow:
    return CorpusRow(
        id=row_id,
        domain=domain,
        source_family=domain,
        source_file="fixture",
        source_kind="time_series",
        entity=entity,
        related_entities=[],
        metric_or_claim=metric,
        value=value,
        unit="index_points",
        valid_from=valid_from,
        valid_to=valid_from,
        transaction_time=transaction_time,
        temporal_type=temporal_type,
        raw_text=f"{entity} {metric} was {value} on {valid_from or transaction_time}.",
    )


def test_negative_year_evidence_is_banned():
    case = _case("For United States CPI, answer CPI index for 2014, not 2012.", forbidden=["wrong"])
    rows, metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("wrong", valid_from="2012-01-01", value="2.0"),
            _row("target", valid_from="2014-01-01", value="4.0"),
        ],
        top_k=2,
    )
    assert [row.id for row in rows] == ["target"]
    assert "negative_temporal_banned" not in metadata["selected_scores"]
    assert metadata["gsm_enabled"] is True


def test_source_specific_filter_removes_wrong_domain():
    case = _case("Using market_index evidence, what does it say about Dow Jones Industrial Average index close for 2016?", category="source_specific_temporal_query", domain="market_index")
    rows, metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("wrong", domain="macro_fred", entity="Dow Jones Industrial Average", metric="index close", valid_from="2016-01-01"),
            _row("target", domain="market_index", entity="Dow Jones Industrial Average", metric="index close", valid_from="2016-01-01"),
        ],
        top_k=5,
    )
    assert [row.id for row in rows] == ["target"]
    assert metadata["gsm_filters_applied"]


def test_metric_specific_filter_demotes_wrong_metric():
    case = _case("For United States CPI in 2014, answer only the metric CPI index.", category="metric_specific_query")
    rows, _metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("wrong", metric="unemployment rate", valid_from="2014-01-01", value="8.0"),
            _row("target", metric="CPI index", valid_from="2014-01-01", value="4.0"),
        ],
        top_k=1,
    )
    assert rows[0].id == "target"


def test_transaction_time_only_removed_when_valid_time_required():
    case = _case(
        "Apple Inc. has a publication or filing record on 2015-05-19; what valid-time evidence answers 4 filing for 2017?",
        category="transaction_time_vs_valid_time",
        domain="sec_submissions",
    )
    rows, _metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("wrong", domain="sec_submissions", entity="Apple Inc.", metric="UPLOAD filing", valid_from=None, temporal_type="transaction_time_only", transaction_time="2015-05-19"),
            _row("target", domain="sec_submissions", entity="Apple Inc.", metric="4 filing", valid_from="2017-08-07", transaction_time="2017-08-09"),
        ],
        top_k=5,
    )
    assert [row.id for row in rows] == ["target"]


def test_exact_valid_time_query_still_selects_exact_date():
    case = _case("What was United States CPI CPI index on 2014-05-01?", category="exact_valid_time_retrieval")
    rows, metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("wrong", valid_from="2014-01-01", value="1.0"),
            _row("target", valid_from="2014-05-01", value="5.0"),
        ],
        top_k=2,
    )
    assert rows[0].id == "target"
    assert metadata["gsm_enabled"] is False


def test_cross_domain_comparison_returns_both_slots():
    case = _case(
        "Compare United States CPI CPI index in 1947 with Dow Jones Industrial Average index close in 2016.",
        category="cross_domain_temporal_comparison",
        domain="macro_fred",
    )
    rows, metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("cpi", domain="macro_fred", entity="United States CPI", metric="CPI index", valid_from="1947-01-01"),
            _row("djia", domain="market_index", entity="Dow Jones Industrial Average", metric="index close", valid_from="2016-06-21"),
        ],
        top_k=2,
    )
    assert {row.id for row in rows} == {"cpi", "djia"}
    assert metadata["gsm_slots"]


def test_conflict_grouping_does_not_treat_different_dates_as_conflict():
    case = _case("Two sources disagree about United States CPI CPI index for 2014.", category="conflict_detection")
    rows, metadata = retrieve_with_chronorag_gsm(
        case,
        [
            _row("a", valid_from="2014-01-01", value="1.0"),
            _row("b", valid_from="2014-02-01", value="2.0"),
        ],
        top_k=2,
    )
    assert {row.id for row in rows} == {"a", "b"}
    assert metadata["gsm_slots"][0]["conflict_group_found"] is False


def test_ambiguous_time_sets_metadata_policy():
    case = _case("Around the recent period, what was United States CPI CPI index?", category="ambiguous_time_query")
    rows, metadata = retrieve_with_chronorag_gsm(case, [_row("target")], top_k=1)
    assert rows[0].id == "target"
    assert metadata["answer_policy"] == "clarify_or_partial"
    assert metadata["gsm_plan"]["suppress_confident_single_date_answer"] is True


def test_embedding_config_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("CHRONORAG_EMBED_MODEL", raising=False)
    monkeypatch.delenv("CHRONORAG_EMBED_DIM", raising=False)
    assert resolve_embedding_config().model_name == "BAAI/bge-small-en-v1.5"
    assert resolve_embedding_config().dim == 384
    monkeypatch.setenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
    monkeypatch.setenv("CHRONORAG_EMBED_DIM", "768")
    config = resolve_embedding_config()
    assert config.model_name == "BAAI/bge-base-en-v1.5"
    assert config.dim == 768


def test_pvdb_persisted_dimension_mismatch_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRONORAG_EMBED_DIM", "768")
    path = tmp_path / "persisted.json"
    path.write_text(
        json.dumps(
            {
                "embedding": {"model": "BAAI/bge-small-en-v1.5", "dim": 384},
                "documents": [],
                "chunks": [],
                "external_index": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="embedding dimension mismatch"):
        PVDB({"embeddings": {"name": "BAAI/bge-small-en-v1.5", "dim": 384}}, persist_path=path)


def test_embedding_model_and_dim_appear_in_gsm_metadata(monkeypatch):
    monkeypatch.setenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
    monkeypatch.setenv("CHRONORAG_EMBED_DIM", "768")
    case = _case("Around the recent period, what was United States CPI CPI index?", category="ambiguous_time_query")
    _rows, metadata = retrieve_with_chronorag_gsm(case, [_row("target")], top_k=1)
    assert metadata["embedding_model"] == "BAAI/bge-base-en-v1.5"
    assert metadata["embedding_dim"] == 768


def test_retrieval_only_evaluator_counts_hits_and_categories(tmp_path):
    questions = {
        "q1": _case("question", expected=["e1"], forbidden=["bad"]),
        "q2": _case("question", category="metric_specific_query", expected=["e2"], forbidden=[]),
    }
    result_path = tmp_path / "results.json"
    result_path.write_text(
        json.dumps(
            {
                "method": "chronorag_gsm",
                "embedding_model": "BAAI/bge-base-en-v1.5",
                "embedding_dim": 768,
                "results": [
                    {"case_id": "q1", "selected_evidence_ids": ["e1", "bad"]},
                    {"case_id": "q2", "selected_evidence_ids": ["x", "e2"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    report = evaluate_result_file(result_path, questions)
    assert report["metrics"]["hit@1"] == 0.5
    assert report["metrics"]["hit@5"] == 1.0
    assert report["metrics"]["forbidden_evidence_absent@5"] == 0.5
    assert report["category_metrics"]["metric_specific_query"]["hit@5"] == 1.0
