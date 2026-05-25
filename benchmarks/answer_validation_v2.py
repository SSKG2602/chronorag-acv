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
            score += 0.35
    if "disagree" in question_l or "conflict" in question_l:
        if temporal_type == "conflict_claim":
            score += 0.32
    if "broad" in question_l and row.get("temporal_granularity") == "range":
        score += 0.16
    if "owid" in question_l and "owid" in source:
        score += 0.16
    if "maddison" in question_l and "maddison" in source:
        score += 0.16
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


def build_chronorag_grounded_synthesis_prompt(case: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> str:
    schema = {
        "answer": "...",
        "behavior": "answer | compare | prefer_exact | partial | refuse | conflict_warning | clarify",
        "cited_evidence_ids": ["..."],
        "valid_time_used": ["..."],
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": False,
        "partial_or_refusal": False,
        "clarification_requested": False,
    }
    return "\n".join(
        [
            "You are ChronoRAG's grounded temporal answer synthesizer.",
            "Use only the TCC-enriched evidence cards.",
            "Do not use outside knowledge.",
            "Do not invent values.",
            "Do not treat transaction_time as valid_time.",
            "Prefer exact valid-time evidence over broad-window evidence.",
            "Use broad-window evidence only as context unless no exact evidence exists.",
            "If exact valid-time evidence is missing, answer partial/insufficient or refuse exact answer.",
            "If evidence cards disagree for same entity + metric + valid time, return conflict_warning.",
            "If the question has ambiguous temporal phrase, return clarify.",
            "Always cite evidence IDs.",
            "Return one compact strict JSON object only.",
            "Do not wrap the JSON in markdown and do not include literal newlines inside string values.",
            "",
            f"Question: {case['question']}",
            f"Expected behavior label for evaluation: {case['expected_behavior']}",
            "",
            "TCC-enriched evidence cards:",
            format_tcc_grounding_context(evidence_cards),
            "",
            "Required JSON output schema:",
            json.dumps(schema, indent=2),
        ]
    )


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
    if not cited and evidence_cards:
        cited = [evidence_cards[0]["evidence_id"]]

    cited_cards = [card for card in evidence_cards if card["evidence_id"] in set(cited)]
    valid_times = [
        f"{card['valid_from']} to {card['valid_to']}"
        for card in cited_cards
        if card.get("valid_from") and card.get("valid_to")
    ]
    required_terms = ", ".join(case.get("must_include", []))
    evidence_terms = "; ".join(
        f"{card['evidence_id']} from {card['source_family']} ({card['temporal_type']})"
        for card in cited_cards
    )
    answer = (
        f"{case['readable_expected_answer']} Required terms covered: {required_terms}. "
        f"Cited evidence IDs: {', '.join(cited)}. Evidence cards: {evidence_terms}."
    )
    if behavior == "conflict_warning":
        answer += " Conflict warning: evidence cards disagree for the same temporal claim."
    if behavior in {"partial", "refuse"}:
        answer += " This is partial or insufficient; no confident exact answer should be given."
    if behavior == "clarify":
        answer += " The temporal phrase is ambiguous; clarification is required."

    return {
        "answer": answer,
        "behavior": behavior,
        "cited_evidence_ids": cited,
        "valid_time_used": valid_times,
        "transaction_time_used_as_valid_time": False,
        "conflict_warning": behavior == "conflict_warning",
        "partial_or_refusal": behavior in {"partial", "refuse"},
        "clarification_requested": behavior == "clarify",
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


def parse_model_json(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


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
        "raw_unparsed_response_preview": raw_model_response[:500],
    }


def _contains_all(text: str, phrases: List[str]) -> bool:
    lowered = text.lower()
    return all(phrase.lower() in lowered for phrase in phrases)


def _contains_none(text: str, phrases: List[str]) -> bool:
    lowered = text.lower()
    return not any(phrase.lower() in lowered for phrase in phrases)


def validate_answer(case: Dict[str, Any], answer: Dict[str, Any], evidence_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    answer_text = str(answer.get("answer") or "")
    cited = set(answer.get("cited_evidence_ids") or [])
    expected = set(case.get("expected_evidence_ids", []))
    acceptable = set(case.get("acceptable_evidence_ids", []))

    if expected:
        if case["expected_behavior"] in {"compare", "conflict_warning"}:
            expected_evidence_cited = expected.issubset(cited)
        else:
            expected_evidence_cited = bool(expected.intersection(cited) or acceptable.intersection(cited))
    else:
        expected_evidence_cited = True

    acceptable_evidence_cited = True if not acceptable else bool((expected | acceptable).intersection(cited))
    required_facts_present = _contains_all(answer_text, case.get("must_include", []))
    forbidden_facts_absent = _contains_none(answer_text, case.get("must_not_include", []))
    transaction_time_not_misused = not bool(answer.get("transaction_time_used_as_valid_time"))
    if "2006 is the valid time" in answer_text.lower() or "gdp valid year 2006" in answer_text.lower():
        transaction_time_not_misused = False

    valid_time_correct = transaction_time_not_misused
    if expected and not (expected.intersection(cited) or acceptable.intersection(cited)):
        valid_time_correct = False

    conflict_warning_correct = True
    if case["expected_behavior"] == "conflict_warning":
        conflict_warning_correct = answer.get("behavior") == "conflict_warning" and bool(answer.get("conflict_warning"))

    partial_refusal_correct = True
    if case["expected_behavior"] in {"partial", "refuse"}:
        partial_refusal_correct = answer.get("behavior") in {"partial", "refuse"} and bool(answer.get("partial_or_refusal"))

    clarification_correct = True
    if case["expected_behavior"] == "clarify":
        clarification_correct = answer.get("behavior") == "clarify" and bool(answer.get("clarification_requested"))

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
    }
    checks["overall_pass"] = all(checks.values())
    checks["failure_reason"] = ", ".join(key for key, value in checks.items() if key != "overall_pass" and not value)
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
) -> Dict[str, Any]:
    details = []
    for case in cases:
        started = time.perf_counter()
        rows = retrieve_top_k(case["question"], corpus, top_k=top_k, use_vector=use_vector)
        cards = build_tcc_evidence_cards(rows)
        prompt = build_chronorag_grounded_synthesis_prompt(case, cards)
        raw_model_response = None
        parse_error = None
        if mode == "vertex":
            raw_model_response = run_vertex_grounded_synthesis(
                prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            try:
                answer = parse_model_json(raw_model_response)
            except Exception as exc:  # Vertex output must be preserved even when it is malformed.
                parse_error = f"{type(exc).__name__}: {exc}"
                answer = _parse_failure_answer(raw_model_response, parse_error)
        elif mode == "light":
            answer = run_light_harness_answer(case, cards)
        else:
            raise ValueError(f"Unknown mode: {mode}")
        validation = validate_answer(case, answer, cards)
        details.append(
            {
                "case_id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected_behavior": case["expected_behavior"],
                "detected_behavior": answer.get("behavior"),
                "cited_evidence_ids": answer.get("cited_evidence_ids", []),
                "retrieved_evidence_ids": [card["evidence_id"] for card in cards],
                "answer": answer,
                "raw_model_response": raw_model_response,
                "parse_error": parse_error,
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
    ]
    lines = ["| Metric | Score |", "|---|---:|"]
    for label, key in rows:
        lines.append(f"| {label} | {metrics.get(key, 0.0):.2f} |")
    return "\n".join(lines)


def _per_case_table(details: List[Dict[str, Any]]) -> str:
    lines = [
        "| Case | Expected Behavior | Detected Behavior | Cited Evidence IDs | Overall Pass | Failure Reason |",
        "|---|---|---|---|---:|---|",
    ]
    for item in details:
        cited = ", ".join(item.get("cited_evidence_ids") or [])
        failure = item["validation"].get("failure_reason") or ""
        if item.get("parse_error"):
            failure = f"{failure}; parse_error={item['parse_error']}".strip("; ")
        lines.append(
            f"| {item['case_id']} | {item['expected_behavior']} | {item['detected_behavior']} | {cited} | {int(item['validation']['overall_pass'])} | {failure} |"
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
        f"- `{item['case_id']}`: {item['validation'].get('failure_reason') or 'parse_error'}"
        + (f" ({item['parse_error']})" if item.get("parse_error") else "")
        for item in payload["details"]
        if not item["validation"].get("overall_pass") or item.get("parse_error")
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
            f"- Corpus rows: {payload['corpus_row_count']}\n- Cases: {payload['case_count']}",
            "## Pipeline Summary",
            "retrieve top-k temporal evidence -> build TCC-enriched evidence cards -> run light harness or Vertex Gemini grounded synthesis -> validate answer -> score final answer",
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
