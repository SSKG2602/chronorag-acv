from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RankedEvidence:
    evidence_id: str
    rank: int
    score: float


def row_id(row: Any) -> str:
    return str(getattr(row, "id", None) or row["id"])


def candidate_text(row: Any) -> str:
    """Return standard baseline text without temporal metadata enrichment."""
    return str(getattr(row, "raw_text", None) or row.get("raw_text") or "")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class BM25Index:
    """Small deterministic BM25Okapi implementation.

    This avoids requiring rank_bm25 at runtime while keeping the baseline a
    standard BM25 ranker over raw candidate text.
    """

    def __init__(self, documents: Sequence[tuple[str, str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.ids = [doc_id for doc_id, _ in documents]
        self.texts = [text for _, text in documents]
        self.tokens = [tokenize(text) for text in self.texts]
        self.term_freqs = [Counter(tokens) for tokens in self.tokens]
        self.doc_lens = [len(tokens) for tokens in self.tokens]
        self.avgdl = sum(self.doc_lens) / max(1, len(self.doc_lens))
        self.idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        df: Counter[str] = Counter()
        for tokens in self.tokens:
            df.update(set(tokens))
        total_docs = len(self.tokens)
        return {
            term: math.log(1.0 + (total_docs - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def scores(self, query: str, candidate_indexes: Sequence[int] | None = None) -> list[tuple[int, float]]:
        query_terms = tokenize(query)
        indexes = range(len(self.ids)) if candidate_indexes is None else candidate_indexes
        scored: list[tuple[int, float]] = []
        for idx in indexes:
            score = 0.0
            freqs = self.term_freqs[idx]
            doc_len = self.doc_lens[idx]
            norm = self.k1 * (1.0 - self.b + self.b * doc_len / max(self.avgdl, 1e-9))
            for term in query_terms:
                tf = freqs.get(term, 0)
                if not tf:
                    continue
                score += self.idf.get(term, 0.0) * (tf * (self.k1 + 1.0)) / (tf + norm)
            scored.append((idx, score))
        return scored

    def search(
        self,
        query: str,
        top_k: int,
        candidate_indexes: Sequence[int] | None = None,
    ) -> list[RankedEvidence]:
        scored = self.scores(query, candidate_indexes)
        scored.sort(key=lambda item: (-item[1], self.ids[item[0]]))
        return [
            RankedEvidence(evidence_id=self.ids[idx], rank=rank, score=float(score))
            for rank, (idx, score) in enumerate(scored[:top_k], start=1)
        ]


def build_index(corpus: Sequence[Any]) -> BM25Index:
    return BM25Index([(row_id(row), candidate_text(row)) for row in corpus])


def run_bm25_baseline(corpus: Sequence[Any], questions: Sequence[Any], top_k: int = 5) -> dict[str, Any]:
    index = build_index(corpus)
    results = []
    for case in questions:
        ranked = index.search(str(case.question), top_k=top_k)
        results.append(
            {
                "case_id": case.id,
                "question": case.question,
                "selected_evidence_ids": [item.evidence_id for item in ranked],
                "ranked_evidence": [item.__dict__ for item in ranked],
                "metadata": {"ranking": "raw_bm25", "uses_temporal_metadata": False},
            }
        )
    return {
        "method": "bm25",
        "top_k": top_k,
        "candidate_unit": "layer2_evidence_row_raw_text",
        "notes": [
            "Ranks only by BM25 over raw_text.",
            "Does not use TCC, temporal metadata, temporal fusion, or forbidden-time suppression.",
        ],
        "results": results,
    }
