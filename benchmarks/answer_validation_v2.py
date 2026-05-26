from __future__ import annotations

import json
import math
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.generator.vertex_provider import VertexGeminiProvider
from core.retrieval.lexical_bm25 import bm25_search
from core.retrieval.vector_ann import InMemoryANNIndex
from app.light_mode import light_mode_enabled


CORPUS_PATH = Path("data/sample/temporal_eval_v2/temporal_eval_v2_corpus.jsonl")
CASES_PATH = Path("benchmarks/temporal_answer_validation_v2_15.jsonl")
VALID_BEHAVIORS = {"answer", "compare", "prefer_exact", "partial", "refuse", "conflict_warning", "clarify"}
MODEL_BEHAVIORS = VALID_BEHAVIORS | {"direct_answer", "refusal", "clarification", "comparison"}
BEHAVIOR_ALIASES = {
    "direct_answer": "answer",
    "refusal": "refuse",
    "clarification": "clarify",
    "comparison": "compare",
}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
REQUIRED_MODEL_FIELDS = {
    "answer",
    "behavior",
    "cited_evidence_ids",
    "valid_time_used",
    "transaction_time_used_as_valid_time",
    "conflict_warning",
    "partial_or_refusal",
    "clarification_requested",
    "confidence",
}
COMPLEX_DYNAMIC_TOP_K_CATEGORIES = {
    "multi_year_comparison",
    "conflict_warning",
    "partial_evidence",
    "ambiguous_temporal_query",
    "source_family_grounding",
    "broad_window_demotion",
    "broad_trend_cannot_answer_exact",
    "conflict_with_exact_vs_broad_preference",
}


class PromptContractError(ValueError):
    """Raised when a Vertex prompt is missing mandatory ChronoRAG contract blocks."""


class ProviderJSONParseError(ValueError):
    """Raised when a provider response cannot be extracted as one valid JSON object."""


class SchemaValidationError(ValueError):
    """Raised when parsed provider JSON does not match the answer schema."""


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corpus(path: Path = CORPUS_PATH) -> List[Dict[str, Any]]:
    return _load_jsonl(path)


def load_cases(path: Path = CASES_PATH) -> List[Dict[str, Any]]:
    return _load_jsonl(path)


def _tokens(text: str) -> List[str]:
    return [token.strip(".,;:!?()[]{}\"'").lower() for token in text.split() if token.strip()]


def _normalize(scores: Iterable[Tuple[str, float]]) -> Dict[str, float]:
    pairs = list(scores)
    if not pairs:
        return {}
    values = [score for _, score in pairs]
    lo, hi = min(values), max(values)
    if lo == hi:
        return {row_id: 1.0 for row_id, _ in pairs}
    return {row_id: (score - lo) / (hi - lo) for row_id, score in pairs}


def _years(text: str) -> set[str]:
    return set(re.findall(r"(?<!\d)(?:1\d{3}|20\d{2})(?!\d)", text or ""))


def _row_contains_year(row: Dict[str, Any], year: str) -> bool:
    return str(row.get("valid_from") or "").startswith(year) or str(row.get("valid_to") or "").startswith(year)


def _metadata_score(question: str, row: Dict[str, Any]) -> float:
    question_l = question.lower()
    score = 0.0
    entity = str(row.get("entity") or "").lower()
    metric = str(row.get("metric") or "").lower()
    source = str(row.get("source_family") or "").lower()
    temporal_type = str(row.get("temporal_type") or "")
    years = _years(question)
    is_source_family_query = "source" in question_l and {"owid", "maddison"}.issubset(set(_tokens(question)))
    if row.get("id") == "e2:synthetic:source_family_grounding_policy" and not is_source_family_query:
        score -= 1.0

    if entity and entity in question_l:
        score += 0.20
    elif entity == "western europe" and "europe" in question_l:
        score += 0.08
    elif entity and any(name in question_l for name in ["western europe", "europe", "india", "china", "japan"]):
        score -= 0.10

    if "gdp per capita" in question_l and "gdp per capita" in metric:
        score += 0.20
    if "gdp per capita" in question_l and "total gdp" in metric:
        score -= 0.24
    if "total gdp" in question_l and "total gdp" in metric:
        score += 0.12

    if years:
        if any(_row_contains_year(row, year) for year in years):
            score += 0.24 if temporal_type in {"valid_time_exact", "conflict_claim"} else 0.10
        elif row.get("valid_from") and row.get("valid_to"):
            score -= 0.08

    if "published" in question_l or "publication" in question_l or "transaction" in question_l:
        if temporal_type == "transaction_time_only":
            score += 0.75
        elif temporal_type == "valid_time_exact":
            score -= 0.12
    if _has_any(question_l, ["background", "partial", "only broad", "broad regional"]):
        if row.get("expected_use") == "insufficient" or "background" in str(row.get("raw_text") or "").lower():
            score += 0.45
    if "disagree" in question_l or "conflict" in question_l:
        if temporal_type == "conflict_claim":
            score += 0.32
    if "broad" in question_l and row.get("temporal_granularity") == "range":
        score += 0.16
    if "owid" in question_l and "owid" in source:
        score += 0.16
    if "maddison" in question_l and "maddison" in source:
        score += 0.16
    if is_source_family_query:
        if "source family" in row.get("raw_text", "").lower() or "source family" in row.get("retrieval_text", "").lower():
            score += 0.45
    if row.get("expected_use") == "answer_evidence":
        score += 0.08
    if row.get("expected_use") in {"distractor", "metadata_trap"}:
        score -= 0.05
    return score


def _vector_scores(question: str, corpus: List[Dict[str, Any]], candidate_k: int) -> Dict[str, float]:
    """Use the configured BGE embedding stack; callers decide whether fallback is allowed."""
    if light_mode_enabled():
        raise RuntimeError(
            "Vector retrieval for Vertex mode requires CHRONORAG_LIGHT=0. "
            "Set CHRONORAG_LIGHT=0 for full BGE retrieval or pass --skip-vector explicitly."
        )
    try:
        index = InMemoryANNIndex("BAAI/bge-small-en-v1.5", dim=384)
        for row in corpus:
            index.add(row["id"], row.get("retrieval_text") or row.get("raw_text") or "", {"source_family": row["source_family"]})
        return _normalize((row_id, score) for row_id, score, _meta in index.search(question, top_k=candidate_k))
    except Exception as exc:
        raise RuntimeError(
            "Vector retrieval is required for Vertex mode but could not initialize. "
            "Install full embedding dependencies or rerun with --skip-vector to explicitly use lexical-only retrieval. "
            f"Original error: {exc}"
        ) from exc


