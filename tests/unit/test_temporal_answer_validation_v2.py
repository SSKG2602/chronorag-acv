from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.answer_validation_v2 import (
    build_chronorag_grounded_synthesis_prompt,
    build_json_repair_prompt,
    build_tcc_evidence_cards,
    effective_top_k_for_case,
    is_provider_contract_failure,
    load_cases,
    load_corpus,
    normalize_provider_answer_shape,
    parse_model_json,
    retrieve_top_k,
    run_cases,
    validate_evidence_grounding,
    validate_model_schema,
    validate_temporal_rules,
    validate_vertex_prompt_contract,
    validate_answer,
    PromptContractError,
    ProviderJSONParseError,
    SchemaValidationError,
)


CASES = Path("benchmarks/temporal_answer_validation_v2_15.jsonl")
RUNNER = Path("benchmarks/run_temporal_answer_validation_v2.py")
REQUIRED_FIELDS = {
    "id",
    "category",
    "question",
    "expected_behavior",
    "feature_under_test",
    "expected_evidence_ids",
    "acceptable_evidence_ids",
    "distractor_evidence_ids",
    "must_include",
    "must_not_include",
    "readable_expected_answer",
    "validation_notes",
}


def test_answer_validation_case_file_schema_and_ids() -> None:
    assert CASES.exists()
    corpus_ids = {row["id"] for row in load_corpus()}
    cases = load_cases()
    assert len(cases) == 15
    for case in cases:
        assert REQUIRED_FIELDS.issubset(case)
        for field in ["expected_evidence_ids", "acceptable_evidence_ids", "distractor_evidence_ids"]:
            for evidence_id in case[field]:
                assert evidence_id in corpus_ids


def test_tcc_evidence_cards_and_prompt_rules() -> None:
    case = load_cases()[0]
    rows = retrieve_top_k(case["question"], load_corpus(), top_k=5)
    cards = build_tcc_evidence_cards(rows)
    assert cards
    card = cards[0]
    assert "valid_from" in card
    assert "valid_to" in card
    assert "transaction_time" in card
    assert "valid_time=" in card["tcc_context"]
    assert "transaction_time=" in card["tcc_context"]
    assert "raw_evidence=" in card["tcc_context"]
    assert "retrieval_context=" in card["tcc_context"]

    prompt = build_chronorag_grounded_synthesis_prompt(case, cards)
    assert "You are ChronoRAG's grounded temporal answer synthesizer." in prompt
    assert "Use only the provided evidence cards." in prompt
    assert "Do not treat publication year, ingestion time, observation time, or transaction_time as valid_time." in prompt
    assert "Cite only evidence IDs from the provided evidence cards." in prompt
    assert case["question"] in prompt
    assert validate_vertex_prompt_contract(prompt, case, cards)


def test_prompt_contract_failures_and_original_question_preserved() -> None:
    corpus = load_corpus()
    cases = load_cases()
    tx_case = next(item for item in cases if item["id"] == "av2_q03_transaction_time_avoidance")
    tx_cards = build_tcc_evidence_cards(retrieve_top_k(tx_case["question"], corpus, top_k=5))
    tx_prompt = build_chronorag_grounded_synthesis_prompt(tx_case, tx_cards)
    assert "publication year, ingestion time, observation time, or transaction_time" in tx_prompt
    assert tx_case["question"] in tx_prompt
    with pytest.raises(PromptContractError):
        validate_vertex_prompt_contract(tx_prompt.replace("TCC evidence cards:", ""), tx_case, tx_cards)
    with pytest.raises(PromptContractError):
        validate_vertex_prompt_contract(tx_prompt.replace("Required JSON fields:", ""), tx_case, tx_cards)
    with pytest.raises(PromptContractError):
        validate_vertex_prompt_contract(tx_prompt.replace("Prefer exact valid-time evidence", ""), tx_case, tx_cards)
    with pytest.raises(PromptContractError):
        validate_vertex_prompt_contract(tx_prompt.replace("Do not treat publication year", ""), tx_case, tx_cards)


