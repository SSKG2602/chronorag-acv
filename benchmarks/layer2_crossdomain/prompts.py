from __future__ import annotations

import json

from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


ANSWER_SCHEMA = {
    "answer": "string",
    "behavior": "answer|partial|refuse|clarify",
    "cited_evidence_ids": ["string"],
    "valid_time_used": ["YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or YYYY"],
    "transaction_time_used_as_valid_time": False,
    "conflict_warning": False,
    "partial_or_refusal": False,
    "clarification_requested": False,
    "confidence": "low|medium|high",
}

JSON_ONLY_RULES = """Output contract:
- Think privately. Return only the final JSON object.
- Return ONLY one valid JSON object.
- Return exactly the required JSON object and never return null for required fields.
- Do not wrap the JSON in markdown or code fences.
- Do not include prose before JSON.
- Do not include prose after JSON.
- Do not apologize.
- Do not explain outside the JSON fields.
- If evidence is insufficient, ambiguous, or has multiple candidates, still return JSON.
- If multiple candidate evidence rows exist, set cited_evidence_ids to the best supported IDs.
- If the answer cannot be determined, use behavior "partial", "clarify", or "refuse" and set partial_or_refusal or clarification_requested accordingly.
"""

ANSWER_FIELD_RULES = """Answer field contract:
- Keep answer short but complete.
- Prefer one complete sentence.
- Use at most two sentences unless the question explicitly asks for comparison, conflict, or multiple records.
- Keep the answer field under roughly 80 words unless conflict or comparison truly requires more.
- For answerable exact retrieval cases, the JSON "answer" field MUST include the entity, metric_or_claim, value, unit if available, and exact valid_from/valid_to date or timestamp from the cited evidence.
- For numeric macro/market rows, use this style: "{entity} {metric_or_claim} was {value} {unit} on {valid_from}."
- For GitHub release rows, use this style: "{entity} {metric_or_claim} was {value} on {valid_from}."
- For SEC filing rows, use valid_from if present, otherwise transaction_time.
- Do not answer with only a number and unit.
- Do not list all evidence rows unless the question requires it.
- Cite at most 1 evidence ID for simple exact, metric, or year cases.
- Cite 2 evidence IDs only when conflict or comparison requires it.
- Cite at most 3 evidence IDs for SEC or source-specific multi-record cases.
"""

HARD_TEMPORAL_RULES = """Hard temporal decision rules:
- If selected evidence contains a direct answer, answer from the best cited row.
- Do not refuse merely because multiple same-year rows exist.
- If the question asks for a year and evidence has multiple exact dates in that year, choose the highest-ranked selected evidence satisfying entity, metric, and valid-time constraints.
- If an exact date is asked, prefer exact-date evidence over same-year evidence.
- If an exact year is asked, an exact date inside that year can satisfy the year query unless the question explicitly asks for one annual aggregate.
- If the question asks for a year and multiple daily/monthly records exist, answer with one representative evidence row and state the specific valid date used.
- If many rows exist for a year, choose one representative exact valid-time row unless the question asks for all records.
- Do not mistake different dates in a time series for conflict.
- Conflict means disagreement for the same entity, metric, and valid time, not ordinary different values on different dates.
- If wording says "not YEAR" but repeats the same year as the target, treat the positive target year as intended and select the best matching evidence from that year.
- Refuse only when no selected evidence supports the requested entity, metric, and time.
- Clarify only when the question itself lacks enough target entity, metric, or time and selected evidence does not resolve it.
- For SEC filings, answer with company/entity, form type or claim, and filing/valid date from cited evidence.
- For market and FRED rows, answer with entity, metric, value, unit, and exact valid date.
- For GitHub releases, answer with repository/project, release/tag/version, and release date.
- Do not treat transaction_time, publication time, filing time, or release time as valid_time unless the question explicitly asks for that timing.
- For ambiguous time expressions like "recent period" or "around", avoid arbitrary confident selection. Clarify or return partial evidence.
"""

