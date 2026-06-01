from __future__ import annotations

from pathlib import Path

import benchmarks.layer2_crossdomain.methods.chronorag_full.finalization as finalization
import benchmarks.layer2_crossdomain.run_layer2_ablations as ablations
from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import (
    AdaptedChronoEvidence,
    ChronoRAGPreparedContext,
    prepare_chronorag_context,
)
from benchmarks.layer2_crossdomain.methods.chronorag_full.finalization import AblationConfig, finalize_chronorag_evidence
from benchmarks.layer2_crossdomain.run_layer2_ablations import (
    DEFAULT_VARIANTS,
    ablation_report_paths,
    parse_variants,
    result_paths,
)
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase
from benchmarks.layer2_crossdomain.temporal_precision import extract_temporal_constraints


def _row(row_id: str, *, raw_text: str | None = None) -> CorpusRow:
    return CorpusRow(
        id=row_id,
        domain="fixture",
        source_family="fixture",
        source_file="fixture.jsonl",
        source_kind="time_series",
        entity="Alpha",
        related_entities=[],
        metric_or_claim="value",
        value="1.0",
        unit="units",
        valid_from="2020-04-20",
        valid_to="2020-04-20",
        transaction_time="2020-04-21T00:00:00",
        temporal_type="valid_time_exact",
        raw_text=raw_text or "Alpha value on 2020-04-20 was 1.0.",
        metadata={"region": "fixture-region"},
    )


def _case(case_id: str = "case") -> QuestionCase:
    return QuestionCase(
        id=case_id,
        domain="fixture",
        question="What was Alpha value on 2020-04-20?",
        category="exact_valid_time_retrieval",
        expected_behavior="answer",
        expected_evidence_ids=["row"],
        acceptable_evidence_ids=[],
        forbidden_evidence_ids=[],
        required_facts=[],
        forbidden_facts=[],
        expected_valid_time=["2020-04-20"],
        notes="",
    )


def _candidate(row_id: str, score: float) -> AdaptedChronoEvidence:
    row = _row(row_id)
    return AdaptedChronoEvidence(
        row=row,
        retrieval_text=row.raw_text,
        temporal_confidence=1.0,
        temporal_source="fixture",
        temporal_metadata={},
        score=score,
    )


def test_ablation_config_defaults_preserve_full_behavior() -> None:
    assert AblationConfig() == AblationConfig(
        disable_tcc=False,
        disable_temporal_precision=False,
        disable_transaction_role=False,
        disable_source_metric=False,
        disable_slot_assembler=False,
        score_only=False,
    )
    assert AblationConfig().effective() == AblationConfig()


def test_score_only_implies_finalization_disables_except_tcc() -> None:
    effective = AblationConfig(score_only=True).effective()
    assert effective.disable_tcc is False
    assert effective.disable_temporal_precision is True
    assert effective.disable_transaction_role is True
    assert effective.disable_source_metric is True
    assert effective.disable_slot_assembler is True
    assert effective.score_only is True

    explicit_no_tcc = AblationConfig(disable_tcc=True, score_only=True).effective()
    assert explicit_no_tcc.disable_tcc is True


def test_prepared_context_not_rebuilt_per_case_in_ablation_runner(monkeypatch) -> None:
    calls: list[bool] = []
    retrieve_calls = 0
    corpus = [_row("row")]

    def fake_prepare_context(rows, *, disable_tcc=False):
        calls.append(disable_tcc)
        return ChronoRAGPreparedContext(corpus=list(rows), adapted_chunks=[], tcc_disabled=disable_tcc)

    def fake_retrieve(case, prepared_context, top_k, ablation_config=None):
        nonlocal retrieve_calls
        retrieve_calls += 1
        return prepared_context.corpus[:top_k], {"method_family": "chronorag_full"}

    monkeypatch.setattr(ablations, "prepare_chronorag_context", fake_prepare_context)
    monkeypatch.setattr(ablations, "retrieve_with_chronorag_prepared", fake_retrieve)

    contexts = ablations.prepare_contexts(["chronorag_full", "chronorag_no_slot_assembler"], corpus)
    for index in range(3):
        rows, _metadata = ablations.select_evidence("chronorag_full", _case(f"case-{index}"), corpus, 1, contexts)
        assert [row.id for row in rows] == ["row"]

    assert calls == [False]
    assert retrieve_calls == 3