def test_prompt_is_simple_flexible_and_not_case_template_heavy() -> None:
    corpus = load_corpus()
    cases = {case["id"]: case for case in load_cases()}

    q02_prompt = build_chronorag_grounded_synthesis_prompt(
        cases["av2_q02_western_europe_1913_window"],
        build_tcc_evidence_cards(retrieve_top_k(cases["av2_q02_western_europe_1913_window"]["question"], corpus, top_k=5)),
    )
    assert "Return one JSON object with the required fields." in q02_prompt
    assert "one sentence" not in q02_prompt
    assert "supporting valid-time/evidence window" not in q02_prompt

    q05_prompt = build_chronorag_grounded_synthesis_prompt(
        cases["av2_q05_india_metric_confusion"],
        build_tcc_evidence_cards(retrieve_top_k(cases["av2_q05_india_metric_confusion"]["question"], corpus, top_k=5)),
    )
    assert "total GDP is not GDP per capita" not in q05_prompt
    assert cases["av2_q05_india_metric_confusion"]["question"] in q05_prompt

    q06_prompt = build_chronorag_grounded_synthesis_prompt(
        cases["av2_q06_western_europe_compare"],
        build_tcc_evidence_cards(retrieve_top_k(cases["av2_q06_western_europe_compare"]["question"], corpus, top_k=5)),
    )
    assert "separate valid-time windows" not in q06_prompt

    q11_prompt = build_chronorag_grounded_synthesis_prompt(
        cases["av2_q11_western_europe_1820_missing"],
        build_tcc_evidence_cards(retrieve_top_k(cases["av2_q11_western_europe_1820_missing"]["question"], corpus, top_k=5)),
    )
    assert "citations may be empty for true refusal" not in q11_prompt

    q12_prompt = build_chronorag_grounded_synthesis_prompt(
        cases["av2_q12_china_1820_partial"],
        build_tcc_evidence_cards(retrieve_top_k(cases["av2_q12_china_1820_partial"]["question"], corpus, top_k=5)),
    )
    assert "confidence low or medium" not in q12_prompt

    q14_prompt = build_chronorag_grounded_synthesis_prompt(
        cases["av2_q14_ambiguous_industrial_era"],
        build_tcc_evidence_cards(retrieve_top_k(cases["av2_q14_ambiguous_industrial_era"]["question"], corpus, top_k=5)),
    )
    assert "specific year or range" not in q14_prompt


def test_json_parser_contract_variants() -> None:
    raw = '{"answer":"ok","behavior":"answer","cited_evidence_ids":[],"valid_time_used":[],"transaction_time_used_as_valid_time":false,"conflict_warning":false,"partial_or_refusal":false,"clarification_requested":false,"confidence":"high"}'
    assert parse_model_json(raw)["answer"] == "ok"
    assert parse_model_json(f"```json\n{raw}\n```")["behavior"] == "answer"
    assert parse_model_json(f"```\n{raw}\n```")["confidence"] == "high"
    assert parse_model_json(f"Here is the JSON:\n{raw}\nDone.")["answer"] == "ok"
    with_braces = raw.replace('"ok"', '"ok {with braces}"')
    assert parse_model_json(with_braces)["answer"] == "ok {with braces}"
    with_quotes = raw.replace('"ok"', '"ok \\"quoted\\" value"')
    assert parse_model_json(with_quotes)["answer"] == 'ok "quoted" value'
    with pytest.raises(ProviderJSONParseError):
        parse_model_json('{"answer": "truncated"')


