from __future__ import annotations

import re
from typing import Any, Sequence

from chronorag.stdcomp.bm25_baseline import BM25Index, build_index


ISO_DATE_RE = re.compile(r"\b(?:18|19|20)\d{2}-\d{2}-\d{2}\b")
YEAR_MONTH_RE = re.compile(r"\b(?:18|19|20)\d{2}-\d{2}\b")
YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
MONTH_RE = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?\s+((?:18|19|20)\d{2})\b",
    re.IGNORECASE,
)
MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


def extract_date_terms(question: str) -> list[str]:
    terms: set[str] = set()
    for match in ISO_DATE_RE.findall(question):
        terms.add(match.lower())
    for match in YEAR_MONTH_RE.findall(question):
        terms.add(match.lower())
    for month, year in MONTH_RE.findall(question):
        normalized_month = MONTHS[month.lower().rstrip(".")]
        terms.add(f"{year}-{normalized_month}")
        terms.add(f"{month.lower()} {year}".rstrip("."))
    for year in YEAR_RE.findall(question):
        terms.add(year)
    return sorted(terms, key=lambda value: (-len(value), value))


def filter_text(row: Any) -> str:
    parts = [
        str(getattr(row, "raw_text", "") or ""),
        str(getattr(row, "source_file", "") or ""),
        str(getattr(row, "source_kind", "") or ""),
        str(getattr(row, "source_family", "") or ""),
        str(getattr(row, "entity", "") or ""),
        str(getattr(row, "metric_or_claim", "") or ""),
        str(getattr(row, "value", "") or ""),
    ]
    return " ".join(parts).lower()


def matching_indexes(corpus: Sequence[Any], terms: Sequence[str]) -> list[int]:
    lowered = [term.lower() for term in terms]
    return [
        idx
        for idx, row in enumerate(corpus)
        if any(term in filter_text(row) for term in lowered)
    ]


def run_date_filter_baseline(corpus: Sequence[Any], questions: Sequence[Any], top_k: int = 5) -> dict[str, Any]:
    index: BM25Index = build_index(corpus)
    results = []
    fallback_count = 0
    for case in questions:
        terms = extract_date_terms(str(case.question))
        candidates = matching_indexes(corpus, terms) if terms else []
        fallback = not candidates
        if fallback:
            fallback_count += 1
            candidates = list(range(len(corpus)))
        ranked = index.search(str(case.question), top_k=top_k, candidate_indexes=candidates)
        results.append(
            {
                "case_id": case.id,
                "question": case.question,
                "selected_evidence_ids": [item.evidence_id for item in ranked],
                "ranked_evidence": [item.__dict__ for item in ranked],
                "metadata": {
                    "ranking": "date_string_filter_then_bm25",
                    "date_terms": terms,
                    "filtered_candidate_count": len(candidates),
                    "fallback_to_all_candidates": fallback,
                    "uses_temporal_metadata": False,
                },
            }
        )
    return {
        "method": "date_filter_rag",
        "top_k": top_k,
        "candidate_unit": "layer2_evidence_row_raw_text",
        "fallback_count": fallback_count,
        "notes": [
            "Filters by naive string containment of query date terms in raw/source text fields.",
            "Ranks filtered candidates by BM25.",
            "Does not separate valid time from transaction time and does not use forbidden-time suppression.",
        ],
        "results": results,
    }
