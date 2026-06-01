from __future__ import annotations

import json
from dataclasses import dataclass

from benchmarks.layer2_crossdomain.methods.chronorag_full.slot_assembler import (
    assemble_top_k,
    audit_conflict_data_contract,
    classify_query_intent,
)


@dataclass(frozen=True)
class Candidate:
    row: dict
    score: float


def _candidate(
    evidence_id: str,
    score: float,
    *,
    entity: str = "Alpha",
    source_family: str = "macro_fred",
    metric: str = "yield",
    valid_from: str | None = "1962-08-15",
    valid_to: str | None = None,
    transaction_time: str | None = None,
    temporal_type: str = "valid_time_exact",
    value: str = "1.0",
    text: str | None = None,
) -> Candidate:
    row = {
        "id": evidence_id,
        "domain": source_family,
        "source_family": source_family,
        "source_file": f"{source_family}.jsonl",
        "source_kind": "time_series",
        "entity": entity,
        "metric_or_claim": metric,
        "value": value,
        "unit": "units",
        "valid_from": valid_from,
        "valid_to": valid_to or valid_from,
        "transaction_time": transaction_time,
        "temporal_type": temporal_type,
        "raw_text": text or f"{entity} {metric} was {value} on {valid_from or transaction_time}.",
    }
    return Candidate(row=row, score=score)


def _assemble(query: str, candidates: list[Candidate], top_k: int = 5) -> tuple[list[str], dict]:
    intent = classify_query_intent(query, candidates=candidates)
    selected, report = assemble_top_k(candidates, intent, top_k)
    return [item.row["id"] for item in selected], report


def test_exact_target_date_beats_higher_scored_same_year_wrong_date() -> None:
    query = "What was Alpha yield on 1962-08-15?"
    wrong = _candidate("wrong", 100.0, valid_from="1962-01-18")
    target = _candidate("target", 10.0, valid_from="1962-08-15")

    selected, report = _assemble(query, [wrong, target], top_k=2)

    assert "target" in selected
    assert selected.index("target") == 0
    assert "wrong" in report["suppressed_evidence_ids"]


def test_broad_evidence_demoted_only_when_exact_exists() -> None:
    query = "What was Alpha yield on 1962-08-15?"
    broad = _candidate("broad", 100.0, valid_from="1962-01-01", valid_to="1962-12-31", temporal_type="valid_time_range")
    exact = _candidate("exact", 10.0, valid_from="1962-08-15")

    selected_with_exact, report = _assemble(query, [broad, exact], top_k=2)
    selected_without_exact, _ = _assemble(query, [broad], top_k=2)

    assert selected_with_exact[0] == "exact"
    assert "broad" in report["suppressed_evidence_ids"]
    assert selected_without_exact == ["broad"]


def test_transaction_time_demotion_triggers_valid_time_replacement() -> None:
    query = "What valid-time evidence answers 4 filing for 2017?"
    transaction = _candidate(
        "transaction",
        100.0,
        metric="4 filing",
        valid_from=None,
        valid_to=None,
        transaction_time="2024-10-30",
        temporal_type="transaction_time_only",
    )
    valid = _candidate("valid", 10.0, metric="4 filing", valid_from="2017-08-07")
    clean = _candidate("clean", 9.0, metric="4 filing", valid_from="2017-09-01")

    selected, report = _assemble(query, [transaction, valid, clean], top_k=2)

    assert "valid" in selected
    assert "transaction" not in selected
    assert "transaction" in report["suppressed_evidence_ids"]


def test_comparison_query_reserves_both_sides() -> None:
    query = "Compare CPI 1947 with DJIA 2016."
    cpi_wrong_year = _candidate("cpi_2016", 100.0, entity="United States CPI", metric="CPI index", valid_from="2016-01-01")
    cpi_target = _candidate("cpi_1947", 10.0, entity="United States CPI", metric="CPI index", valid_from="1947-01-01")
    djia_target = _candidate("djia_2016", 90.0, entity="DJIA", source_family="market_index", metric="index close", valid_from="2016-06-21")

    selected, report = _assemble(query, [cpi_wrong_year, cpi_target, djia_target], top_k=2)

    assert "cpi_1947" in selected
    assert "djia_2016" in selected
    assert "comparison_slot_0" in report["slot_filled"]
    assert "comparison_slot_1" in report["slot_filled"]


def test_source_specific_lookup_keeps_source_match_and_exact_date() -> None:
    query = "Using macro_fred evidence, what was Alpha yield on 1962-08-15?"
    wrong = _candidate("wrong", 100.0, source_family="macro_fred", valid_from="1962-01-18")
    exact = _candidate("exact", 10.0, source_family="macro_fred", valid_from="1962-08-15")
    other_source = _candidate("other_source", 90.0, source_family="market_index", valid_from="1962-08-15")

    selected, report = _assemble(query, [wrong, exact, other_source], top_k=2)

    assert selected[0] == "exact"
    assert "wrong" in report["suppressed_evidence_ids"]
    assert "other_source" in report["suppressed_evidence_ids"]


def test_metric_version_query_suppresses_sibling_versions() -> None:
    query = "For Kubernetes, answer release v1.30.6."
    sibling = _candidate(
        "sibling",
        100.0,
        entity="Kubernetes",
        source_family="github_releases",
        metric="release v1.31.2",
        valid_from="2024-11-01",
        text="Kubernetes release v1.31.2.",
    )
    exact = _candidate(
        "exact",
        10.0,
        entity="Kubernetes",
        source_family="github_releases",
        metric="release v1.30.6",
        valid_from="2024-10-23",
        text="Kubernetes release v1.30.6.",
    )
    clean = _candidate("clean", 9.0, entity="Kubernetes", source_family="github_releases", metric="release notes", valid_from="2024-10-24")

    selected, report = _assemble(query, [sibling, exact, clean], top_k=2)

    assert "exact" in selected
    assert "sibling" not in selected
    assert "sibling" in report["suppressed_evidence_ids"]


def test_conflict_acceptable_id_absence_is_reported_as_data_contract_issue(tmp_path) -> None:
    questions_path = tmp_path / "questions.jsonl"
    corpus_path = tmp_path / "corpus.jsonl"
    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"
    questions_path.write_text(
        json.dumps(
            {
                "id": "q1",
                "category": "conflict_detection",
                "question": "Two sources disagree about Alpha.",
                "expected_evidence_ids": ["real"],
                "acceptable_evidence_ids": ["synthetic:conflict:real"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    corpus_path.write_text(json.dumps({"id": "real"}) + "\n", encoding="utf-8")

    payload = audit_conflict_data_contract(questions_path, corpus_path, output_json, output_md)

    assert payload["missing_id_count"] == 1
    assert payload["cases"][0]["missing_ids"] == ["synthetic:conflict:real"]
    assert "synthetic:conflict:real" in output_md.read_text(encoding="utf-8")


def test_forbidden_like_rows_are_not_forced_when_clean_candidates_exist() -> None:
    query = "What valid-time evidence answers Alpha filing for 2017?"
    transaction = _candidate(
        "transaction",
        100.0,
        metric="filing",
        valid_from=None,
        valid_to=None,
        transaction_time="2024-10-30",
        temporal_type="transaction_time_only",
    )
    valid = _candidate("valid", 10.0, metric="filing", valid_from="2017-01-01")
    clean = _candidate("clean", 9.0, metric="filing", valid_from="2017-02-01")

    selected, _report = _assemble(query, [transaction, valid, clean], top_k=2)

    assert selected == ["valid", "clean"]
