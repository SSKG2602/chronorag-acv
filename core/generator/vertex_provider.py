"""Optional Vertex AI Gemini provider for grounded answer synthesis."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from app.utils.chrono_reducer import ChronoPassage
from app.utils.time_windows import TimeWindow


@dataclass(frozen=True)
class VertexProviderResult:
    """Result returned by the optional Vertex provider wrapper."""

    text: str
    provider_error: str | None = None
    debug: str | None = None

    @property
    def ok(self) -> bool:
        return self.provider_error is None and bool(self.text.strip())


def _format_evidence(evidence_items: Iterable[ChronoPassage]) -> str:
    lines = []
    for idx, item in enumerate(evidence_items, start=1):
        text = item.text.strip().replace("\n", " ")
        if len(text) > 700:
            text = text[:700].rsplit(" ", 1)[0] + "..."
        lines.append(
            "\n".join(
                [
                    f"[{idx}] Source: {item.uri}",
                    f"Valid window: {item.valid_window.start.date()} to {item.valid_window.end.date()}",
                    f"Authority: {item.authority:.3f}",
                    f"Units: {', '.join(item.units or []) or 'unknown'}",
                    f"Evidence: {text}",
                ]
            )
        )
    return "\n\n".join(lines)


def _format_temporal_context(temporal_context: Mapping[str, Any] | TimeWindow | None) -> str:
    if isinstance(temporal_context, TimeWindow):
        return f"Requested valid window: {temporal_context.start.date()} to {temporal_context.end.date()}"
    if isinstance(temporal_context, Mapping):
        parts = []
        for key in ("mode", "axis", "window_kind", "domain"):
            if key in temporal_context:
                parts.append(f"{key}: {temporal_context[key]}")
        window = temporal_context.get("window")
        if isinstance(window, TimeWindow):
            parts.append(f"requested window: {window.start.date()} to {window.end.date()}")
        return "; ".join(parts) or "No temporal context supplied."
    return "No temporal context supplied."


def _build_prompt(
    question: str,
    evidence_items: list[ChronoPassage],
    temporal_context: Mapping[str, Any] | TimeWindow | None,
) -> str:
    evidence_block = _format_evidence(evidence_items)
    if not evidence_block:
        evidence_block = "No retrieved evidence was supplied."
    return f"""You are ChronoRAG's grounded answer synthesizer.

Rules:
- Answer only using the supplied evidence.
- Do not use outside knowledge.
- Preserve temporal validity and mention the relevant valid-time window.
- Mention uncertainty when evidence is weak or incomplete.
- If supplied evidence conflicts, explain the conflict instead of forcing one answer.
- If evidence is insufficient, say the evidence is insufficient.
- Keep the answer concise and cite source numbers like [1].

Question:
{question}

Temporal context:
{_format_temporal_context(temporal_context)}

Retrieved evidence:
{evidence_block}

Grounded answer:"""


class VertexGeminiProvider:
    """Thin adapter around Vertex AI Gemini using Application Default Credentials."""

    def __init__(
        self,
        project: str | None = None,
        location: str | None = None,
        model_id: str | None = None,
    ) -> None:
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.model_id = model_id or os.getenv("VERTEX_MODEL_ID", "gemini-2.5-flash")

    def generate_grounded_answer(
        self,
        question: str,
        evidence_items: list[ChronoPassage],
        temporal_context: Mapping[str, Any] | TimeWindow | None,
        max_output_tokens: int = 512,
    ) -> VertexProviderResult:
        if not self.project:
            return VertexProviderResult(
                text="",
                provider_error="GOOGLE_CLOUD_PROJECT is required for Vertex provider mode.",
                debug="Set GOOGLE_CLOUD_PROJECT or run with CHRONORAG_LIGHT=1.",
            )

        try:
            import vertexai
            from vertexai.generative_models import GenerationConfig, GenerativeModel
        except Exception as exc:
            return VertexProviderResult(
                text="",
                provider_error=f"Vertex SDK import failed: {exc}",
                debug="Install optional provider dependencies with: pip install -r requirements-provider.txt",
            )

        try:
            vertexai.init(project=self.project, location=self.location)
            model = GenerativeModel(self.model_id)
            prompt = _build_prompt(question, evidence_items, temporal_context)
            response = model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=0.0,
                ),
            )
            text = (getattr(response, "text", "") or "").strip()
            if not text:
                return VertexProviderResult(
                    text="",
                    provider_error="Vertex provider returned an empty response.",
                    debug=f"model={self.model_id}; location={self.location}",
                )
            return VertexProviderResult(text=text)
        except Exception as exc:
            return VertexProviderResult(
                text="",
                provider_error=f"Vertex provider call failed: {exc}",
                debug=f"model={self.model_id}; project={self.project}; location={self.location}",
            )


def generate_grounded_answer(
    question: str,
    evidence_items: list[ChronoPassage],
    temporal_context: Mapping[str, Any] | TimeWindow | None,
    max_output_tokens: int = 512,
) -> VertexProviderResult:
    """Generate a grounded answer through Vertex AI Gemini, failing closed."""
    return VertexGeminiProvider().generate_grounded_answer(
        question=question,
        evidence_items=evidence_items,
        temporal_context=temporal_context,
        max_output_tokens=max_output_tokens,
    )
