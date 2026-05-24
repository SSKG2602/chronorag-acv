"""Utilities for reducing and comparing chronological passages.

Answer generation receives many overlapping snippets for each fact.  These helpers
deduplicate passages, detect temporal conflicts, and build short timeline snippets
used in audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from app.utils.time_windows import TimeWindow, window_iou


@dataclass
class ChronoPassage:
    """Wrapper holding passage text plus metadata needed for chronological checks."""

    chunk_id: str
    doc_id: str
    text: str
    uri: str
    valid_window: TimeWindow
    authority: float
    score: float
    facets: Dict[str, str]
    entities: List[str]
    units: List[str]
    region: Optional[str] = None
    global_context: Optional[Dict] = None
    temporal_metadata: Optional[Dict] = None


def reduce_passages(passages: Iterable[ChronoPassage]) -> List[ChronoPassage]:
    """Merge passages chronologically, preferring higher-authority/high-score entries."""
    bucket = {}
    for passage in passages:
        key = (passage.text.strip().lower(), passage.valid_window.start)
        current = bucket.get(key)
        if current is None or passage.authority > current.authority or passage.score > current.score:
            bucket[key] = passage
    ordered = sorted(bucket.values(), key=lambda p: (-p.score, p.valid_window.start, -p.authority))
    return ordered


@dataclass
class ChronoConflict:
    """Represents two passages whose windows overlap beyond a threshold."""

    first: ChronoPassage
    second: ChronoPassage
    overlap: float


def detect_conflicts(passages: List[ChronoPassage], threshold: float = 0.6) -> List[ChronoConflict]:
    """Return overlapping passage pairs whose IoU meets or exceeds the threshold."""
    conflicts: List[ChronoConflict] = []
    for idx, first in enumerate(passages):
        for second in passages[idx + 1 :]:
            overlap = window_iou(first.valid_window, second.valid_window)
            if overlap >= threshold:
                conflicts.append(ChronoConflict(first=first, second=second, overlap=overlap))
    return conflicts


def build_dual_timelines(passages: List[ChronoPassage]) -> List[Tuple[str, str]]:
    """Produce short (timestamp, text) tuples used to explain conflicting evidence."""
    timelines: List[Tuple[str, str]] = []
    for passage in passages:
        label = passage.valid_window.start.date().isoformat()
        timelines.append((label, passage.text[:140]))
    return timelines