def test_disable_slot_assembler_path_does_not_call_assemble_top_k(monkeypatch) -> None:
    called = False

    def fail(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("assemble_top_k should not be called")

    monkeypatch.setattr(finalization, "assemble_top_k", fail)
    selected, metadata = finalize_chronorag_evidence(
        [_candidate("high", 0.9), _candidate("low", 0.4)],
        extract_temporal_constraints("What was Alpha value on 2020-04-20?"),
        "What was Alpha value on 2020-04-20?",
        1,
        ablation_config=AblationConfig(disable_slot_assembler=True),
    )

    assert called is False
    assert [item.row.id for item in selected] == ["high"]
    assert metadata["slot_aware_assembly_applied"] is False


def test_disable_temporal_precision_bypasses_exact_wrong_time_cleanup(monkeypatch) -> None:
    called = False

    def counted(candidates, constraints, query_text):
        nonlocal called
        called = True
        return candidates, 99

    monkeypatch.setattr(finalization, "_apply_exact_valid_time_cleanup", counted)
    _selected, metadata = finalize_chronorag_evidence(
        [_candidate("only", 0.5)],
        extract_temporal_constraints("What was Alpha value on 2020-04-20?"),
        "What was Alpha value on 2020-04-20?",
        1,
        ablation_config=AblationConfig(disable_temporal_precision=True),
    )

    assert called is False
    assert metadata["exact_time_cleanup_applied_count"] == 0


def test_disable_transaction_role_bypasses_transaction_cleanup(monkeypatch) -> None:
    called = False

    def counted(candidates, constraints, query_text):
        nonlocal called
        called = True
        return candidates, 88

    monkeypatch.setattr(finalization, "_apply_transaction_role_cleanup", counted)
    _selected, metadata = finalize_chronorag_evidence(
        [_candidate("only", 0.5)],
        extract_temporal_constraints("What valid-time evidence answers Alpha for 2020?"),
        "What valid-time evidence answers Alpha for 2020?",
        1,
        ablation_config=AblationConfig(disable_transaction_role=True),
    )

    assert called is False
    assert metadata["transaction_role_cleanup_applied_count"] == 0


def test_disable_source_metric_bypasses_source_metric_adjustment(monkeypatch) -> None:
    called = False

    def counted(candidates, query_text):
        nonlocal called
        called = True
        return candidates, 77

    monkeypatch.setattr(finalization, "_apply_source_metric_adjustments", counted)
    _selected, metadata = finalize_chronorag_evidence(
        [_candidate("only", 0.5)],
        extract_temporal_constraints("Use fixture evidence for Alpha on 2020-04-20."),
        "Use fixture evidence for Alpha on 2020-04-20.",
        1,
        ablation_config=AblationConfig(disable_source_metric=True),
    )

    assert called is False
    assert metadata["source_metric_adjustment_applied_count"] == 0


def test_no_tcc_uses_raw_retrieval_text_and_preserves_metadata() -> None:
    row = _row("row", raw_text="Raw fixture text that should be used directly.")
    context = prepare_chronorag_context([row], disable_tcc=True)

    assert context.tcc_disabled is True
    assert len(context.adapted_chunks) == 1
    adapted = context.adapted_chunks[0]
    assert adapted.retrieval_text == row.raw_text
    assert adapted.temporal_source == "row_metadata"
    assert adapted.temporal_metadata["tcc_disabled"] is True
    assert adapted.temporal_metadata["valid_from"] == row.valid_from
    assert adapted.temporal_metadata["valid_to"] == row.valid_to
    assert adapted.temporal_metadata["transaction_time"] == row.transaction_time
    assert adapted.temporal_metadata["temporal_type"] == row.temporal_type
    assert adapted.temporal_metadata["source_family"] == row.source_family


def test_run_layer2_ablations_builds_variant_list_and_output_names() -> None:
    variants = parse_variants(",".join(DEFAULT_VARIANTS))
    assert variants == list(DEFAULT_VARIANTS)

    json_path, md_path = result_paths("chronorag_score_only", "v3_ablation200")
    assert json_path == Path("benchmarks/layer2_crossdomain/results/layer2_chronorag_score_only_v3_ablation200_results.json")
    assert md_path == Path("benchmarks/layer2_crossdomain/results/layer2_chronorag_score_only_v3_ablation200_results.md")

    no_tcc_json, no_tcc_md = result_paths("chronorag_no_tcc", "v3_ablation200")
    assert no_tcc_json == Path("benchmarks/layer2_crossdomain/results/layer2_chronorag_no_tcc_v3_ablation200_results.json")
    assert no_tcc_md == Path("benchmarks/layer2_crossdomain/results/layer2_chronorag_no_tcc_v3_ablation200_results.md")

    report_json, report_md = ablation_report_paths("v3_ablation200")
    assert report_json == Path("benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.json")
    assert report_md == Path("benchmarks/layer2_crossdomain/results/layer2_ablation_v3_ablation200.md")


def test_ablation_helpers_do_not_target_question_or_corpus_outputs() -> None:
    variant_json, variant_md = result_paths("chronorag_full", "check")
    report_json, report_md = ablation_report_paths("check")
    targets = {variant_json.as_posix(), variant_md.as_posix(), report_json.as_posix(), report_md.as_posix()}
    assert "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl" not in targets
    assert "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl" not in targets
