"""Lightweight ANN index used for local retrieval experiments and tests."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np

from app.light_mode import light_mode_enabled

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingConfig:
    model_name: str
    dim: int


def resolve_embedding_config(model_name: str | None = None, dim: int | str | None = None) -> EmbeddingConfig:
    """Resolve embedding model/dim from explicit config with env overrides."""
    resolved_name = os.getenv("CHRONORAG_EMBED_MODEL") or model_name or "BAAI/bge-small-en-v1.5"
    raw_dim = os.getenv("CHRONORAG_EMBED_DIM") or dim or 384
    try:
        resolved_dim = int(raw_dim)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid CHRONORAG_EMBED_DIM value: {raw_dim!r}") from exc
    return EmbeddingConfig(model_name=resolved_name, dim=resolved_dim)


def _hash_embedding(text: str, dim: int) -> np.ndarray:
    """Return a deterministic pseudo-embedding for light-mode/integration tests."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big", signed=False)
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=dim)
    norm = np.linalg.norm(vec) or 1.0
    return (vec / norm).astype(np.float32)


class EmbeddingEncoder:
    def __init__(self, name: str = "BAAI/bge-small-en-v1.5", dim: int = 384):
        config = resolve_embedding_config(name, dim)
        self.name = config.model_name
        self.dim = config.dim
        self._model = None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if light_mode_enabled():
            self._model = "_stub_"
            return
        from sentence_transformers import SentenceTransformer  # noqa: WPS433

        self._model = SentenceTransformer(self.name)
        if os.getenv("CHRONORAG_EMBED_FP16", "").strip().lower() in ("1", "true", "yes"):
            try:
                self._model.half()
            except Exception as exc:  # pragma: no cover - depends on local model backend
                logger.warning("CHRONORAG_EMBED_FP16 requested but half precision failed: %s", exc)

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode text strings into L2-normalised vectors."""
        self._ensure_model()
        if self._model == "_stub_":
            vectors = [_hash_embedding(text, self.dim) for text in texts]
            return np.stack(vectors, axis=0)
        vectors = np.asarray(
            self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(
                f"Embedding dimension mismatch for {self.name}: expected {self.dim}, got {vectors.shape[1] if vectors.ndim == 2 else 'unknown'}."
            )
        return vectors


@dataclass
class ANNEntry:
    chunk_id: str
    text: str
    vector: np.ndarray
    metadata: Dict


class InMemoryANNIndex:
    def __init__(self, model_name: str, dim: int = 384):
        self.encoder = EmbeddingEncoder(model_name, dim=dim)
        self.model_name = self.encoder.name
        self.dim = self.encoder.dim
        self.entries: Dict[str, ANNEntry] = {}

    def add(self, chunk_id: str, text: str, metadata: Dict) -> np.ndarray:
        """Encode a chunk and store it in-memory, returning the embedding vector."""
        vector = self.encoder.encode([text])[0]
        if len(vector) != self.dim:
            raise ValueError(f"Embedding dimension mismatch: index dim is {self.dim}, vector dim is {len(vector)}.")
        self.entries[chunk_id] = ANNEntry(
            chunk_id=chunk_id,
            text=text,
            vector=vector,
            metadata=metadata,
        )
        return vector

    def bulk_add(self, items: Iterable[Tuple[str, str, Dict]]) -> None:
        for chunk_id, text, metadata in items:
            self.add(chunk_id, text, metadata)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """Return cosine similarity neighbours for the query text."""
        if not self.entries:
            return []
        query_vec = self.encoder.encode([query])[0]
        q_norm = np.linalg.norm(query_vec) or 1.0
        results: List[Tuple[str, float, Dict]] = []
        for entry in self.entries.values():
            denom = (np.linalg.norm(entry.vector) or 1.0) * q_norm
            score = float(np.dot(entry.vector, query_vec) / denom)
            results.append((entry.chunk_id, score, entry.metadata))
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def rebuild(self) -> None:
        # Placeholder to match CLI expectation; no-op for in-memory index.
        return
