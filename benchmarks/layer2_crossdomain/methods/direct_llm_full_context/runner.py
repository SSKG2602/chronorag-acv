from __future__ import annotations

from benchmarks.layer2_crossdomain.prompts import build_direct_full_context_prompt
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


METHOD_NAME = "direct_llm_full_context"


def select_evidence(_case: QuestionCase, corpus: list[CorpusRow], _top_k: int) -> list[CorpusRow]:
    return corpus


def build_prompt(case: QuestionCase, corpus: list[CorpusRow], top_k: int) -> dict:
    prompt, truncated, metadata = build_direct_full_context_prompt(case, corpus)
    included_rows = corpus[: int(metadata["included_rows"])]
    return {
        "prompt": prompt,
        "evidence_rows": included_rows,
        "prompt_truncated": truncated,
        "metadata": {
            "method_family": METHOD_NAME,
            "uses_retrieval": False,
            "uses_tcc": False,
            **metadata,
        },
    }