def test_schema_grounding_temporal_and_retry_policy() -> None:
    valid = {
        "answer": "ok",
        "behavior": "answer",
        "cited_evidence_ids": [],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }
    assert validate_model_schema(valid)
    with pytest.raises(SchemaValidationError):
        validate_model_schema({key: value for key, value in valid.items() if key != "confidence"})
    invalid_behavior = dict(valid)
    invalid_behavior["behavior"] = "bad"
    with pytest.raises(SchemaValidationError):
        validate_model_schema(invalid_behavior)
    invalid_confidence = dict(valid)
    invalid_confidence["confidence"] = "certain"
    with pytest.raises(SchemaValidationError):
        validate_model_schema(invalid_confidence)

    case = next(item for item in load_cases() if item["id"] == "av2_q04_india_1913_wrong_year")
    cards = build_tcc_evidence_cards(retrieve_top_k(case["question"], load_corpus(), top_k=5))
    good_id = cards[0]["evidence_id"]
    assert not validate_evidence_grounding({"cited_evidence_ids": [good_id]}, cards)["grounding_validation_failure"]
    assert validate_evidence_grounding({"cited_evidence_ids": ["invented:id"]}, cards)["grounding_validation_failure"]

    tx_bad = dict(valid)
    tx_bad["transaction_time_used_as_valid_time"] = True
    assert validate_temporal_rules(case, tx_bad, cards)["temporal_rule_failure"]
    ambiguous_case = next(item for item in load_cases() if item["expected_behavior"] == "clarify")
    assert validate_temporal_rules(ambiguous_case, valid, cards)["temporal_rule_failure"]
    conflict_case = next(item for item in load_cases() if item["expected_behavior"] == "conflict_warning")
    assert validate_temporal_rules(conflict_case, valid, cards)["temporal_rule_failure"]

    assert is_provider_contract_failure({"provider_json_parse_failure": True})
    assert is_provider_contract_failure({"schema_validation_failure": True})
    assert not is_provider_contract_failure({"temporal_rule_failure": True})
    assert "Previous raw response" in build_json_repair_prompt("bad", [good_id])
    assert "one valid JSON object" in build_json_repair_prompt("bad", [good_id])
    assert "from scratch" in build_json_repair_prompt("bad", [good_id])


def test_schema_normalization_for_harmless_provider_shape_drift() -> None:
    raw = {
        "answer": "ok",
        "behavior": "Answer",
        "cited_evidence_ids": "e2:test",
        "valid_time_used": "1913-01-01 to 1913-12-31",
        "transaction_time_used_as_valid_time": "false",
        "conflict_warning": "False",
        "partial_or_refusal": "false",
        "clarification_requested": "false",
        "confidence": "HIGH",
        "extra_field": "ignored by validator",
    }
    normalized, diagnostics = normalize_provider_answer_shape(raw)
    assert diagnostics["schema_normalization_applied"]
    assert normalized["behavior"] == "answer"
    assert normalized["confidence"] == "high"
    assert normalized["cited_evidence_ids"] == ["e2:test"]
    assert normalized["valid_time_used"] == ["1913-01-01 to 1913-12-31"]
    assert normalized["transaction_time_used_as_valid_time"] is False
    assert normalized["conflict_warning"] is False
    assert validate_model_schema(normalized)

    nulls, null_diagnostics = normalize_provider_answer_shape(
        {
            "answer": "ok",
            "behavior": "partial",
            "cited_evidence_ids": None,
            "valid_time_used": None,
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": True,
            "clarification_requested": False,
            "confidence": "low",
        }
    )
    assert null_diagnostics["schema_normalization_applied"]
    assert nulls["cited_evidence_ids"] == []
    assert nulls["valid_time_used"] == []

    inferred, inferred_diagnostics = normalize_provider_answer_shape(
        {
            "answer": "partial answer",
            "behavior": "partial",
            "cited_evidence_ids": [],
            "valid_time_used": [],
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": False,
            "clarification_requested": False,
            "confidence": "medium",
        }
    )
    assert inferred["partial_or_refusal"] is True
    assert "inferred true from behavior=partial" in " ".join(inferred_diagnostics["schema_normalization_notes"])

    refused, refused_diagnostics = normalize_provider_answer_shape(dict(inferred, behavior="refuse", partial_or_refusal=False))
    assert refused["partial_or_refusal"] is True
    assert "inferred true from behavior=refuse" in " ".join(refused_diagnostics["schema_normalization_notes"])

    clarified, clarified_diagnostics = normalize_provider_answer_shape(dict(inferred, behavior="clarify", clarification_requested=False))
    assert clarified["clarification_requested"] is True
    assert "inferred true from behavior=clarify" in " ".join(clarified_diagnostics["schema_normalization_notes"])


