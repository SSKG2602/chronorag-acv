"""Dataclasses representing persistent PVDB documents and chunks."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.utils.time_windows import TimeWindow


@dataclass
class DocumentRecord:
    """Container for document-level metadata."""

    doc_id: str
    source_path: Optional[str]
    text: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "text": self.text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DocumentRecord":
        return cls(
            doc_id=payload["doc_id"],
            source_path=payload.get("source_path"),
            text=payload.get("text", ""),
            metadata=payload.get("metadata", {}),
        )


@dataclass
class ChunkRecord:
    """Chunk-level record including time windows and metadata."""

    chunk_id: str
    doc_id: str
    text: str
    uri: str
    authority: float
    valid_window: TimeWindow
    tx_window: Optional[TimeWindow]
    raw_text: Optional[str] = None
    retrieval_text: Optional[str] = None
    global_context: Dict[str, Any] = field(default_factory=dict)
    temporal_metadata: Dict[str, Any] = field(default_factory=dict)
    external_id: Optional[str] = None
    version_id: Optional[str] = None
    facets: Dict[str, str] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    units: List[str] = field(default_factory=list)
    time_granularity: Optional[str] = None
    time_sigma_days: Optional[int] = None
    embedding: Optional[list] = None
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "raw_text": self.raw_text,
            "retrieval_text": self.retrieval_text,
            "global_context": self.global_context,
            "temporal_metadata": self.temporal_metadata,
            "uri": self.uri,
            "authority": self.authority,
            "valid_window": {
                "start": self.valid_window.start.isoformat(),
                "end": self.valid_window.end.isoformat(),
            },
            "tx_window": (
                {
                    "start": self.tx_window.start.isoformat(),
                    "end": self.tx_window.end.isoformat(),
                }
                if self.tx_window
                else None
            ),
            "external_id": self.external_id,
            "version_id": self.version_id,
            "facets": self.facets,
            "entities": self.entities,
            "tags": self.tags,
            "units": self.units,
            "time_granularity": self.time_granularity,
            "time_sigma_days": self.time_sigma_days,
            "embedding": self.embedding,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ChunkRecord":
        tx_payload = payload.get("tx_window")
        text = payload["text"]
        raw_text = payload.get("raw_text") or text
        retrieval_text = payload.get("retrieval_text") or text
        return cls(
            chunk_id=payload["chunk_id"],
            doc_id=payload["doc_id"],
            text=raw_text,
            uri=payload["uri"],
            authority=payload["authority"],
            valid_window=TimeWindow(
                start=_parse_ts(payload["valid_window"]["start"]),
                end=_parse_ts(payload["valid_window"]["end"]),
            ),
            tx_window=TimeWindow(
                start=_parse_ts(tx_payload["start"]),
                end=_parse_ts(tx_payload["end"]),
            )
            if tx_payload
            else None,
            raw_text=raw_text,
            retrieval_text=retrieval_text,
            global_context=payload.get("global_context", {}),
            temporal_metadata=payload.get("temporal_metadata", {}),
            external_id=payload.get("external_id"),
            version_id=payload.get("version_id"),
            facets=payload.get("facets", {}),
            entities=payload.get("entities", []),
            tags=payload.get("tags", []),
            units=payload.get("units", []),
            time_granularity=payload.get("time_granularity"),
            time_sigma_days=payload.get("time_sigma_days"),
            embedding=payload.get("embedding"),
            extra=payload.get("extra", {}),
        )


def _parse_ts(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)
