from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from app.services.answer_service import answer


QUESTIONS = [
    "Western Europe GDP per capita in 1870 1990 international dollars",
    "Western Europe GDP per capita in 1913 1990 international dollars",
    "For the 1870 valid window return Western Europe GDP per capita and ignore 1913",
    "Western Europe GDP per capita increased between 1870 and 1913",
    "publication released 2006 but valid-time answer should not use 2006 as GDP year",
]


def _evidence_summary(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    card = response.get("attribution_card", {})
    summary = []
    for source in card.get("sources", [])[:3]:
        summary.append(
            {
                "uri": source.get("uri"),
                "score": source.get("score"),
                "interval": source.get("interval"),
                "quote": (source.get("quote") or "").strip()[:220],
            }
        )
    return summary


def main() -> None:
    for question in QUESTIONS:
        started = time.perf_counter()
        response = answer(question, None, "INTELLIGENT", "valid")
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        payload = {
            "question": question,
            "retrieved_evidence": _evidence_summary(response),
            "provider_answer": response.get("answer"),
            "fallback_or_debug": {
                "evidence_only": response.get("evidence_only"),
                "reason": response.get("reason"),
                "degraded": response.get("controller_stats", {}).get("degraded"),
                "provider_debug_in_answer": "Provider debug:" in (response.get("answer") or ""),
            },
            "latency_ms": latency_ms,
        }
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