def test_vertex_contract_retry_success_is_logged(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}
    case = load_cases()[0]
    corpus = load_corpus()

    def fake_vertex(_prompt: str, *, temperature: float, max_output_tokens: int) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return '{"answer": "truncated"'
        return json.dumps(
            {
                "answer": "Western Europe GDP per capita in 1870 is answered using exact evidence.",
                "behavior": "answer",
                "cited_evidence_ids": ["e2:oecd_pdf:western_europe_exact_1870"],
                "valid_time_used": ["1870-01-01 to 1870-12-31"],
                "transaction_time_used_as_valid_time": False,
                "conflict_warning": False,
                "partial_or_refusal": False,
                "clarification_requested": False,
                "confidence": "high",
            }
        )

    monkeypatch.setattr("benchmarks.answer_validation_v2.run_vertex_grounded_synthesis", fake_vertex)
    result = run_cases([case], corpus, mode="vertex", top_k=5, use_vector=False)
    detail = result["details"][0]
    assert calls["count"] == 2
    assert detail["json_repair_retry_used"]
    assert not detail["provider_json_parse_failure"]
    assert detail["parsed_response_available"]


def test_retry_policy_preserves_usable_initial_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}
    case = next(item for item in load_cases() if item["id"] == "av2_q02_western_europe_1913_window")
    corpus = load_corpus()

    def fake_vertex(_prompt: str, *, temperature: float, max_output_tokens: int) -> str:
        calls["count"] += 1
        return json.dumps(
            {
                "answer": "Western Europe GDP per capita in 1913 was 3,473 in 1990 international dollars.",
                "behavior": "answer",
                "cited_evidence_ids": ["e2:oecd_pdf:western_europe_exact_1913"],
                "valid_time_used": "1913-01-01 to 1913-12-31",
                "transaction_time_used_as_valid_time": "false",
                "conflict_warning": False,
                "partial_or_refusal": False,
                "clarification_requested": False,
                "confidence": "HIGH",
            }
        )

    monkeypatch.setattr("benchmarks.answer_validation_v2.run_vertex_grounded_synthesis", fake_vertex)
    result = run_cases([case], corpus, mode="vertex", top_k=5, use_vector=False)
    detail = result["details"][0]
    assert calls["count"] == 1
    assert not detail["retry_attempted"]
    assert detail["schema_normalization_applied"]
    assert detail["answer"]["valid_time_used"] == ["1913-01-01 to 1913-12-31"]


def test_answer_validation_failure_does_not_trigger_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}
    case = next(item for item in load_cases() if item["id"] == "av2_q05_india_metric_confusion")
    corpus = load_corpus()

    def fake_vertex(_prompt: str, *, temperature: float, max_output_tokens: int) -> str:
        calls["count"] += 1
        return json.dumps(
            {
                "answer": "India has GDP evidence.",
                "behavior": "answer",
                "cited_evidence_ids": ["e2:maddison:country:gdp_pc:india:1870"],
                "valid_time_used": ["1870-01-01 to 1870-12-31"],
                "transaction_time_used_as_valid_time": False,
                "conflict_warning": False,
                "partial_or_refusal": False,
                "clarification_requested": False,
                "confidence": "high",
            }
        )

    monkeypatch.setattr("benchmarks.answer_validation_v2.run_vertex_grounded_synthesis", fake_vertex)
    result = run_cases([case], corpus, mode="vertex", top_k=5, use_vector=False)
    detail = result["details"][0]
    assert calls["count"] == 1
    assert not detail["retry_attempted"]
    assert detail["failure_type"] == "Answer Validation Failure"


