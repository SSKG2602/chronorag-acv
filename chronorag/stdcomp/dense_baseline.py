from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from chronorag.stdcomp.bm25_baseline import candidate_text, row_id


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def run_dense_baseline(
    corpus: Sequence[Any],
    questions: Sequence[Any],
    top_k: int = 5,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
    cache_dir: str | Path = "chronorag/stdcomp/results/cache",
    corpus_fingerprint: str | None = None,
) -> dict[str, Any]:
    ids = [row_id(row) for row in corpus]
    texts = [candidate_text(row) for row in corpus]
    cache_path = _cache_path(cache_dir, model_name, ids, texts, corpus_fingerprint)
    doc_vectors = _load_cached_embeddings(cache_path, ids)
    if doc_vectors is None:
        model = _load_model(model_name)
        doc_vectors = _encode(model, texts, batch_size=batch_size)
        _save_cached_embeddings(cache_path, ids, doc_vectors, model_name)
    else:
        model = _load_model(model_name)

    query_texts = [str(case.question) for case in questions]
    query_vectors = _encode(model, query_texts, batch_size=batch_size)
    results = []
    for case, query_vec in zip(questions, query_vectors):
        scores = np.dot(doc_vectors, query_vec)
        order = sorted(range(len(ids)), key=lambda idx: (-float(scores[idx]), ids[idx]))[:top_k]
        ranked = [
            {"evidence_id": ids[idx], "rank": rank, "score": float(scores[idx])}
            for rank, idx in enumerate(order, start=1)
        ]
        results.append(
            {
                "case_id": case.id,
                "question": case.question,
                "selected_evidence_ids": [item["evidence_id"] for item in ranked],
                "ranked_evidence": ranked,
                "metadata": {
                    "ranking": "cosine_similarity_normalized_embeddings",
                    "embedding_model": model_name,
                    "uses_temporal_metadata": False,
                },
            }
        )
    return {
        "method": "dense_only",
        "top_k": top_k,
        "candidate_unit": "layer2_evidence_row_raw_text",
        "embedding_model": model_name,
        "cache_path": str(cache_path),
        "notes": [
            "Ranks only by cosine similarity over normalized off-the-shelf embeddings.",
            "Does not use TCC, temporal metadata, temporal fusion, or forbidden-time suppression.",
        ],
        "results": results,
    }


def _load_model(model_name: str) -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError(
            "sentence-transformers is required for the dense-only baseline. "
            "Install dependencies or rerun without dense evaluation only for diagnostics."
        ) from exc
    return SentenceTransformer(model_name)


def _encode(model: Any, texts: Sequence[str], batch_size: int) -> np.ndarray:
    vectors = np.asarray(
        model.encode(
            list(texts),
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        ),
        dtype=np.float32,
    )
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return vectors / norms


def _cache_path(
    cache_dir: str | Path,
    model_name: str,
    ids: Sequence[str],
    texts: Sequence[str],
    corpus_fingerprint: str | None,
) -> Path:
    digest = hashlib.sha256()
    digest.update(model_name.encode("utf-8"))
    if corpus_fingerprint:
        digest.update(corpus_fingerprint.encode("utf-8"))
    else:
        for evidence_id, text in zip(ids, texts):
            digest.update(evidence_id.encode("utf-8"))
            digest.update(b"\0")
            digest.update(text.encode("utf-8"))
            digest.update(b"\0")
    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root / f"dense_docs_{digest.hexdigest()[:16]}.npz"


def _load_cached_embeddings(path: Path, ids: Sequence[str]) -> np.ndarray | None:
    if not path.exists():
        return None
    payload = np.load(path, allow_pickle=False)
    cached_ids = [str(item) for item in payload["ids"].tolist()]
    if cached_ids != list(ids):
        return None
    return np.asarray(payload["embeddings"], dtype=np.float32)


def _save_cached_embeddings(path: Path, ids: Sequence[str], embeddings: np.ndarray, model_name: str) -> None:
    np.savez_compressed(path, ids=np.asarray(ids), embeddings=embeddings)
    path.with_suffix(".json").write_text(
        json.dumps({"embedding_model": model_name, "rows": len(ids), "cache_file": str(path)}, indent=2),
        encoding="utf-8",
    )
