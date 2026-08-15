"""In-process token-bucket rate limiter for outbound SDK calls.

Ported from ``extensions/rate-limiter.ts``. Designed to sit *inside*
``with_retries`` so each retry attempt acquires its own token:

    limiter = RateLimiter(rps=5, burst=10)
    await with_retries(
        lambda: limiter.limit(lambda: sdk.messages.search_messages_async(...)),
        operation_id="searchMessages",
    )

In-process only. Multi-process rate limiting needs a shared store and
is out of scope. Waits are cancellation-safe: a cancelled waiter leaves
the queue and its token goes to the next caller.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any, TypeVar

T = TypeVar("T")


class RateLimitQueueFullError(Exception):
    """Raised when more callers wait than ``max_queue`` allows."""

    def __init__(self) -> None:
        super().__init__("rate limiter queue is full")


class RateLimiter:
    """Token bucket: starts full at ``burst``, refills at ``rps`` per second."""

    def __init__(
        self,
        *,
        rps: float,
        burst: float,
        max_queue: int | None = None,
        now: Callable[[], float] = monotonic,
        set_timer: Callable[[Callable[[], None], float], Any] | None = None,
    ) -> None:
        if not rps > 0:
            raise ValueError(f"RateLimiter: rps must be > 0, got {rps}")
        if not burst >= 1:
            raise ValueError(f"RateLimiter: burst must be >= 1, got {burst}")
        if max_queue is not None and max_queue < 0:
            raise ValueError(f"RateLimiter: max_queue must be >= 0, got {max_queue}")
        self._rps = rps
        self._burst = burst
        self._max_queue = max_queue
        self._now = now
        self._set_timer = set_timer or self._default_set_timer
        self._tokens = float(burst)
        self._last_refill = now()
        self._queue: deque[asyncio.Future[None]] = deque()
        self._drain_handle: Any = None

    @staticmethod
    def _default_set_timer(callback: Callable[[], None], delay_s: float) -> Any:
        return asyncio.get_running_loop().call_later(delay_s, callback)

    def _refill(self) -> None:
        t = self._now()
        elapsed = t - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self._burst, self._tokens + elapsed * self._rps)
        self._last_refill = t

    def _try_drain(self) -> None:
        self._drain_handle = None
        self._refill()
        while self._tokens >= 1 and self._queue:
            waiter = self._queue.popleft()
            if waiter.done():
                continue  # cancelled while queued; token stays available
            self._tokens -= 1
            waiter.set_result(None)
        if self._queue:
            self._schedule_drain()

    def _schedule_drain(self) -> None:
        if self._drain_handle is not None or not self._queue:
            return
        self._refill()
        tokens_needed = max(0.0, 1.0 - self._tokens)
        wait_s = max(0.0, tokens_needed / self._rps)
        self._drain_handle = self._set_timer(self._try_drain, wait_s)

    async def _acquire(self) -> None:
        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return
        if self._max_queue is not None and len(self._queue) >= self._max_queue:
            raise RateLimitQueueFullError
        waiter: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._queue.append(waiter)
        self._schedule_drain()
        try:
            await waiter
        except asyncio.CancelledError:
            if waiter in self._queue:
                self._queue.remove(waiter)
            raise

    async def limit(self, fn: Callable[[], Awaitable[T] | T]) -> T:
        """Wait for a token, then invoke ``fn``.

        A failing call still costs its token.
        """
        await self._acquire()
        result = fn()
        if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
            return await result  # type: ignore[no-any-return]
        return result

    def available(self) -> float:
        """Current available tokens after the implicit refill. Inspect-only."""
        self._refill()
        return self._tokens