def test_failed_retry_does_not_overwrite_parsed_initial_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}
    case = load_cases()[0]
    corpus = load_corpus()

    def fake_vertex(_prompt: str, *, temperature: float, max_output_tokens: int) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps({"answer": "parsed but missing required fields"})
        return '{"answer": "still broken"'

    monkeypatch.setattr("benchmarks.answer_validation_v2.run_vertex_grounded_synthesis", fake_vertex)
    result = run_cases([case], corpus, mode="vertex", top_k=5, use_vector=False)
    detail = result["details"][0]
    assert calls["count"] == 2
    assert detail["retry_attempted"]
    assert detail["fallback_to_initial_response"]
    assert detail["answer"]["answer"] == "parsed but missing required fields"
    assert detail["schema_validation_failure"]


def test_behavior_aware_validation_for_vertex_failure_cases() -> None:
    corpus = load_corpus()
    cases = {case["id"]: case for case in load_cases()}

    q02 = cases["av2_q02_western_europe_1913_window"]
    q02_cards = build_tcc_evidence_cards(retrieve_top_k(q02["question"], corpus, top_k=5))
    q02_without_window = {
        "answer": "Western Europe GDP per capita in 1913 was 3,473 in 1990 international dollars.",
        "behavior": "answer",
        "cited_evidence_ids": ["e2:oecd_pdf:western_europe_exact_1913"],
        "valid_time_used": ["1913-01-01 to 1913-12-31"],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }
    assert validate_answer(q02, q02_without_window, q02_cards)["required_facts_present"]
    q02_wrong_value = dict(q02_without_window)
    q02_wrong_value["answer"] = "Western Europe GDP per capita in 1913 was 999 in 1990 international dollars."
    assert not validate_answer(q02, q02_wrong_value, q02_cards)["required_facts_present"]
    q02_with_window = dict(q02_without_window)
    q02_with_window["answer"] = (
        "Western Europe GDP per capita in 1913 was 3,473 in 1990 international dollars, "
        "supported by the valid-time window 1913-01-01 to 1913-12-31."
    )
    assert validate_answer(q02, q02_with_window, q02_cards)["required_facts_present"]

    q05 = cases["av2_q05_india_metric_confusion"]
    q05_cards = build_tcc_evidence_cards(retrieve_top_k(q05["question"], corpus, top_k=5))
    metric_answer = {
        "answer": "No. Total GDP is not GDP per capita; use GDP per capita evidence for GDP per capita questions.",
        "behavior": "prefer_exact",
        "cited_evidence_ids": ["e2:maddison:country:gdp_pc:india:1870"],
        "valid_time_used": ["1870-01-01 to 1870-12-31"],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }
    assert validate_answer(q05, metric_answer, q05_cards)["required_facts_present"]

    q06 = cases["av2_q06_western_europe_compare"]
    q06_cards = build_tcc_evidence_cards(retrieve_top_k(q06["question"], corpus, top_k=5))
    compare_answer = {
        "answer": "Western Europe rose from 1,960 in 1870 to 3,473 in 1913, each supported by separate exact-year evidence.",
        "behavior": "compare",
        "cited_evidence_ids": ["e2:oecd_pdf:western_europe_exact_1870", "e2:oecd_pdf:western_europe_exact_1913"],
        "valid_time_used": ["1870-01-01 to 1870-12-31", "1913-01-01 to 1913-12-31"],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }
    assert validate_answer(q06, compare_answer, q06_cards)["required_facts_present"]

    q11 = cases["av2_q11_western_europe_1820_missing"]
    q11_cards = build_tcc_evidence_cards(retrieve_top_k(q11["question"], corpus, top_k=5))
    refusal = {
        "answer": "No exact evidence is available, so the system should not answer confidently.",
        "behavior": "refuse",
        "cited_evidence_ids": [],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": True,
        "clarification_requested": False,
        "confidence": "low",
    }
    refusal_checks = validate_answer(q11, refusal, q11_cards)
    assert refusal_checks["required_facts_present"]
    assert refusal_checks["acceptable_evidence_cited"]
    refusal_no_exact_phrase = dict(refusal)
    refusal_no_exact_phrase["answer"] = (
        "I cannot provide the GDP per capita for Western Europe in 1820 because there is no evidence "
        "available for that specific year, so it cannot be answered confidently."
    )
    assert validate_answer(q11, refusal_no_exact_phrase, q11_cards)["required_facts_present"]

    q12 = cases["av2_q12_china_1820_partial"]
    q12_cards = build_tcc_evidence_cards(retrieve_top_k(q12["question"], corpus, top_k=5))
    partial = {
        "answer": "Only background evidence is available for China in 1820; no exact GDP per capita value is available, so this is partial.",
        "behavior": "partial",
        "cited_evidence_ids": ["e2:oecd_pdf:china_background_1820"],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": True,
        "clarification_requested": False,
        "confidence": "medium",
    }
    assert validate_answer(q12, partial, q12_cards)["required_facts_present"]

    q13 = cases["av2_q13_transaction_time_only_records"]
    q13_cards = build_tcc_evidence_cards(retrieve_top_k(q13["question"], corpus, top_k=5))
    tx_only_partial = {
        "answer": "Transaction-time-only records should not be counted as valid-time evidence for historical GDP claims.",
        "behavior": "partial",
        "cited_evidence_ids": q13["expected_evidence_ids"],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": True,
        "clarification_requested": False,
        "confidence": "high",
    }
    q13_checks = validate_answer(q13, tx_only_partial, q13_cards)
    assert q13_checks["required_facts_present"]
    assert q13_checks["confidence_correct"]
    q13_missing_flag = dict(tx_only_partial)
    q13_missing_flag["partial_or_refusal"] = False
    q13_missing_flag_checks = validate_answer(q13, q13_missing_flag, q13_cards)
    assert q13_missing_flag_checks["partial_refusal_correct"]

    q14 = cases["av2_q14_ambiguous_industrial_era"]
    q14_cards = build_tcc_evidence_cards(retrieve_top_k(q14["question"], corpus, top_k=5))
    clarify = {
        "answer": "The temporal target is ambiguous; please provide a more specific year or range.",
        "behavior": "clarify",
        "cited_evidence_ids": ["e2:synthetic:western_europe_industrial_ambiguous"],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": True,
        "confidence": "low",
    }
    assert validate_answer(q14, clarify, q14_cards)["required_facts_present"]

    q08 = cases["av2_q08_broad_trend_no_exact_value"]
    q08_cards = build_tcc_evidence_cards(retrieve_top_k(q08["question"], corpus, top_k=5))
    exact_value_only = {
        "answer": "Western Europe GDP per capita in 1870 was 1,960 in 1990 international dollars.",
        "behavior": "answer",
        "cited_evidence_ids": ["e2:oecd_pdf:western_europe_exact_1870"],
        "valid_time_used": ["1870-01-01 to 1870-12-31"],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }
    assert not validate_answer(q08, exact_value_only, q08_cards)["required_facts_present"]


