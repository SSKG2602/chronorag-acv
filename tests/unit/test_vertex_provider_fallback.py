from __future__ import annotations

import datetime as dt

from app.utils.chrono_reducer import ChronoPassage
from app.utils.time_windows import TimeWindow
from core.generator.generate import generate_answer


def _passage() -> ChronoPassage:
    window = TimeWindow(
        start=dt.datetime(1870, 1, 1, tzinfo=dt.timezone.utc),
        end=dt.datetime(1871, 1, 1, tzinfo=dt.timezone.utc),
    )
    return ChronoPassage(
        chunk_id="c1",
        doc_id="d1",
        text="Europe GDP per capita in 1870 appears in the world economy source.",
        uri="file:///mnt/data/world_economy.pdf",
        valid_window=window,
        authority=0.9,
        score=0.8,
        facets={},
        entities=["Europe"],
        units=["intl_1990_usd"],
        region="Europe",
    )


def _generate_with_provider(provider: str, monkeypatch) -> str:
    monkeypatch.setenv("CHRONORAG_LIGHT", "0")
    monkeypatch.setenv("CHRONORAG_PROVIDER", provider)
    return generate_answer(
        query="Europe GDP per capita in 1870",
        mode="INTELLIGENT",
        axis="valid",
        window=_passage().valid_window,
        evidence=[_passage()],
        models_cfg={"llm": {"vertex": {"max_output_tokens": 64}}},
        domain="world-economy",
        window_kind="explicit",
    )[0]


def test_unknown_provider_returns_evidence_fallback(monkeypatch) -> None:
    text = _generate_with_provider("unknown-provider", monkeypatch)

    assert "ChronoGuard fallback mode" in text
    assert "Provider debug:" in text
    assert "Unknown CHRONORAG_PROVIDER" in text


def test_vertex_missing_project_returns_evidence_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    text = _generate_with_provider("vertex", monkeypatch)

    assert "ChronoGuard fallback mode" in text
    assert "Provider debug:" in text
    assert "GOOGLE_CLOUD_PROJECT" in text
