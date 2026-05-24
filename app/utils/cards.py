"""Utilities for formatting attribution cards returned to clients."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.utils.chrono_reducer import ChronoPassage
from app.utils.time_windows import TimeWindow


def window_to_payload(window: TimeWindow) -> Dict[str, str]:
    """Serialise a TimeWindow for API payloads."""
    return {
        "from": window.start.isoformat(),
        "to": window.end.isoformat(),
    }


def build_sources(passages: Iterable[ChronoPassage]) -> List[Dict]:
    """Convert ChronoPassage objects into source entries for attribution cards."""
    sources = []
    for passage in passages:
        sources.append(
            {
                "uri": passage.uri,
                "quote": passage.text[:280],
                "interval": window_to_payload(passage.valid_window),
                "score": round(passage.score, 4),
                "temporal_source": (passage.temporal_metadata or {}).get("temporal_source"),
                "temporal_confidence": (passage.temporal_metadata or {}).get("temporal_confidence"),
                "temporal_ambiguity": (passage.temporal_metadata or {}).get("temporal_ambiguity"),
            }
        )
    return sources


def build_attribution_card(
    passages: Iterable[ChronoPassage],
    mode: str,
    axis: str,
    window: TimeWindow,
    confidence: Dict,
    counterfactuals: Optional[List[str]] = None,
) -> Dict:
    """Build the complete attribution card structure consumed by clients."""
    counterfactuals = counterfactuals or []
    return {
        "mode": mode,
        "time_axis": axis,
        "window": window_to_payload(window),
        "sources": build_sources(passages),
        "temporal_confidence": confidence,
        "counterfactuals": counterfactuals,
    }
