from __future__ import annotations

import re
from dataclasses import replace

from benchmarks.layer2_crossdomain.schemas import CorpusRow


def chunk_rows(rows: list[CorpusRow], max_chars: int = 900) -> list[CorpusRow]:
    """Create ordinary raw-text chunks without TCC context enrichment."""
    chunks: list[CorpusRow] = []
    for row in rows:
        if len(row.raw_text) <= max_chars:
            chunks.append(row)
            continue
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", row.raw_text) if part.strip()]
        current: list[str] = []
        current_len = 0
        idx = 0
        for sentence in sentences:
            if current and current_len + len(sentence) > max_chars:
                chunks.append(_chunk(row, idx, " ".join(current)))
                idx += 1
                current = []
                current_len = 0
            current.append(sentence)
            current_len += len(sentence)
        if current:
            chunks.append(_chunk(row, idx, " ".join(current)))
    return chunks


def _chunk(row: CorpusRow, idx: int, text: str) -> CorpusRow:
    return replace(row, id=f"{row.id}:chunk{idx}", raw_text=text)
