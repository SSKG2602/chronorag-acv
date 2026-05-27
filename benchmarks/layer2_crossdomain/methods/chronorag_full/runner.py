from __future__ import annotations

from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import retrieve_with_chronorag_adapter
from benchmarks.layer2_crossdomain.prompts import build_grounded_prompt
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


METHOD_NAME = "chronorag_full"


def select_evidence(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> list[CorpusRow]:
    rows, _metadata = retrieve_with_chronorag_adapter(case, corpus, top_k)
    return rows


def build_prompt(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> dict:
    rows, metadata = retrieve_with_chronorag_adapter(case, corpus, top_k)
    prompt = build_grounded_prompt(case, rows, METHOD_NAME)
    return {
        "prompt": prompt,
        "evidence_rows": rows,
        "prompt_truncated": False,
        "metadata": {**metadata, "prompt_chars": len(prompt)},
    }
