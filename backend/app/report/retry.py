"""Shared retry helpers with exponential backoff and jitter.

Used by the Gemini author (longer backoff) and by builder-side YouTube /
Sheets API calls (short backoff). Only transient failures are retried;
permanent 4xx errors (auth, bad request, schema) fail immediately.
"""

from __future__ import annotations

import random
import sys
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

# ---- Gemini (author.py) ----------------------------------------------------
# Max attempts including the first try. Backoff between tries: 5s → 15s → 45s.
GEMINI_MAX_ATTEMPTS = 4
GEMINI_BACKOFF_BASE_S = 5.0
GEMINI_BACKOFF_FACTOR = 3.0

# ---- YouTube / Sheets API (builder.py) -------------------------------------
API_MAX_ATTEMPTS = 3
API_BACKOFF_BASE_S = 1.0
API_BACKOFF_FACTOR = 2.0


def _log(message: str) -> None:
    print(f"[retry] {message}", file=sys.stderr)


def _http_status(exc: BaseException) -> int | None:
    """Best-effort extract of an HTTP status code from common Google exceptions."""
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    resp = getattr(exc, "resp", None)
    if resp is not None:
        status = getattr(resp, "status", None)
        if isinstance(status, int):
            return status
        if isinstance(status, str) and status.isdigit():
            return int(status)
    return None


def is_retryable_http_status(status: int) -> bool:
    """True for rate-limit / transient server errors worth retrying."""
    return status in (429, 500, 502, 503, 504)


def is_retryable_api_error(exc: BaseException) -> bool:
    """Retry YouTube / Sheets failures that look transient."""
    if isinstance(exc, (TimeoutError, ConnectionError, BrokenPipeError)):
        return True
    # googleapiclient / urllib style
    status = _http_status(exc)
    if status is not None:
        return is_retryable_http_status(status)
    name = type(exc).__name__
    if name in {"SSLError", "RemoteDisconnected", "ProtocolError"}:
        return True
    # google-auth transport sometimes wraps these
    if "timed out" in str(exc).lower() or "temporarily" in str(exc).lower():
        return True
    return False


def is_retryable_gemini_error(exc: BaseException) -> bool:
    """Retry Gemini 503 / 429 / connection blips; skip permanent 4xx."""
    if isinstance(exc, (TimeoutError, ConnectionError, BrokenPipeError)):
        return True
    status = _http_status(exc)
    if status is not None:
        if is_retryable_http_status(status):
            return True
        # Permanent client errors (auth, bad schema, etc.) — do not retry.
        if 400 <= status < 500:
            return False
    # google-genai ServerError / ClientError often embed the status in the message.
    text = str(exc)
    for code in (429, 500, 502, 503, 504):
        if str(code) in text:
            return True
    lowered = text.lower()
    if any(
        token in lowered
        for token in ("unavailable", "high demand", "resource exhausted", "try again")
    ):
        return True
    return False


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    base_delay_s: float,
    factor: float,
    label: str,
    is_retryable: Callable[[BaseException], bool],
) -> T:
    """Call ``fn`` with exponential backoff + jitter on retryable errors."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - classified by is_retryable
            last_exc = exc
            if attempt >= max_attempts or not is_retryable(exc):
                raise
            delay = base_delay_s * (factor ** (attempt - 1))
            # Full jitter in [0.5, 1.5) × delay so concurrent jobs don't sync.
            sleep_for = delay * (0.5 + random.random())
            _log(
                f"{label}: attempt {attempt}/{max_attempts} failed "
                f"({type(exc).__name__}: {exc}); retry in {sleep_for:.1f}s"
            )
            time.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc


__all__ = [
    "API_BACKOFF_BASE_S",
    "API_BACKOFF_FACTOR",
    "API_MAX_ATTEMPTS",
    "GEMINI_BACKOFF_BASE_S",
    "GEMINI_BACKOFF_FACTOR",
    "GEMINI_MAX_ATTEMPTS",
    "is_retryable_api_error",
    "is_retryable_gemini_error",
    "is_retryable_http_status",
    "with_retry",
]
