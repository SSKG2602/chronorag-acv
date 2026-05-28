from __future__ import annotations

import random
import time
from typing import Callable, TypeVar


T = TypeVar("T")


RETRYABLE_MARKERS = (
    "429",
    "resource exhausted",
    "resourceexhausted",
    "503",
    "service unavailable",
    "serviceunavailable",
    "stream removed",
    "tsi_data_corrupted",
    "ssl",
    "transport",
    "connection reset",
    "temporarily unavailable",
    "timeout",
    "timed out",
    "vertex response did not contain a json object",
    "vertex response contained incomplete json",
    "providerjsonerror",
)

NON_RETRYABLE_MARKERS = (
    "missing credentials",
    "application default credentials",
    "google_cloud_project",
    "google_cloud_location",
    "vertex_model_id",
    "permission denied",
    "unauthorized",
    "forbidden",
    "invalid argument",
    "prompt contract",
)


def is_retryable_vertex_error(exc: BaseException) -> bool:
    """Classify transient Vertex/provider transport failures without LLM calls."""
    message = f"{exc.__class__.__name__}: {exc}".lower()
    if any(marker in message for marker in NON_RETRYABLE_MARKERS):
        return False
    return any(marker in message for marker in RETRYABLE_MARKERS)


def call_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 5,
    base_sleep: float = 5.0,
    max_sleep: float = 90.0,
    jitter: bool = True,
    label: str = "",
) -> T:
    """Run a provider call with truncated exponential backoff for temporary overloads."""
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt >= attempts or not is_retryable_vertex_error(exc):
                raise
            sleep_seconds = min(max_sleep, base_sleep * (2 ** (attempt - 1)))
            if jitter:
                sleep_seconds *= random.uniform(0.75, 1.25)
            print(
                "[vertex-retry] "
                f"{label} attempt={attempt + 1} sleep={sleep_seconds:.1f}s "
                f"error={_short_error(exc)}",
                flush=True,
            )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    raise RuntimeError("unreachable retry state")


def _short_error(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    if not text:
        text = exc.__class__.__name__
    return text[:240]