HARD_CATEGORY_RULES = """Hard category behavior:
- conflict_detection: if the same valid time has conflicting values, answer with a short conflict warning and cite conflicting IDs. If evidence only shows different dates, say there is no same-valid-time conflict.
- partial_or_insufficient_evidence: if exact evidence is missing, use partial/refusal and do not invent exact values. If representative evidence exists inside a broad year, say it is not an aggregate for the whole year.
- source_specific_temporal_query: use only evidence from the requested source/domain, cite 1-3 IDs max, and do not list every matching filing/date.
- metric_specific_query: answer only the requested metric/form and exclude unrelated metrics.
- cross_domain_temporal_comparison: include both domains only if evidence for both is selected; otherwise use partial and state which side is missing.
- ambiguous_time_query: do not pick an arbitrary date confidently; clarify or provide partial evidence with low/medium confidence.
"""


def compact_row(row: CorpusRow) -> str:
    return json.dumps(row.to_prompt_dict(), ensure_ascii=False, sort_keys=True)


def build_evidence_fact_sentence(row: CorpusRow) -> str:
    """Build a fact sentence only from evidence fields, never answer-key fields."""
    when = row.valid_from or row.transaction_time
    value = "" if row.value is None else str(row.value)
    unit = f" {row.unit}" if row.unit and value else ""
    if value and when:
        return f"{row.entity} {row.metric_or_claim} was {value}{unit} on {when}."
    if value:
        return f"{row.entity} {row.metric_or_claim} was {value}{unit}."
    if when:
        return f"{row.entity} {row.metric_or_claim} was recorded on {when}."
    return f"{row.entity} {row.metric_or_claim}."


def build_candidate_fact_hint(rows: list[CorpusRow]) -> str:
    if not rows:
        return "No evidence-derived candidate fact sentence is available."
    row = rows[0]
    if row.temporal_type not in {"valid_time_exact", "revision"}:
        return "No exact evidence-derived candidate fact sentence is available."
    return (
        "Use this evidence-derived candidate fact sentence if it is supported by "
        f"the cited evidence: {build_evidence_fact_sentence(row)}"
    )


def build_grounded_prompt(case: QuestionCase, rows: list[CorpusRow], method_name: str) -> str:
    evidence = "\n".join(compact_row(row) for row in rows)
    # Layer 2 hard cases previously produced semantically useful but overlong
    # provider outputs that were truncated before JSON closed. The prompt keeps
    # answers compact while preserving the evidence facts needed for validation.
    return f"""You are evaluating a temporal QA method named {method_name}.

Use only the supplied evidence rows.
Do not use outside knowledge.
Cite only evidence IDs from the supplied rows.
Do not invent evidence IDs.
valid_time is when the claim/data is about.
Do not treat transaction_time or publication time as valid_time.
Prefer exact valid-time evidence over broad-window evidence for exact-time questions.
If evidence is missing, conflicting, partial, or ambiguous, say so clearly.
For conflict/revision questions, surface disagreement instead of hiding it.
If this is a same-entity wrong-year or multi-evidence case, select the evidence matching the requested valid_time and still return JSON.
Each evidence row below is a JSON evidence packet with id, domain, entity, metric_or_claim, value, unit, valid_from, valid_to, transaction_time, temporal_type, and raw_text.
{JSON_ONLY_RULES}
{ANSWER_FIELD_RULES}
{HARD_TEMPORAL_RULES}
{HARD_CATEGORY_RULES}
{build_candidate_fact_hint(rows)}
Required JSON schema and allowed values:
{json.dumps(ANSWER_SCHEMA, sort_keys=True)}

Question:
{case.question}

Evidence rows:
{evidence}
"""


def build_direct_full_context_prompt(
    case: QuestionCase,
    corpus: list[CorpusRow],
    max_chars: int = 45000,
) -> tuple[str, bool, dict[str, int | bool]]:
    rows: list[CorpusRow] = []
    used = 0
    truncated = False
    for row in corpus:
        rendered = compact_row(row)
        if used + len(rendered) > max_chars:
            truncated = True
            break
        rows.append(row)
        used += len(rendered)
    prompt = build_grounded_prompt(case, rows, "direct_llm_full_context")
    return prompt, truncated, {
        "prompt_chars": len(prompt),
        "included_rows": len(rows),
        "total_rows": len(corpus),
        "context_budget_chars": max_chars,
        "context_truncated": truncated,
    }
