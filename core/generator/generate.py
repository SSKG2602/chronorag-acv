"""Answer generation orchestration for ChronoRAG.

This module turns retrieval output into final structured answers. It constructs
role-tagged chat messages, selects the most appropriate language model backend,
and enforces deterministic JSON output with validation. When validation fails or
the LLM is unreachable we fall back to an evidence digest.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.utils.chrono_reducer import ChronoPassage
from app.utils.time_windows import TimeWindow
from core.generator.llm_loader import load_backend
from core.generator.prompts import build_messages

# Separator injected into the prompt; we cut any text that follows this marker.
STOP_MARKER = "<|ATTR_CARD|>"
logger = logging.getLogger(__name__)


def _format_passage_line(idx: int, passage: ChronoPassage) -> str:
    text = passage.text.strip().replace("\n", " ")
    if len(text) > 220:
        text = text[:220].rsplit(" ", 1)[0] + "…"
    window = f"{passage.valid_window.start.date()} → {passage.valid_window.end.date()}"
    source = passage.uri
    return f"{idx}. {text} (Window: {window}; Source: {source})"


def _fallback_response(query: str, evidence: List[ChronoPassage]) -> str:
    """Return a deterministic message when no LLM backend is reachable."""
    top = evidence[0] if evidence else None
    if not top:
        return f"No direct in-window evidence found for: {query}\n\n{STOP_MARKER}"
    lines = [
        "ChronoGuard fallback mode — unable to reach the language model, supplying evidence digest.",
        f"Query: {query}",
        "Key evidence:",
    ]
    for idx, passage in enumerate(evidence[:5], 1):
        lines.append(_format_passage_line(idx, passage))
    lines.append("Use the cited passages to construct the final narrative.")
    return "\n".join(lines) + "\n\n" + STOP_MARKER


def _inject_json_instructions(messages: List[dict]) -> None:
    """Append strict JSON formatting instructions to the final user message."""
    json_instruction = (
        "Respond ONLY with minified JSON matching this schema:\n"
        '{"range":{"low":number,"high":number,"most_likely":number,"unit":"1990_intl_usd"},'
        '"bullets":[{"summary":string,"source":string},{"summary":string,"source":string}]}\n'
        "- Use floats for numeric fields and ensure low <= most_likely <= high.\n"
        "- Summaries must mention the referenced year (YYYY) and stay within 20 words.\n"
        "- Sources must be concise citations or URIs.\n"
        "- Do not emit any text outside the JSON object."
    )
    messages[-1]["content"] = f"{messages[-1]['content']}\n\n{json_instruction}"


def _validate_payload(payload: Dict[str, Any]) -> List[str]:
    """Validate structured JSON payload and return issues (empty when valid)."""
    issues: List[str] = []
    value_range = payload.get("range")
    bullets = payload.get("bullets")

    if not isinstance(value_range, dict):
        issues.append("range field missing or not an object")
    else:
        for key in ("low", "high", "most_likely"):
            val = value_range.get(key)
            if not isinstance(val, (int, float)):
                issues.append(f"{key} must be numeric")
        numeric_present = all(
            isinstance(value_range.get(key), (int, float)) for key in ("low", "high", "most_likely")
        )
        if numeric_present:
            low = float(value_range["low"])
            high = float(value_range["high"])
            most = float(value_range["most_likely"])
            if not (low <= most <= high):
                issues.append("most_likely must fall within [low, high]")
            if low < 10 or high > 20000:
                issues.append("values must stay within the 10-20000 band for 1990 intl$")
        unit = value_range.get("unit")
        if not isinstance(unit, str) or "1990" not in unit or "intl" not in unit.lower():
            issues.append("unit must specify 1990 international dollars")

    if not isinstance(bullets, list) or len(bullets) != 2:
        issues.append("exactly two bullets required")
    else:
        year_pattern = re.compile(r"\b(18\d{2}|190\d|191[0-3])\b")
        for idx, bullet in enumerate(bullets):
            if not isinstance(bullet, dict):
                issues.append(f"bullet {idx} must be an object")
                continue
            summary = bullet.get("summary")
            source = bullet.get("source")
            if not isinstance(summary, str) or not summary.strip():
                issues.append(f"bullet {idx} summary missing")
            else:
                words = summary.strip().split()
                if len(words) > 20:
                    issues.append(f"bullet {idx} summary exceeds 20 words")
                if not year_pattern.search(summary):
                    issues.append(f"bullet {idx} summary lacks year reference")
            if not isinstance(source, str) or not source.strip():
                issues.append(f"bullet {idx} source missing")
    return issues


def _run_structured_generation(
    backend,
    messages: List[dict],
    max_tokens: int,
    temperature: float,
    stop_list: List[str],
) -> Tuple[Optional[Dict[str, Any]], str, List[str]]:
    """Execute a generation attempt and return (payload, text, validation_issues)."""
    raw = backend.generate(messages, max_tokens=max_tokens, temperature=temperature, stop=stop_list)
    text = raw.split(STOP_MARKER)[0].strip()
    if not text:
        return None, text, ["empty response"]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to decode JSON response: %s", exc)
        return None, text, ["invalid JSON"]
    issues = _validate_payload(payload)
    if issues:
        return None, text, issues
    return payload, text, []


def generate_answer(
    query: str,
    mode: str,
    axis: str,
    window: TimeWindow,
    evidence: List[ChronoPassage],
    models_cfg: Dict,
    domain: str,
    window_kind: str,
) -> Tuple[str, int]:
    """Generate an answer string and a token estimate from supplied evidence."""
    llm_cfg = models_cfg.get("llm", {})
    prompt_limits = llm_cfg.get("prompt_limits", {})
    max_passages = prompt_limits.get("max_passages")
    snippet_chars = prompt_limits.get("snippet_chars", 180)
    if not isinstance(snippet_chars, int) or snippet_chars <= 0:
        snippet_chars = 180
    prompt_evidence = evidence
    if isinstance(max_passages, int) and max_passages > 0:
        prompt_evidence = evidence[:max_passages]

    stop_list = [STOP_MARKER]
    max_tokens = 512
    temperature = 0.15
    try:
        backend, backend_name = load_backend(llm_cfg)
        if backend_name == "local_hf":
            entry = llm_cfg.get("local_hf", {})
            stop_list = entry.get("stop", stop_list)
            max_tokens = entry.get("max_new_tokens", max_tokens)
            temperature = entry.get("temperature", temperature)
        elif backend_name == "lightning_ai":
            entry = llm_cfg.get("lightning_ai", {})
            stop_list = entry.get("stop", stop_list)
            max_tokens = entry.get("max_tokens", max_tokens)
            temperature = entry.get("temperature", temperature)
        elif backend_name == "openai_compat":
            entry = llm_cfg.get("openai_compat", {})
            stop_list = entry.get("stop", stop_list)
            max_tokens = entry.get("max_tokens", max_tokens)
            temperature = entry.get("temperature", temperature)
        elif backend_name == "llama_cpp":
            entry = llm_cfg.get("llama_cpp", {})
            stop_list = entry.get("stop", stop_list)
            max_tokens = entry.get("max_new_tokens", max_tokens)
            temperature = entry.get("temperature", temperature)
        elif backend_name == "ollama":
            entry = llm_cfg.get("ollama", {})
            stop_list = entry.get("stop", stop_list)
            max_tokens = entry.get("max_tokens", max_tokens)
            temperature = entry.get("temperature", temperature)

        payload: Optional[Dict[str, Any]] = None
        raw_text = ""
        issues: List[str] = []

        attempt_specs = [
            ("primary", prompt_evidence, snippet_chars),
        ]
        retry_evidence = prompt_evidence[: min(len(prompt_evidence), 8)]
        retry_snippet = min(snippet_chars, 100)
        if retry_evidence and retry_evidence != prompt_evidence:
            attempt_specs.append(("retry", retry_evidence, retry_snippet))

        for tag, attempt_evidence, attempt_snippet in attempt_specs:
            messages = build_messages(
                query,
                mode,
                axis,
                window,
                attempt_evidence,
                domain,
                window_kind,
                snippet_chars=attempt_snippet,
            )
            _inject_json_instructions(messages)
            payload, raw_text, issues = _run_structured_generation(
                backend,
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop_list=stop_list,
            )
            if payload is not None:
                break
            logger.warning("Structured generation %s attempt failed: %s", tag, issues)

        if payload is None:
            logger.warning("Structured generation failed after retries; using fallback digest")
            clipped = _fallback_response(query, evidence).split(STOP_MARKER)[0].strip()
            token_estimate = max(1, len(clipped.split()))
            return clipped, token_estimate

        final_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        token_estimate = max(1, len(final_text.split()))
        return final_text, token_estimate
    except Exception:
        logger.exception("LLM generation failed; returning evidence digest")
        clipped = _fallback_response(query, evidence).split(STOP_MARKER)[0].strip()
        token_estimate = max(1, len(clipped.split()))
        return clipped, token_estimate
