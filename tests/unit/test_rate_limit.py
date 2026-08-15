"""P09: token-bucket limiter — deterministic clock, bounded queue, cancellation."""

from __future__ import annotations

import asyncio

import pytest

from pumble_keys.extensions.rate_limit import (
    RateLimiter,
    RateLimitQueueFullError,
)
from pumble_keys.extensions.retries import with_retries


class FakeClock:
    def __init__(self) -> None:
        self.time = 0.0

    def __call__(self) -> float:
        return self.time


class FakeTimers:
    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def set_timer(self, callback, delay_s: float):
        self.scheduled.append((delay_s, callback))
        return callback

    def fire_all(self) -> None:
        pending, self.scheduled = self.scheduled, []
        for _delay, callback in pending:
            callback()


def make_limiter(**kwargs):
    clock = FakeClock()
    timers = FakeTimers()
    limiter = RateLimiter(now=clock, set_timer=timers.set_timer, **kwargs)
    return limiter, clock, timers


def test_constructor_validation() -> None:
    with pytest.raises(ValueError, match="rps must be > 0"):
        RateLimiter(rps=0, burst=1)
    with pytest.raises(ValueError, match="burst must be >= 1"):
        RateLimiter(rps=1, burst=0)
    with pytest.raises(ValueError, match="max_queue must be >= 0"):
        RateLimiter(rps=1, burst=1, max_queue=-1)


@pytest.mark.asyncio
async def test_bucket_starts_full_at_burst() -> None:
    limiter, _clock, _timers = make_limiter(rps=1, burst=3)
    for _ in range(3):
        assert await limiter.limit(lambda: "ok") == "ok"
    assert limiter.available() == 0


@pytest.mark.asyncio
async def test_fractional_refill_and_cap() -> None:
    limiter, clock, _timers = make_limiter(rps=2, burst=3)
    for _ in range(3):
        await limiter.limit(lambda: None)
    clock.time = 0.25  # 0.5 tokens refilled
    assert limiter.available() == pytest.approx(0.5)
    clock.time = 100.0  # refill far past burst; capped
    assert limiter.available() == 3


@pytest.mark.asyncio
async def test_waiter_resumes_after_refill() -> None:
    limiter, clock, timers = make_limiter(rps=1, burst=1)
    await limiter.limit(lambda: None)  # drain the bucket

    task = asyncio.ensure_future(limiter.limit(lambda: "queued"))
    await asyncio.sleep(0)
    assert not task.done()
    assert timers.scheduled and timers.scheduled[0][0] == pytest.approx(1.0)

    clock.time = 1.0
    timers.fire_all()
    assert await task == "queued"


@pytest.mark.asyncio
async def test_queue_full_raises_dedicated_error() -> None:
    limiter, _clock, _timers = make_limiter(rps=1, burst=1, max_queue=1)
    await limiter.limit(lambda: None)

    task = asyncio.ensure_future(limiter.limit(lambda: "first-waiter"))
    await asyncio.sleep(0)

    with pytest.raises(RateLimitQueueFullError, match="queue is full"):
        await limiter.limit(lambda: "second-waiter")

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_cancelled_waiter_leaves_queue_and_token_goes_to_next() -> None:
    limiter, clock, timers = make_limiter(rps=1, burst=1)
    await limiter.limit(lambda: None)

    first = asyncio.ensure_future(limiter.limit(lambda: "first"))
    second = asyncio.ensure_future(limiter.limit(lambda: "second"))
    await asyncio.sleep(0)

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first

    clock.time = 1.0
    timers.fire_all()
    assert await second == "second"


@pytest.mark.asyncio
async def test_failing_call_still_costs_a_token() -> None:
    limiter, _clock, _timers = make_limiter(rps=1, burst=2)

    async def boom():
        raise RuntimeError("call failed")

    with pytest.raises(RuntimeError):
        await limiter.limit(boom)
    assert limiter.available() == 1


@pytest.mark.asyncio
async def test_sync_and_async_callables_supported() -> None:
    limiter, _clock, _timers = make_limiter(rps=1, burst=2)

    async def async_fn():
        return "async"

    assert await limiter.limit(async_fn) == "async"
    assert await limiter.limit(lambda: "sync") == "sync"


@pytest.mark.asyncio
async def test_every_retry_attempt_consumes_a_token() -> None:
    """The limiter sits inside the retry loop: attempts each cost a token."""
    limiter, _clock, _timers = make_limiter(rps=1, burst=5)
    attempts = []

    async def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("blip")
        return "ok"

    async def sleep_noop(_s: float) -> None:
        return None

    result = await with_retries(
        lambda: limiter.limit(flaky),
        unsafe_allow_write_retry=True,  # test thunk, not a Pumble write
        sleep=sleep_noop,
    )
    assert result == "ok"
    assert limiter.available() == 2  # 5 - 3 attempts