def test_q15_uses_source_family_policy_card_honestly() -> None:
    case = next(item for item in load_cases() if item["id"] == "av2_q15_source_family_grounding")
    cards = build_tcc_evidence_cards(retrieve_top_k(case["question"], load_corpus(), top_k=5))
    ids = [card["evidence_id"] for card in cards]
    assert "e2:synthetic:source_family_grounding_policy" in ids
    answer = {
        "answer": "Cite evidence IDs and source family names for OWID and Maddison separately; avoid unsupported value mixing.",
        "behavior": "answer",
        "cited_evidence_ids": ["e2:synthetic:source_family_grounding_policy"],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high",
    }
    assert validate_answer(case, answer, cards)["overall_pass"]


def test_light_runner_writes_results(tmp_path: Path) -> None:
    out_json = tmp_path / "light.json"
    out_md = tmp_path / "light.md"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "light",
            "--top-k",
            "5",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        check=True,
    )
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["mode"] == "light"
    assert payload["case_count"] == 15
    assert len(payload["details"]) == 15
    assert "Temporal Answer Validation v2 Results" in out_md.read_text(encoding="utf-8")


def test_dry_run_and_estimate_only(tmp_path: Path) -> None:
    out_json = tmp_path / "dry.json"
    out_md = tmp_path / "dry.md"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "light",
            "--dry-run-prompts",
            "--limit",
            "2",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        check=True,
    )
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["prompt_count"] == 2
    assert "TCC evidence cards" in out_md.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "light", "--estimate-only"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Selected cases: 15" in result.stdout
    assert "Estimated Vertex calls: 0" in result.stdout


