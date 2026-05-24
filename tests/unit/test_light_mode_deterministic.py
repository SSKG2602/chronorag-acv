from __future__ import annotations

import datetime as dt
import sys

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
        text="Europe per capita GDP in 1870 is reported in 1990 international dollars.",
        uri="file:///mnt/data/world_economy.pdf",
        valid_window=window,
        authority=0.9,
        score=0.8,
        facets={},
        entities=["Europe"],
        units=["intl_1990_usd"],
        region="Europe",
    )


def test_light_mode_ignores_vertex_provider_and_sdk(monkeypatch) -> None:
    monkeypatch.setenv("CHRONORAG_LIGHT", "1")
    monkeypatch.setenv("CHRONORAG_PROVIDER", "vertex")
    sys.modules.pop("vertexai", None)

    text, tokens = generate_answer(
        query="Europe GDP per capita in 1870",
        mode="INTELLIGENT",
        axis="valid",
        window=_passage().valid_window,
        evidence=[_passage()],
        models_cfg={"llm": {}},
        domain="world-economy",
        window_kind="explicit",
    )

    assert "ChronoGuard fallback mode" in text
    assert "Provider debug:" not in text
    assert tokens > 0
    assert "vertexai" not in sys.modules
