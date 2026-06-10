from __future__ import annotations

import os

from benchmarks.layer2_crossdomain.methods.metadata_temporal_rag.retrieval import retrieve
from benchmarks.layer2_crossdomain.prompts import build_grounded_prompt
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


METHOD_NAME = "metadata_temporal_rag"


def select_evidence(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> list[CorpusRow]:
    return retrieve(case, corpus, top_k=top_k)


def build_prompt(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> dict:
    rows = select_evidence(case, corpus, top_k)
    prompt = build_grounded_prompt(case, rows, METHOD_NAME)
    return {
        "prompt": prompt,
        "evidence_rows": rows,
        "prompt_truncated": False,
        "metadata": {
            "method_family": METHOD_NAME,
            "uses_retrieval": True,
            "uses_tcc": False,
            "retrieval_note": "Independent raw_text plus metadata baseline; no ChronoRAG temporal fusion or ChronoSanity.",
            "embedding_model": os.getenv("CHRONORAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
            "embedding_dim": int(os.getenv("CHRONORAG_EMBED_DIM", "384")),
            "prompt_chars": len(prompt),
        },
    }