def test_dynamic_top_k_keeps_default_and_expands_only_complex_cases() -> None:
    cases = {case["id"]: case for case in load_cases()}
    simple = cases["av2_q01_western_europe_1870_exact"]
    complex_case = cases["av2_q06_western_europe_compare"]
    assert effective_top_k_for_case(simple, 5, False) == 5
    assert effective_top_k_for_case(simple, 5, True) == 5
    assert effective_top_k_for_case(complex_case, 5, False) == 5
    assert effective_top_k_for_case(complex_case, 5, True) == 7
    assert effective_top_k_for_case(complex_case, 8, True) == 8
    assert effective_top_k_for_case(complex_case, 12, True) == 10


def test_result_suffix_outputs_and_sanitization(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "light",
            "--top-k",
            "5",
            "--limit",
            "1",
            "--result-suffix",
            "unit_suffix",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    out_json = Path("benchmarks/results/temporal_answer_validation_v2_light_unit_suffix_results.json")
    out_md = Path("benchmarks/results/temporal_answer_validation_v2_light_unit_suffix_results.md")
    assert out_json.exists()
    assert out_md.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["result_suffix"] == "unit_suffix"
    assert "Result suffix: unit_suffix" in out_md.read_text(encoding="utf-8")
    assert "temporal_answer_validation_v2_light_results.json" not in result.stdout
    out_json.unlink(missing_ok=True)
    out_md.unlink(missing_ok=True)

    bad = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "light", "--result-suffix", "../bad"],
        text=True,
        capture_output=True,
    )
    assert bad.returncode != 0
    assert "result-suffix" in bad.stderr or "result-suffix" in bad.stdout


def test_vertex_mode_without_env_fails_clearly() -> None:
    env = dict(os.environ)
    env.pop("GOOGLE_CLOUD_PROJECT", None)
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "vertex", "--limit", "1"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "Vertex mode requested" in result.stderr or "Vertex mode requested" in result.stdout


def test_validator_detects_answer_failures() -> None:
    case = next(item for item in load_cases() if item["id"] == "av2_q03_transaction_time_avoidance")
    cards = build_tcc_evidence_cards(retrieve_top_k(case["question"], load_corpus(), top_k=5))
    bad = {
        "answer": "2006 is the valid time. GDP valid year 2006.",
        "behavior": "answer",
        "cited_evidence_ids": [],
        "valid_time_used": ["2006"],
        "transaction_time_used_as_valid_time": True,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
    }
    result = validate_answer(case, bad, cards)
    assert not result["transaction_time_not_misused"]
    assert not result["forbidden_facts_absent"]
    assert not result["expected_evidence_cited"]

    conflict_case = next(item for item in load_cases() if item["expected_behavior"] == "conflict_warning")
    conflict_result = validate_answer(
        conflict_case,
        {
            "answer": "Western Europe 1913 answer without conflict.",
            "behavior": "answer",
            "cited_evidence_ids": conflict_case["expected_evidence_ids"],
            "valid_time_used": ["1913-01-01 to 1913-12-31"],
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": False,
            "clarification_requested": False,
        },
        cards,
    )
    assert not conflict_result["conflict_warning_correct"]

    partial_case = next(item for item in load_cases() if item["expected_behavior"] == "partial")
    partial_result = validate_answer(
        partial_case,
        {
            "answer": "confident exact China answer",
            "behavior": "answer",
            "cited_evidence_ids": partial_case["acceptable_evidence_ids"],
            "valid_time_used": [],
            "transaction_time_used_as_valid_time": False,
            "conflict_warning": False,
            "partial_or_refusal": False,
            "clarification_requested": False,
        },
        cards,
    )
    assert not partial_result["partial_refusal_correct"]
