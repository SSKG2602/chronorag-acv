from __future__ import annotations

from benchmarks.layer2_crossdomain.methods.chronorag_full.gsm import GSMQueryMode, analyze_gsm_plan


def test_exact_date_query_keeps_gsm_disabled():
    plan = analyze_gsm_plan("What was United States CPI CPI index on 1947-01-01?")
    assert plan.enabled is False
    assert plan.query_mode == GSMQueryMode.EXACT_VALID_TIME


def test_wrong_year_trap_extracts_positive_and_negative_years():
    plan = analyze_gsm_plan("For United States unemployment rate, answer unemployment rate for 2014, not 2012.")
    assert plan.enabled is True
    assert plan.query_mode == GSMQueryMode.SAME_ENTITY_WRONG_YEAR_TRAP
    assert plan.positive_temporal_constraints == ["2014"]
    assert plan.negative_temporal_constraints == ["2012"]


def test_transaction_time_vs_valid_time_requires_valid_time():
    plan = analyze_gsm_plan("Published in 2006 but contains data about 1870. What valid-time evidence answers GDP for 1870?")
    assert plan.query_mode == GSMQueryMode.TRANSACTION_TIME_VS_VALID_TIME
    assert plan.valid_time_required is True
    assert plan.transaction_time_allowed is False


def test_source_specific_domain_detected():
    plan = analyze_gsm_plan("Using market_index evidence, what does it say about S&P 500 index close for 2022?")
    assert plan.query_mode == GSMQueryMode.SOURCE_SPECIFIC
    assert plan.required_domain == "market_index"
    assert plan.needs_source_filter is True


def test_metric_specific_terms_detected():
    plan = analyze_gsm_plan("For Dow Jones Industrial Average in 2016, answer only the metric index close.")
    assert plan.query_mode == GSMQueryMode.METRIC_SPECIFIC
    assert "index" in plan.required_metric_terms
    assert "close" in plan.required_metric_terms


def test_conflict_detection_sets_grouping():
    plan = analyze_gsm_plan("Two sources disagree about United States CPI CPI index for 1947.")
    assert plan.query_mode == GSMQueryMode.CONFLICT_DETECTION
    assert plan.needs_conflict_grouping is True


def test_missing_exact_evidence_sets_partial_policy():
    plan = analyze_gsm_plan("What was CPI in 1900? If exact evidence is missing, do not answer confidently.")
    assert plan.query_mode == GSMQueryMode.PARTIAL_OR_INSUFFICIENT
    assert plan.requires_exact_evidence is True
    assert plan.answer_policy == "partial_or_refuse_if_exact_missing"


def test_ambiguous_time_suppresses_confident_single_date_answer():
    plan = analyze_gsm_plan("Around the recent period, what was kubernetes release v1.30.6?")
    assert plan.query_mode == GSMQueryMode.AMBIGUOUS_TIME
    assert plan.ambiguous_time is True
    assert plan.suppress_confident_single_date_answer is True


def test_comparison_query_uses_slots():
    plan = analyze_gsm_plan("Compare United States CPI CPI index in 1947 with Dow Jones Industrial Average index close in 2016.")
    assert plan.query_mode == GSMQueryMode.CROSS_DOMAIN_COMPARISON
    assert plan.needs_cross_domain_slots is True
    assert len(plan.slots) == 2
    assert plan.slots[0].positive_temporal_constraints == ["1947"]
    assert plan.slots[1].positive_temporal_constraints == ["2016"]
