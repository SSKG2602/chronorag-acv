from __future__ import annotations

import re
from collections import Counter

from benchmarks.layer2_crossdomain.methods.metadata_temporal_rag.chunking import chunk_rows
from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


TOKEN_RE = re.compile(r"[a-z0-9]+")
YEAR_RE = re.compile(r"\b(19[0-9]{2}|20[0-9]{2}|18[0-9]{2})\b")


def retrieve(case: QuestionCase, corpus: list[CorpusRow], top_k: int = 5) -> list[CorpusRow]:
    scored = [(row, _score(case, row)) for row in chunk_rows(corpus)]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [row for row, _ in scored[:top_k]]


def _tokens(text: str) -> Counter[str]:
    return Counter(TOKEN_RE.findall(text.lower()))


def _score(case: QuestionCase, row: CorpusRow) -> float:
    query_tokens = _tokens(case.question)
    raw_tokens = _tokens(row.raw_text)
    lexical = sum(min(query_tokens[token], raw_tokens[token]) for token in query_tokens)
    lexical_score = lexical / max(1.0, len(query_tokens))
    domain_score = 0.15 if row.domain == case.domain else 0.0
    entity_score = 0.20 if row.entity.lower() in case.question.lower() else 0.0
    related_score = _related_entity_score(case, row)
    metric_score = _field_overlap(case.question, row.metric_or_claim) * 0.20
    source_score = 0.12 if row.source_family.lower().replace("_", " ") in case.question.lower() else 0.0
    conflict_score = _conflict_score(case, row)
    temporal_score = _temporal_score(case, row)
    return lexical_score + domain_score + entity_score + related_score + metric_score + source_score + conflict_score + temporal_score


def _field_overlap(query: str, field: str | None) -> float:
    if not field:
        return 0.0
    query_terms = set(TOKEN_RE.findall(query.lower()))
    field_terms = set(TOKEN_RE.findall(field.lower()))
    if not field_terms:
        return 0.0
    return len(query_terms & field_terms) / len(field_terms)


def _related_entity_score(case: QuestionCase, row: CorpusRow) -> float:
    query_lower = case.question.lower()
    return 0.10 if any(entity.lower() in query_lower for entity in row.related_entities) else 0.0


def _conflict_score(case: QuestionCase, row: CorpusRow) -> float:
    if case.category in {"conflict_or_revision", "conflict_detection"} and row.temporal_type in {"conflict_claim", "revision"}:
        return 0.35
    if case.category in {"broad_window_vs_exact", "broad_window_distractor"} and row.temporal_type == "valid_time_exact":
        return 0.20
    return 0.0


def _temporal_score(case: QuestionCase, row: CorpusRow) -> float:
    years = YEAR_RE.findall(case.question)
    query_lower = case.question.lower()
    asks_transaction = any(
        token in query_lower
        for token in (
            "transaction-time-only",
            "transaction time only",
            "which records are transaction",
            "publication records",
            "republished records",
        )
    )
    if row.temporal_type == "transaction_time_only":
        return 0.55 if asks_transaction else -0.35
    if not years:
        if row.temporal_type == "missing_or_unknown":
            return 0.03
        return 0.12
    year = years[0]
    if row.valid_from and row.valid_from.startswith(year) and row.temporal_type == "valid_time_exact":
        return 0.80
    if row.valid_from and row.valid_to and row.valid_from[:4] <= year <= row.valid_to[:4]:
        if row.temporal_type == "valid_time_range":
            return 0.45
        return 0.30
    if row.temporal_type == "missing_or_unknown":
        return 0.03
    return 0.0
