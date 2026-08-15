"""Transient-only retry wrapper for read operations.

Ported from ``extensions/with-retries.ts`` with one deliberate
tightening: the wrapper refuses to run a callable that is not provably
safe to retry. A retry after a lost response can create a second
user-visible object, so writes must never pass through here.

A callable is accepted when one of these holds:

- ``operation_id`` is one of the 11 read operations in the manifest;
- the callable carries the ``SafeToRetry`` marker
  (``mark_safe_to_retry``);
- the caller passes the explicit, greppable
  ``unsafe_allow_write_retry=True`` override.

Cancellation propagates: ``asyncio.CancelledError`` is never counted as
an attempt, categorized, or swallowed.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from email.utils import parsedate_to_datetime
from time import time as _wall_time
from typing import Any, TypeVar

from pumble_keys.extensions.errors import categorize_error

T = TypeVar("T")

# The 11 read operations from contracts/operations.json. A contract test
# asserts this stays equal to the manifest; the constant exists so the
# packaged wheel does not depend on repository files.
READ_OPERATION_IDS: frozenset[str] = frozenset(
    {
        "listChannels",
        "getChannel",
        "fetchMessage",
        "fetchThreadReplies",
        "searchMessages",
        "listMessages",
        "fetchScheduledMessages",
        "fetchScheduledMessage",
        "listUsers",
        "listUserGroups",
        "myInfo",
    }
)

DEFAULT_RETRY_STATUSES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})

_SAFE_MARKER = "__pumble_safe_to_retry__"


def mark_safe_to_retry(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a read-only thunk as safe for ``with_retries``. Decorator-friendly."""
    setattr(fn, _SAFE_MARKER, True)
    return fn


def is_safe_to_retry(fn: Callable[..., Any]) -> bool:
    return getattr(fn, _SAFE_MARKER, False) is True


async def with_retries(
    fn: Callable[[], Awaitable[T]],
    *,
    operation_id: str | None = None,
    unsafe_allow_write_retry: bool = False,
    max_attempts: int = 3,
    base_ms: float = 250,
    max_delay_ms: float = 8_000,
    retry_statuses: frozenset[int] = DEFAULT_RETRY_STATUSES,
    is_retryable: Callable[[Any, int], bool] | None = None,
    respect_retry_after: bool = True,
    on_retry: Callable[[int, float, Any], None] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    rng: Callable[[], float] = random.random,
    wall_now: Callable[[], float] = _wall_time,
) -> T:
    """Run ``fn`` with jittered exponential backoff on transient errors.

    Permanent errors (auth, validation, 4xx other than 408/425/429) are
    raised immediately. ``on_retry(attempt, delay_ms, error)`` fires
    before each sleep. ``Retry-After`` on 429/503 overrides the backoff
    delay, capped at ``max_delay_ms``.
    """
    if not (
        unsafe_allow_write_retry
        or (operation_id is not None and operation_id in READ_OPERATION_IDS)
        or is_safe_to_retry(fn)
    ):
        raise ValueError(
            "with_retries: refusing to retry an unproven callable. Pass a "
            "read operation_id, mark the thunk with mark_safe_to_retry, or "
            "set unsafe_allow_write_retry=True (never for Pumble writes: a "
            "retried write can duplicate a message)."
        )

    def default_is_retryable(error: Any, _attempt: int) -> bool:
        categorized = categorize_error(error)
        if not categorized.retryable:
            return False
        return (
            categorized.status_code is None or categorized.status_code in retry_statuses
        )

    retryable = is_retryable or default_is_retryable

    last_error: Any = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            last_error = error
            more = attempt + 1 < max_attempts
            if not more or not retryable(error, attempt):
                raise

            retry_after_ms = (
                _extract_retry_after_ms(error, wall_now)
                if respect_retry_after
                else None
            )
            if retry_after_ms is not None:
                delay_ms = min(max_delay_ms, max(0.0, retry_after_ms))
            else:
                jitter = 0.5 + rng()
                delay_ms = min(max_delay_ms, base_ms * (2**attempt) * jitter)
            if on_retry is not None:
                on_retry(attempt + 1, delay_ms, error)
            await sleep(delay_ms / 1000)

    raise last_error  # pragma: no cover — loop always returns or raises


def _extract_retry_after_ms(error: Any, wall_now: Callable[[], float]) -> float | None:
    """``Retry-After`` (delta-seconds or HTTP-date) from a 429/503 error."""
    status_code = getattr(error, "status_code", None)
    if status_code not in (429, 503):
        return None
    headers = getattr(error, "headers", None)
    if headers is None:
        return None
    raw = headers.get("retry-after")
    if raw is None:
        return None
    return _parse_retry_after_ms(raw, wall_now)


def _parse_retry_after_ms(raw: str, wall_now: Callable[[], float]) -> float | None:
    trimmed = raw.strip()
    if not trimmed:
        return None
    if trimmed.isdigit():
        return int(trimmed) * 1000.0
    try:
        target = parsedate_to_datetime(trimmed)
    except (TypeError, ValueError):
        return None
    if target.tzinfo is None:
        return None
    return target.timestamp() * 1000.0 - wall_now() * 1000.0