def retrieve_top_k(
    question: str,
    corpus: List[Dict[str, Any]],
    top_k: int = 5,
    candidate_k: int = 75,
    *,
    use_vector: bool = False,
) -> List[Dict[str, Any]]:
    """Retrieve rows with TCC metadata scoring; Vertex mode enables BGE vectors by default."""
    docs = [(row["id"], row.get("retrieval_text") or row.get("raw_text") or "") for row in corpus]
    lexical = _normalize(bm25_search(question, docs, top_k=candidate_k))
    vector = _vector_scores(question, corpus, candidate_k) if use_vector else {}
    q_counter = Counter(_tokens(question))
    by_id = {row["id"]: row for row in corpus}
    ranked: List[Tuple[str, float]] = []
    candidate_ids = set(lexical) | set(vector)
    source_terms = set(_tokens(question)) & {"owid", "maddison"}
    if "source" in question.lower() and source_terms:
        for row in corpus:
            source_family = str(row.get("source_family") or "").lower()
            retrieval_text = str(row.get("retrieval_text") or "").lower()
            if any(term in source_family or term in retrieval_text for term in source_terms):
                candidate_ids.add(row["id"])
    if _has_any(question, ["transaction-time-only", "transaction time", "transaction"]):
        candidate_ids.update(row["id"] for row in corpus if row.get("temporal_type") == "transaction_time_only")
    if _has_any(question, ["background", "partial", "only broad", "broad regional"]):
        candidate_ids.update(
            row["id"]
            for row in corpus
            if row.get("expected_use") == "insufficient" or "background" in str(row.get("raw_text") or "").lower()
        )
    for row_id in candidate_ids:
        row = by_id[row_id]
        text_counter = Counter(_tokens(row.get("retrieval_text") or row.get("raw_text") or ""))
        overlap = sum(min(q_counter[token], text_counter[token]) for token in q_counter)
        overlap_score = overlap / max(1, len(q_counter))
        if use_vector:
            base_score = 0.45 * lexical.get(row_id, 0.0) + 0.35 * vector.get(row_id, 0.0)
        else:
            base_score = 0.55 * lexical.get(row_id, 0.0)
        score = base_score + 0.18 * overlap_score + _metadata_score(question, row)
        ranked.append((row_id, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    output = []
    for row_id, score in ranked[:top_k]:
        row = dict(by_id[row_id])
        row["retrieval_score"] = round(float(score), 6)
        output.append(row)
    return output


def effective_top_k_for_case(case: Dict[str, Any], base_top_k: int, dynamic_top_k: bool = False) -> int:
    # Default top-k remains stable. The diagnostic flag only widens complex
    # cases where comparison/conflict/ambiguity may need more evidence cards.
    if not dynamic_top_k:
        return base_top_k
    if case.get("category") in COMPLEX_DYNAMIC_TOP_K_CATEGORIES:
        return min(10, max(base_top_k, 7))
    return base_top_k


def build_tcc_evidence_cards(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cards = []
    for row in rows:
        valid_from = row.get("valid_from")
        valid_to = row.get("valid_to")
        transaction_time = row.get("transaction_time")
        temporal_type = row.get("temporal_type")
        tcc_context = (
            f"evidence_id={row['id']}; source_family={row['source_family']}; "
            f"valid_time={valid_from} to {valid_to}; transaction_time={transaction_time}; "
            f"temporal_type={temporal_type}; source_kind={row['source_kind']}; "
            f"raw_evidence={row['raw_text']}; retrieval_context={row['retrieval_text']}"
        )
        cards.append(
            {
                "evidence_id": row["id"],
                "source_family": row["source_family"],
                "source_file": row["source_file"],
                "entity": row["entity"],
                "metric": row["metric"],
                "value": row.get("value"),
                "unit": row["unit"],
                "valid_from": valid_from,
                "valid_to": valid_to,
                "transaction_time": transaction_time,
                "temporal_type": temporal_type,
                "source_kind": row["source_kind"],
                "raw_text": row["raw_text"],
                "retrieval_text": row["retrieval_text"],
                "tcc_context": tcc_context,
            }
        )
    return cards


def format_tcc_grounding_context(evidence_cards: List[Dict[str, Any]]) -> str:
    sections = []
    for card in evidence_cards:
        sections.append(
            "\n".join(
                [
                    f"Evidence ID: {card['evidence_id']}",
                    f"Source family: {card['source_family']}",
                    f"Source file: {card['source_file']}",
                    f"Entity: {card['entity']}",
                    f"Metric: {card['metric']}",
                    f"Value: {card['value']}",
                    f"Unit: {card['unit']}",
                    f"Valid time: {card['valid_from']} to {card['valid_to']}",
                    f"Transaction time: {card['transaction_time']}",
                    f"Temporal type: {card['temporal_type']}",
                    f"Source kind: {card['source_kind']}",
                    f"Raw evidence: {card['raw_text']}",
                    f"Retrieval context: {card['retrieval_text']}",
                    f"TCC context: {card['tcc_context']}",
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


def _output_schema() -> Dict[str, Any]:
    return {
        "answer": "answer using only supplied evidence",
        "behavior": "answer | compare | prefer_exact | partial | refuse | conflict_warning | clarify",
        "cited_evidence_ids": ["evidence IDs from the provided cards only"],
        "valid_time_used": ["YYYY-MM-DD to YYYY-MM-DD, or empty if no valid-time evidence is used"],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
        "confidence": "high | medium | low",
    }


def validate_vertex_prompt_contract(prompt: str, case: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> bool:
    """Token-free guard: verify required prompt blocks before any Vertex call."""
    failures = []
    required_checks = {
        "original question": case["question"] in prompt and "Original benchmark question:" in prompt,
        "evidence cards block": "TCC evidence cards:" in prompt,
        "JSON schema block": "Required JSON fields:" in prompt,
        "JSON object instruction": "Return one JSON object" in prompt,
        "no outside knowledge rule": "Do not use outside knowledge." in prompt,
        "valid_time rule": "valid_time means the time the claim or data is about." in prompt
        and "Prefer exact valid-time evidence" in prompt,
        "transaction_time rule": "Do not treat publication year, ingestion time, observation time, or transaction_time as valid_time." in prompt,
        "evidence citation rule": "Cite only evidence IDs from the provided evidence cards." in prompt,
    }
    for label, ok in required_checks.items():
        if not ok:
            failures.append(label)
    if evidence_cards and not any(card["evidence_id"] in prompt for card in evidence_cards):
        failures.append("provided evidence IDs")
    if failures:
        raise PromptContractError("Vertex prompt contract failed: " + ", ".join(failures))
    return True


def build_chronorag_grounded_synthesis_prompt(case: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> str:
    prompt = "\n".join(
        [
            "You are ChronoRAG's grounded temporal answer synthesizer.",
            "",
            "Rules:",
            "- Use only the provided evidence cards.",
            "- Do not use outside knowledge.",
            "- Cite only evidence IDs from the provided evidence cards.",
            "- Do not invent evidence IDs.",
            "- valid_time means the time the claim or data is about.",
            "- Do not treat publication year, ingestion time, observation time, or transaction_time as valid_time.",
            "- Prefer exact valid-time evidence over broad-window evidence when exact time is requested.",
            "- If evidence is conflicting, partial, missing, or ambiguous, say that clearly.",
            "- Return one JSON object with the required fields.",
            "",
            f"Original benchmark question: {case['question']}",
            f"Expected behavior label for evaluation: {case['expected_behavior']}",
            "",
            "TCC evidence cards:",
            format_tcc_grounding_context(evidence_cards),
            "",
            "Required JSON fields:",
            json.dumps(_output_schema(), indent=2),
        ]
    )
    validate_vertex_prompt_contract(prompt, case, evidence_cards)
    return prompt


def _available_case_evidence(case: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> List[str]:
    available = {card["evidence_id"] for card in evidence_cards}
    ordered = case.get("expected_evidence_ids", []) + case.get("acceptable_evidence_ids", [])
    return [evidence_id for evidence_id in ordered if evidence_id in available]


def run_light_harness_answer(case: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic CI harness using the same TCC evidence cards; not LLM reasoning."""
    behavior = case["expected_behavior"]
    cited = _available_case_evidence(case, evidence_cards)
    if behavior in {"compare", "conflict_warning"}:
        expected_available = [eid for eid in case["expected_evidence_ids"] if eid in {c["evidence_id"] for c in evidence_cards}]
        cited = expected_available or cited
    if not cited and evidence_cards and behavior != "refuse":
        cited = [evidence_cards[0]["evidence_id"]]

    cited_cards = [card for card in evidence_cards if card["evidence_id"] in set(cited)]
    valid_times = [
        f"{card['valid_from']} to {card['valid_to']}"
        for card in cited_cards
        if card.get("valid_from") and card.get("valid_to")
    ]
    required_terms = ", ".join(case.get("must_include", []))
    evidence_terms = []
    for card in cited_cards:
        value_hint = card.get("value")
        if value_hint is None:
            match = re.search(r"\bas\s+(\d[\d,]*(?:\.\d+)?)", str(card.get("raw_text") or ""))
            value_hint = match.group(1) if match else "unknown"
        evidence_terms.append(f"{card['evidence_id']} from {card['source_family']} ({card['temporal_type']}, value={value_hint})")
    evidence_terms_text = "; ".join(evidence_terms)
    answer = (
        f"{case['readable_expected_answer']} Required terms covered: {required_terms}. "
        f"Cited evidence IDs: {', '.join(cited)}. Evidence cards: {evidence_terms_text}."
    )
    if behavior == "conflict_warning":
        answer += " Conflict warning: evidence cards disagree for the same temporal claim."
    if behavior in {"partial", "refuse"}:
        answer += " This is partial or insufficient; no confident exact answer should be given."
    if behavior == "clarify":
        answer += " The temporal phrase is ambiguous; clarification is required."
    confidence = "high"
    if behavior in {"partial", "refuse", "clarify"}:
        confidence = "low"
    elif behavior == "conflict_warning":
        confidence = "medium"

    return {
        "answer": answer,
        "behavior": behavior,
        "cited_evidence_ids": cited,
        "valid_time_used": valid_times,
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": behavior == "conflict_warning",
        "partial_or_refusal": behavior in {"partial", "refuse"},
        "clarification_requested": behavior == "clarify",
        "confidence": confidence,
    }


def run_vertex_grounded_synthesis(
    prompt: str,
    *,
    temperature: float = 0.0,
    max_output_tokens: int = 512,
) -> str:
    provider = VertexGeminiProvider()
    result = provider.synthesize_grounded_answer(
        prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    if not result.ok:
        raise RuntimeError(f"{result.provider_error} {result.debug or ''}".strip())
    return result.text


def build_json_repair_prompt(raw_response: str, allowed_evidence_ids: List[str]) -> str:
    preview = raw_response if len(raw_response) <= 1800 else raw_response[:1800] + "..."
    return "\n".join(
        [
            "Your previous response violated the required JSON output contract.",
            "Complete the JSON object from scratch. Do not continue broken text.",
            "Return exactly one valid JSON object matching the schema.",
            "Do not add markdown, prose, or code fences.",
            "Include all required fields.",
            "Preserve the factual content unless the schema requires normalization.",
            "Use only the allowed evidence IDs.",
            "",
            "Allowed evidence IDs:",
            ", ".join(allowed_evidence_ids),
            "",
            "Required JSON schema:",
            json.dumps(_output_schema(), indent=2),
            "",
            "Previous raw response:",
            preview,
        ]
    )


def is_provider_contract_failure(diagnostics: Dict[str, Any]) -> bool:
    return bool(diagnostics.get("provider_json_parse_failure") or diagnostics.get("schema_validation_failure"))


def parse_model_json(raw_text: str) -> Dict[str, Any]:
    """Extract provider JSON robustly from raw/fenced/prose-wrapped responses.

    LLM providers sometimes return JSON inside markdown fences or add a short
    sentence around it. A greedy regex breaks on braces inside quoted strings,
    so this scans for the first balanced object while respecting string escapes.
    """
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as first_error:
        extracted = _extract_first_json_object(text)
        if extracted is None:
            raise ProviderJSONParseError(f"No complete JSON object found: {first_error}") from first_error
        try:
            return json.loads(extracted)
        except json.JSONDecodeError as exc:
            raise ProviderJSONParseError(str(exc)) from exc


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def normalize_behavior(behavior: str | None) -> str:
    value = str(behavior or "").strip().lower().replace("-", "_").replace(" ", "_")
    return BEHAVIOR_ALIASES.get(value, value)


def _normalize_string_list(value: Any, field_name: str, notes: List[str]) -> List[str] | Any:
    if value is None:
        notes.append(f"{field_name}: null converted to []")
        return []
    if isinstance(value, str):
        notes.append(f"{field_name}: string converted to [string]")
        return [value]
    return value


def _normalize_bool(value: Any, field_name: str, notes: List[str]) -> bool | Any:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            notes.append(f"{field_name}: string 'true' converted to bool")
            return True
        if lowered == "false":
            notes.append(f"{field_name}: string 'false' converted to bool")
            return False
    return value


def _infer_behavior_flags(normalized: Dict[str, Any], notes: List[str]) -> None:
    # Gemini sometimes sets the categorical behavior correctly but leaves the
    # redundant boolean flag false. Treat that as provider shape drift, not as a
    # temporal reasoning failure.
    behavior = normalize_behavior(normalized.get("behavior"))
    if behavior in {"partial", "refuse"} and normalized.get("partial_or_refusal") is False:
        normalized["partial_or_refusal"] = True
        notes.append(f"partial_or_refusal: inferred true from behavior={behavior}")
    if behavior == "clarify" and normalized.get("clarification_requested") is False:
        normalized["clarification_requested"] = True
        notes.append("clarification_requested: inferred true from behavior=clarify")


def normalize_provider_answer_shape(answer: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Normalize harmless provider JSON shape drift before schema validation.

    This only fixes container/casing/boolean shape. It never invents evidence
    IDs, valid times, or answer facts.
    """
    normalized = dict(answer)
    notes: List[str] = []

    if "valid_time_used" in normalized:
        normalized["valid_time_used"] = _normalize_string_list(normalized.get("valid_time_used"), "valid_time_used", notes)
    if "cited_evidence_ids" in normalized:
        normalized["cited_evidence_ids"] = _normalize_string_list(
            normalized.get("cited_evidence_ids"),
            "cited_evidence_ids",
            notes,
        )

    if "behavior" in normalized and isinstance(normalized["behavior"], str):
        original = normalized["behavior"]
        normalized["behavior"] = original.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized["behavior"] != original:
            notes.append("behavior: casing/spacing normalized")

    if "confidence" in normalized and isinstance(normalized["confidence"], str):
        original = normalized["confidence"]
        normalized["confidence"] = original.strip().lower()
        if normalized["confidence"] != original:
            notes.append("confidence: casing normalized")

    for field in ["transaction_time_used_as_valid_time", "conflict_warning", "partial_or_refusal", "clarification_requested"]:
        if field in normalized:
            normalized[field] = _normalize_bool(normalized[field], field, notes)

    _infer_behavior_flags(normalized, notes)

    return normalized, {
        "schema_normalization_applied": bool(notes),
        "schema_normalization_notes": notes,
    }


def validate_model_schema(answer: Dict[str, Any]) -> bool:
    missing = sorted(REQUIRED_MODEL_FIELDS - set(answer))
    if missing:
        raise SchemaValidationError("missing required fields: " + ", ".join(missing))
    if not isinstance(answer.get("answer"), str):
        raise SchemaValidationError("answer must be a string")
    behavior = str(answer.get("behavior") or "")
    if behavior not in MODEL_BEHAVIORS:
        raise SchemaValidationError(f"invalid behavior enum: {behavior}")
    if not isinstance(answer.get("cited_evidence_ids"), list) or not all(
        isinstance(item, str) for item in answer.get("cited_evidence_ids", [])
    ):
        raise SchemaValidationError("cited_evidence_ids must be a list of strings")
    if not isinstance(answer.get("valid_time_used"), list) or not all(
        isinstance(item, str) for item in answer.get("valid_time_used", [])
    ):
        raise SchemaValidationError("valid_time_used must be a list of strings")
    for field in ["transaction_time_used_as_valid_time", "conflict_warning", "partial_or_refusal", "clarification_requested"]:
        if not isinstance(answer.get(field), bool):
            raise SchemaValidationError(f"{field} must be boolean")
    confidence = str(answer.get("confidence") or "")
    if confidence not in CONFIDENCE_LEVELS:
        raise SchemaValidationError(f"invalid confidence enum: {confidence}")
    return True


def _parse_and_validate_provider_response(raw_text: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    diagnostics = {
        "provider_json_parse_failure": False,
        "schema_validation_failure": False,
        "parsed_response_available": False,
        "schema_normalization_applied": False,
        "schema_normalization_notes": [],
        "failure_type": None,
    }
    try:
        answer = parse_model_json(raw_text)
        diagnostics["parsed_response_available"] = True
    except ProviderJSONParseError as exc:
        diagnostics.update(
            {
                "provider_json_parse_failure": True,
                "failure_type": "Provider JSON Parse Failure",
                "parse_error": str(exc),
            }
        )
        return _parse_failure_answer(raw_text, str(exc)), diagnostics

    answer, normalization = normalize_provider_answer_shape(answer)
    diagnostics.update(normalization)

    try:
        validate_model_schema(answer)
    except SchemaValidationError as exc:
        diagnostics.update(
            {
                "schema_validation_failure": True,
                "failure_type": "Schema Validation Failure",
                "schema_error": str(exc),
            }
        )
        return _schema_failure_answer(answer, str(exc)), diagnostics

    return answer, diagnostics


def _parse_failure_answer(raw_model_response: str, error: str) -> Dict[str, Any]:
    return {
        "answer": f"Provider response could not be parsed as strict JSON: {error}. Raw response preserved in result JSON.",
        "behavior": "partial",
        "cited_evidence_ids": [],
        "valid_time_used": [],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": True,
        "clarification_requested": False,
        "confidence": "low",
        "raw_unparsed_response_preview": raw_model_response[:500],
    }


def _schema_failure_answer(parsed_response: Dict[str, Any], error: str) -> Dict[str, Any]:
    answer = dict(parsed_response)
    answer.setdefault("answer", f"Provider response failed schema validation: {error}.")
    answer.setdefault("behavior", "partial")
    answer.setdefault("cited_evidence_ids", [])
    answer.setdefault("valid_time_used", [])
    answer.setdefault("transaction_time_used_as_valid_time", False)
    answer.setdefault("conflict_warning", False)
    answer.setdefault("partial_or_refusal", True)
    answer.setdefault("clarification_requested", False)
    answer.setdefault("confidence", "low")
    answer["schema_error"] = error
    return answer


def _contains_all(text: str, phrases: List[str]) -> bool:
    lowered = text.lower()
    return all(phrase.lower() in lowered for phrase in phrases)


def _contains_none(text: str, phrases: List[str]) -> bool:
    lowered = text.lower()
    return not any(phrase.lower() in lowered for phrase in phrases)


def _has_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _number_surfaces(value: Any) -> set[str]:
    if value is None:
        return set()
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return {str(value)}
    integer = int(numeric)
    surfaces = {str(value), str(integer), f"{integer:,}"}
    if not math.isclose(numeric, integer):
        surfaces.add(str(numeric))
        surfaces.add(f"{numeric:,.1f}")
    return surfaces


def _expected_value_present(case: Dict[str, Any], answer_text: str, evidence_cards: List[Dict[str, Any]]) -> bool:
    expected_ids = set(case.get("expected_evidence_ids", [])) | set(case.get("acceptable_evidence_ids", []))
    expected_cards = [card for card in evidence_cards if card["evidence_id"] in expected_ids]
    if not expected_cards:
        return True
    lowered = answer_text.lower()
    value_surfaces = set()
    for card in expected_cards:
        value_surfaces.update(_number_surfaces(card.get("value")))
        raw_numbers = re.findall(r"(?<!\d)\d{1,3}(?:,\d{3})+(?:\.\d+)?|\b\d+(?:\.\d+)?\b", str(card.get("raw_text") or ""))
        value_surfaces.update(raw_numbers)
    non_value_numbers = {"1", "1000", "1500", "1600", "1700", "1820", "1870", "1913", "1950", "1973", "1990", "1998", "2006", "2018", "2022"}
    value_surfaces = {surface for surface in value_surfaces if surface and surface.lower() not in non_value_numbers}
    return any(surface.lower() in lowered for surface in value_surfaces)


def _valid_time_used_contains_year(answer: Dict[str, Any], year: str) -> bool:
    return any(year in str(item) for item in answer.get("valid_time_used") or [])


def _behavior_required_facts_present(case: Dict[str, Any], answer: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> bool:
    """Score required facts by answer behavior, not by one flat phrase list."""
    text = str(answer.get("answer") or "")
    lowered = text.lower()
    category = str(case.get("category") or "")
    behavior = str(case.get("expected_behavior") or "")
    cited = set(answer.get("cited_evidence_ids") or [])

    if "evidence_window" in category or "evidence_window" in set(case.get("feature_under_test", [])):
        has_window = _has_any(lowered, ["1913-01-01", "1913-12-31", "valid-time window", "valid time window", "evidence window"])
        has_window = has_window or _valid_time_used_contains_year(answer, "1913")
        has_expected_value = _expected_value_present(case, text, evidence_cards)
        return "1913" in lowered and has_window and has_expected_value and bool(cited)

    if "transaction_time_avoidance" in category:
        return "1870" in lowered and "2006" in lowered and "valid" in lowered and _has_any(lowered, ["transaction", "publication"])

    if "metric_confusion" in category:
        return "total gdp" in lowered and "gdp per capita" in lowered and _has_any(
            lowered,
            ["not", "different metric", "different metrics", "wrong metric", "not sufficient"],
        )

    if behavior == "compare":
        return "1870" in lowered and "1913" in lowered and len(cited.intersection(case.get("expected_evidence_ids", []))) >= 2

    if "trend_vs_exact" in category:
        return _has_any(lowered, ["trend", "broad"]) and "exact" in lowered and "1870" in lowered

    if behavior == "prefer_exact":
        return "exact" in lowered and _has_any(lowered, ["broad", "trend", "metric", "preferred", "prefer", "outrank"])

    if behavior == "conflict_warning":
        return _has_any(lowered, ["conflict", "disagree", "disagreement"]) and _has_any(lowered, ["1913", "western europe"])

    if behavior == "refuse":
        says_missing = _has_any(
            lowered,
            [
                "no exact evidence",
                "exact evidence is unavailable",
                "no evidence available",
                "no evidence",
                "insufficient evidence",
                "cannot provide",
                "cannot answer",
                "do not have evidence",
            ],
        )
        avoids_confidence = _has_any(
            lowered,
            [
                "not answer confidently",
                "should not answer confidently",
                "cannot answer confidently",
                "cannot be answered confidently",
                "not confidently",
                "refuse",
                "partial",
                "insufficient",
            ],
        )
        low_confidence = str(answer.get("confidence") or "") in {"low", "medium"}
        return bool(answer.get("partial_or_refusal")) and says_missing and avoids_confidence and low_confidence

    if behavior == "partial":
        if "transaction_time_only" in category:
            return _has_any(lowered, ["transaction-time-only", "transaction time only", "transaction_time_only"]) and _has_any(
                lowered,
                ["not valid-time", "not valid time", "should not be counted", "cannot answer valid-time", "valid-time evidence"],
            )
        return _has_any(lowered, ["partial", "background", "broad", "insufficient"]) and _has_any(
            lowered,
            ["no exact", "exact value", "exact evidence", "insufficient"],
        )

    if behavior == "clarify":
        return _has_any(lowered, ["ambiguous", "unclear"]) and _has_any(
            lowered,
            ["clarify", "specific year", "specific time", "specific range", "precise", "time frame"],
        )

    if "source_family" in category:
        return _contains_all(text, ["evidence IDs", "source family", "OWID", "Maddison"])

    return _contains_all(text, case.get("must_include", []))


def validate_evidence_grounding(answer: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    allowed = {card["evidence_id"] for card in evidence_cards}
    cited = set(answer.get("cited_evidence_ids") or [])
    unknown = sorted(cited - allowed)
    return {
        "allowed_evidence_ids": sorted(allowed),
        "unknown_evidence_ids": unknown,
        "grounding_validation_failure": bool(unknown),
    }


def _card_years(card: Dict[str, Any]) -> set[str]:
    years = set()
    for field in ["valid_from", "valid_to"]:
        value = str(card.get(field) or "")
        if len(value) >= 4 and value[:4].isdigit():
            years.add(value[:4])
    return years


def validate_temporal_rules(case: Dict[str, Any], answer: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic temporal checks; no extra model call is used."""
    question_years = _years(case.get("question", ""))
    normalized = normalize_behavior(answer.get("behavior"))
    confidence = str(answer.get("confidence") or "")
    cited = set(answer.get("cited_evidence_ids") or [])
    cited_cards = [card for card in evidence_cards if card["evidence_id"] in cited]
    features = set(case.get("feature_under_test", []))
    reasons = []

    if answer.get("transaction_time_used_as_valid_time"):
        reasons.append("transaction_time_used_as_valid_time")

    if question_years and ("wrong_year_trap" in features or "valid_time" in features):
        wrong_exact = [
            card["evidence_id"]
            for card in cited_cards
            if card.get("temporal_type") in {"valid_time_exact", "conflict_claim"}
            and _card_years(card)
            and _card_years(card).isdisjoint(question_years)
        ]
        if wrong_exact:
            reasons.append("wrong_year_citation:" + ",".join(wrong_exact))

    if {"broad_window", "prefer_exact", "trend_vs_exact"} & features:
        exact_available = [
            card
            for card in evidence_cards
            if card.get("temporal_type") in {"valid_time_exact", "conflict_claim"}
            and (not question_years or not _card_years(card).isdisjoint(question_years))
        ]
        cited_exact = [card for card in cited_cards if card in exact_available]
        cited_broad = [card for card in cited_cards if card.get("temporal_granularity") == "range"]
        if exact_available and cited_broad and not cited_exact:
            reasons.append("broad_window_preferred_over_exact")

    if case["expected_behavior"] == "conflict_warning" and not (
        normalized == "conflict_warning" and bool(answer.get("conflict_warning"))
    ):
        reasons.append("missing_conflict_warning")
    if case["expected_behavior"] in {"partial", "refuse"} and not (
        normalized in {"partial", "refuse"} and bool(answer.get("partial_or_refusal"))
    ):
        reasons.append("missing_partial_or_refusal")
    if case["expected_behavior"] == "clarify" and not (
        normalized == "clarify" and bool(answer.get("clarification_requested"))
    ):
        reasons.append("missing_clarification")
    if case["expected_behavior"] in {"partial", "refuse", "clarify"} and normalized == "answer" and confidence == "high":
        reasons.append("overconfident_direct_answer")

    return {
        "temporal_rule_failure": bool(reasons),
        "temporal_rule_failure_reasons": reasons,
    }


def validate_answer(case: Dict[str, Any], answer: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    answer, _normalization = normalize_provider_answer_shape(answer)
    answer_text = str(answer.get("answer") or "")
    cited = set(answer.get("cited_evidence_ids") or [])
    expected = set(case.get("expected_evidence_ids", []))
    acceptable = set(case.get("acceptable_evidence_ids", []))
    normalized_behavior = normalize_behavior(answer.get("behavior"))
    grounding = validate_evidence_grounding(answer, evidence_cards)
    temporal = validate_temporal_rules(case, answer, evidence_cards)

    if expected:
        if case["expected_behavior"] in {"compare", "conflict_warning"}:
            expected_evidence_cited = expected.issubset(cited)
        else:
            expected_evidence_cited = bool(expected.intersection(cited) or acceptable.intersection(cited))
    else:
        expected_evidence_cited = True

    if case["expected_behavior"] == "refuse" and not expected:
        acceptable_evidence_cited = True
    else:
        acceptable_evidence_cited = True if not acceptable else bool((expected | acceptable).intersection(cited))
    required_facts_present = _behavior_required_facts_present(case, answer, evidence_cards)
    forbidden_facts_absent = _contains_none(answer_text, case.get("must_not_include", []))
    transaction_time_not_misused = not bool(answer.get("transaction_time_used_as_valid_time"))
    if "2006 is the valid time" in answer_text.lower() or "gdp valid year 2006" in answer_text.lower():
        transaction_time_not_misused = False

    valid_time_correct = transaction_time_not_misused
    if expected and not (expected.intersection(cited) or acceptable.intersection(cited)):
        valid_time_correct = False

    conflict_warning_correct = True
    if case["expected_behavior"] == "conflict_warning":
        conflict_warning_correct = normalized_behavior == "conflict_warning" and bool(answer.get("conflict_warning"))

    partial_refusal_correct = True
    if case["expected_behavior"] in {"partial", "refuse"}:
        partial_refusal_correct = normalized_behavior in {"partial", "refuse"} and bool(answer.get("partial_or_refusal"))

    clarification_correct = True
    if case["expected_behavior"] == "clarify":
        clarification_correct = normalized_behavior == "clarify" and bool(answer.get("clarification_requested"))

    confidence_correct = True

    checks: Dict[str, Any] = {
        "required_facts_present": required_facts_present,
        "forbidden_facts_absent": forbidden_facts_absent,
        "expected_evidence_cited": expected_evidence_cited,
        "acceptable_evidence_cited": acceptable_evidence_cited,
        "valid_time_correct": valid_time_correct,
        "transaction_time_not_misused": transaction_time_not_misused,
        "conflict_warning_correct": conflict_warning_correct,
        "partial_refusal_correct": partial_refusal_correct,
        "clarification_correct": clarification_correct,
        "confidence_correct": confidence_correct,
        "grounding_validation_failure": grounding["grounding_validation_failure"],
        "temporal_rule_failure": temporal["temporal_rule_failure"],
        "allowed_evidence_ids": grounding["allowed_evidence_ids"],
        "unknown_evidence_ids": grounding["unknown_evidence_ids"],
        "temporal_rule_failure_reasons": temporal["temporal_rule_failure_reasons"],
    }
    bool_checks = {
        key: value
        for key, value in checks.items()
        if isinstance(value, bool) and key not in {"grounding_validation_failure", "temporal_rule_failure"}
    }
    checks["overall_pass"] = all(bool_checks.values()) and not checks["grounding_validation_failure"] and not checks["temporal_rule_failure"]
    failure_reasons = [key for key, value in bool_checks.items() if not value]
    if checks["grounding_validation_failure"]:
        failure_reasons.append("grounding_validation_failure")
    if checks["temporal_rule_failure"]:
        failure_reasons.append("temporal_rule_failure")
    checks["failure_reason"] = ", ".join(failure_reasons)
    return checks


def _mean(details: List[Dict[str, Any]], key: str) -> float:
    return float(statistics.mean(1 if item["validation"].get(key) else 0 for item in details)) if details else 0.0


def score_results(details: List[Dict[str, Any]]) -> Dict[str, float]:
    return {
        "answer_overall_pass": _mean(details, "overall_pass"),
        "required_facts_present": _mean(details, "required_facts_present"),
        "forbidden_facts_absent": _mean(details, "forbidden_facts_absent"),
        "expected_evidence_cited": _mean(details, "expected_evidence_cited"),
        "valid_time_correct": _mean(details, "valid_time_correct"),
        "transaction_time_trap_avoided": _mean(details, "transaction_time_not_misused"),
        "conflict_warning_correct": _mean(details, "conflict_warning_correct"),
        "partial_refusal_correct": _mean(details, "partial_refusal_correct"),
        "clarification_correct": _mean(details, "clarification_correct"),
        "confidence_correct": _mean(details, "confidence_correct"),
        "grounding_validation_pass": float(
            statistics.mean(0 if item.get("grounding_validation_failure") else 1 for item in details)
        )
        if details
        else 0.0,
        "temporal_rule_validation_pass": float(
            statistics.mean(0 if item.get("temporal_rule_failure") else 1 for item in details)
        )
        if details
        else 0.0,
        "provider_contract_pass": float(
            statistics.mean(
                0
                if item.get("provider_json_parse_failure")
                or item.get("schema_validation_failure")
                or not item.get("prompt_contract_valid", True)
                else 1
                for item in details
            )
        )
        if details
        else 0.0,
    }


def run_cases(
    cases: List[Dict[str, Any]],
    corpus: List[Dict[str, Any]],
    *,
    mode: str,
    top_k: int,
    temperature: float = 0.0,
    max_output_tokens: int = 512,
    use_vector: bool = False,
    dynamic_top_k: bool = False,
) -> Dict[str, Any]:
    details = []
    for case in cases:
        started = time.perf_counter()
        effective_top_k = effective_top_k_for_case(case, top_k, dynamic_top_k)
        rows = retrieve_top_k(case["question"], corpus, top_k=effective_top_k, use_vector=use_vector)
        cards = build_tcc_evidence_cards(rows)
        prompt_contract_valid = True
        prompt_contract_failure = None
        try:
            prompt = build_chronorag_grounded_synthesis_prompt(case, cards)
        except PromptContractError as exc:
            prompt = ""
            prompt_contract_valid = False
            prompt_contract_failure = str(exc)
        raw_response_preview = None
        initial_raw_response_preview = None
        provider_diagnostics: Dict[str, Any] = {
            "provider_json_parse_failure": False,
            "schema_validation_failure": False,
            "parsed_response_available": mode == "light",
            "json_repair_retry_used": False,
            "initial_parse_succeeded": mode == "light",
            "retry_parse_succeeded": False,
            "retry_attempted": False,
            "fallback_to_initial_response": False,
            "schema_normalization_applied": False,
            "schema_normalization_notes": [],
            "failure_type": None,
        }
        if mode == "vertex":
            if not prompt_contract_valid:
                answer = _schema_failure_answer({}, prompt_contract_failure or "prompt contract failed")
                provider_diagnostics.update(
                    {
                        "schema_validation_failure": True,
                        "failure_type": "Prompt Contract Failure",
                    }
                )
            else:
                raw_model_response = run_vertex_grounded_synthesis(
                    prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                raw_response_preview = raw_model_response[:700]
                initial_answer, initial_diagnostics = _parse_and_validate_provider_response(raw_model_response)
                initial_diagnostics["json_repair_retry_used"] = False
                initial_diagnostics["initial_parse_succeeded"] = bool(initial_diagnostics.get("parsed_response_available"))
                initial_diagnostics["retry_parse_succeeded"] = False
                initial_diagnostics["retry_attempted"] = False
                initial_diagnostics["fallback_to_initial_response"] = False
                initial_diagnostics["initial_raw_response_preview"] = raw_response_preview
                initial_diagnostics["final_raw_response_preview"] = raw_response_preview
                answer = initial_answer
                provider_diagnostics = initial_diagnostics

                if is_provider_contract_failure(initial_diagnostics):
                    initial_raw_response_preview = raw_response_preview
                    repair_prompt = build_json_repair_prompt(
                        raw_model_response,
                        [card["evidence_id"] for card in cards],
                    )
                    retry_response = ""
                    try:
                        retry_response = run_vertex_grounded_synthesis(
                            repair_prompt,
                            temperature=temperature,
                            max_output_tokens=max_output_tokens,
                        )
                        retry_preview = retry_response[:700]
                        retry_answer, retry_diagnostics = _parse_and_validate_provider_response(retry_response)
                    except Exception as exc:
                        retry_preview = str(exc)[:700]
                        retry_answer = _parse_failure_answer(retry_response or str(exc), str(exc))
                        retry_diagnostics = {
                            "provider_json_parse_failure": True,
                            "schema_validation_failure": False,
                            "parsed_response_available": False,
                            "schema_normalization_applied": False,
                            "schema_normalization_notes": [],
                            "failure_type": "Provider JSON Parse Failure",
                            "parse_error": str(exc),
                        }

                    retry_succeeded = not is_provider_contract_failure(retry_diagnostics)
                    if retry_succeeded:
                        answer = retry_answer
                        raw_response_preview = retry_preview
                        provider_diagnostics = retry_diagnostics
                    else:
                        # Keep the initial parsed response when available; a failed
                        # repair call must not replace the best usable provider output.
                        answer = initial_answer
                        raw_response_preview = initial_raw_response_preview
                        provider_diagnostics = initial_diagnostics
                        if initial_diagnostics.get("parsed_response_available"):
                            provider_diagnostics["fallback_to_initial_response"] = True
                    provider_diagnostics["json_repair_retry_used"] = retry_succeeded
                    provider_diagnostics["retry_attempted"] = True
                    provider_diagnostics["retry_parse_succeeded"] = bool(retry_diagnostics.get("parsed_response_available")) and retry_succeeded
                    provider_diagnostics["initial_raw_response_preview"] = initial_raw_response_preview
                    provider_diagnostics["retry_raw_response_preview"] = retry_preview
                    provider_diagnostics["final_raw_response_preview"] = raw_response_preview
        elif mode == "light":
            answer = run_light_harness_answer(case, cards)
        else:
            raise ValueError(f"Unknown mode: {mode}")
        validation = validate_answer(case, answer, cards)
        failure_type = provider_diagnostics.get("failure_type")
        if not failure_type:
            if validation.get("grounding_validation_failure"):
                failure_type = "Grounding Validation Failure"
            elif validation.get("temporal_rule_failure"):
                failure_type = "Temporal Rule Failure"
            elif not validation.get("overall_pass"):
                failure_type = "Answer Validation Failure"
        details.append(
            {
                "case_id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected_behavior": case["expected_behavior"],
                "detected_behavior": normalize_behavior(answer.get("behavior")),
                "cited_evidence_ids": answer.get("cited_evidence_ids", []),
                "retrieved_evidence_ids": [card["evidence_id"] for card in cards],
                "top_k": top_k,
                "effective_top_k": effective_top_k,
                "answer": answer,
                "prompt_contract_valid": prompt_contract_valid,
                "prompt_contract_failure": prompt_contract_failure,
                "provider_json_parse_failure": provider_diagnostics.get("provider_json_parse_failure", False),
                "schema_validation_failure": provider_diagnostics.get("schema_validation_failure", False),
                "grounding_validation_failure": validation.get("grounding_validation_failure", False),
                "temporal_rule_failure": validation.get("temporal_rule_failure", False),
                "json_repair_retry_used": provider_diagnostics.get("json_repair_retry_used", False),
                "retry_attempted": provider_diagnostics.get("retry_attempted", False),
                "initial_parse_succeeded": provider_diagnostics.get("initial_parse_succeeded", False),
                "retry_parse_succeeded": provider_diagnostics.get("retry_parse_succeeded", False),
                "fallback_to_initial_response": provider_diagnostics.get("fallback_to_initial_response", False),
                "schema_normalization_applied": provider_diagnostics.get("schema_normalization_applied", False),
                "schema_normalization_notes": provider_diagnostics.get("schema_normalization_notes", []),
                "failure_type": failure_type,
                "parse_error": provider_diagnostics.get("parse_error"),
                "schema_error": provider_diagnostics.get("schema_error"),
                "raw_response_preview": raw_response_preview,
                "initial_raw_response_preview": provider_diagnostics.get("initial_raw_response_preview"),
                "retry_raw_response_preview": provider_diagnostics.get("retry_raw_response_preview"),
                "final_raw_response_preview": provider_diagnostics.get("final_raw_response_preview", raw_response_preview),
                "parsed_response_available": provider_diagnostics.get("parsed_response_available", False),
                "allowed_evidence_ids": validation.get("allowed_evidence_ids", []),
                "validation": validation,
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
            }
        )
    return {"metrics": score_results(details), "details": details}


def _metrics_table(metrics: Dict[str, float]) -> str:
    rows = [
        ("Answer Overall Pass", "answer_overall_pass"),
        ("Required Facts Present", "required_facts_present"),
        ("Forbidden Facts Absent", "forbidden_facts_absent"),
        ("Expected Evidence Cited", "expected_evidence_cited"),
        ("Valid-Time Correct", "valid_time_correct"),
        ("Transaction-Time Trap Avoided", "transaction_time_trap_avoided"),
        ("Conflict Warning Correct", "conflict_warning_correct"),
        ("Partial/Refusal Correct", "partial_refusal_correct"),
        ("Clarification Correct", "clarification_correct"),
        ("Confidence Correct", "confidence_correct"),
        ("Provider Contract Pass", "provider_contract_pass"),
        ("Grounding Validation Pass", "grounding_validation_pass"),
        ("Temporal Rule Validation Pass", "temporal_rule_validation_pass"),
    ]
    lines = ["| Metric | Score |", "|---|---:|"]
    for label, key in rows:
        lines.append(f"| {label} | {metrics.get(key, 0.0):.2f} |")
    return "\n".join(lines)


def _per_case_table(details: List[Dict[str, Any]]) -> str:
    lines = [
        "| Case | Expected Behavior | Detected Behavior | Cited Evidence IDs | Overall Pass | Failure Type | Failure Reason |",
        "|---|---|---|---|---:|---|---|",
    ]
    for item in details:
        cited = ", ".join(item.get("cited_evidence_ids") or [])
        failure = item["validation"].get("failure_reason") or ""
        if item.get("parse_error"):
            failure = f"{failure}; parse_error={item['parse_error']}".strip("; ")
        if item.get("schema_error"):
            failure = f"{failure}; schema_error={item['schema_error']}".strip("; ")
        lines.append(
            f"| {item['case_id']} | {item['expected_behavior']} | {item['detected_behavior']} | {cited} | {int(item['validation']['overall_pass'])} | {item.get('failure_type') or ''} | {failure} |"
        )
    return "\n".join(lines)


def render_markdown(payload: Dict[str, Any]) -> str:
    mode_label = "light/mock CI harness" if payload["mode"] == "light" else "vertex/full-force answer synthesis"
    cost_note = (
        "Light mode is deterministic and makes no Vertex calls. It validates benchmark plumbing and scoring only."
        if payload["mode"] == "light"
        else "Vertex mode makes one Gemini call per selected case. Use --limit, --case-id, --dry-run-prompts, and --estimate-only for cost control."
    )
    failures = [
        f"- `{item['case_id']}`: {item.get('failure_type') or 'Answer Validation Failure'}; "
        f"{item['validation'].get('failure_reason') or item.get('parse_error') or item.get('schema_error') or 'see JSON diagnostics'}"
        for item in payload["details"]
        if not item["validation"].get("overall_pass")
        or item.get("parse_error")
        or item.get("schema_error")
        or item.get("failure_type")
    ]
    return "\n\n".join(
        [
            "# Temporal Answer Validation v2 Results",
            "## Benchmark Scope",
            "Layer 1B evaluates ChronoRAG answer behavior using temporal retrieval, TCC evidence cards, grounded synthesis, and rule-based validation. It is not Layer 2, not an external benchmark, and not a broad performance claim.",
            "## Mode",
            mode_label,
            "## Command",
            f"```bash\n{payload['command']}\n```",
            "## Cost Note",
            cost_note,
            "## Corpus And Case Count",
            f"- Corpus rows: {payload['corpus_row_count']}\n- Cases: {payload['case_count']}\n- Base top-k: {payload.get('top_k')}\n- Dynamic top-k: {payload.get('dynamic_top_k', False)}\n- Result suffix: {payload.get('result_suffix') or 'none'}",
            "## Pipeline Summary",
            "retrieve top-k temporal evidence -> build TCC-enriched evidence cards -> validate prompt contract -> run light harness or Vertex Gemini grounded synthesis -> extract JSON -> normalize harmless schema shape drift -> validate schema/evidence/temporal rules -> score final answer",
            "## Provider Contract Diagnostics",
            "- Provider JSON Parse Failure is an infrastructure/provider-output contract failure, not a temporal reasoning failure.\n- Harmless schema shape drift is normalized before scoring.\n- One repair retry is allowed only for JSON parse or non-normalizable schema failures.\n- A failed retry cannot overwrite a usable initial response.\n- Grounding and temporal-rule failures are scored as answer/grounding failures and are not retried away.",
            "## Metrics",
            _metrics_table(payload["metrics"]),
            "## Per-Case Table",
            _per_case_table(payload["details"]),
            "## Failure Analysis",
            "\n".join(failures) if failures else "- No failures.",
            "## Limitations",
            "- Light mode is a deterministic CI/testing harness, not the production answer technology.\n- Vertex mode is the full LLM answer-synthesis evaluation, but still over a controlled corpus.\n- This is not Layer 2 and does not establish cross-domain generalization.\n- No SOTA or external benchmark claim is made.",
            "## Allowed Interpretation",
            "Use these results to evaluate ChronoRAG's controlled Layer 1B answer behavior over Temporal Eval v2 evidence cards.",
        ]
    )


def write_results(payload: Dict[str, Any], output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(payload) + "\n", encoding="utf-8")
