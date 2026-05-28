from __future__ import annotations

import json

from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


ANSWER_SCHEMA = {
    "answer": "string",
    "behavior": "answer|compare|prefer_exact|partial|refuse|conflict_warning|clarify",
    "cited_evidence_ids": ["evidence_id"],
    "valid_time_used": ["YYYY or interval"],
    "transaction_time_used_as_valid_time": False,
    "conflict_warning": False,
    "partial_or_refusal": False,
    "clarification_requested": False,
    "confidence": "high|medium|low",
}

JSON_ONLY_RULES = """Output contract:
- Return ONLY one valid JSON object.
- Do not wrap the JSON in markdown or code fences.
- Do not include prose before JSON.
- Do not include prose after JSON.
- Do not apologize.
- Do not explain outside the JSON fields.
- If evidence is insufficient, ambiguous, or has multiple candidates, still return JSON.
- If multiple candidate evidence rows exist, set cited_evidence_ids to the best supported IDs.
- If the answer cannot be determined, use behavior "partial", "clarify", or "refuse" and set partial_or_refusal or clarification_requested accordingly.
"""


def compact_row(row: CorpusRow) -> str:
    return json.dumps(row.to_prompt_dict(), ensure_ascii=False, sort_keys=True)


def build_grounded_prompt(case: QuestionCase, rows: list[CorpusRow], method_name: str) -> str:
    evidence = "\n".join(compact_row(row) for row in rows)
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
{JSON_ONLY_RULES}
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
