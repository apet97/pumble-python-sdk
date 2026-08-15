"""P09: transient-only retry — write callables cannot slip through."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from pumble_keys.extensions.retries import (
    READ_OPERATION_IDS,
    is_safe_to_retry,
    mark_safe_to_retry,
    with_retries,
)
from pumble_keys.models.errors import PumbleSDKError


def _sdk_error(status: int, headers: dict | None = None) -> PumbleSDKError:
    return PumbleSDKError(
        "API error occurred",
        httpx.Response(
            status,
            text="",
            headers=headers or {},
            request=httpx.Request("GET", "https://sanitized.example.invalid"),
        ),
    )


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def test_read_operation_ids_match_manifest() -> None:
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent.parent
    ledger = json.loads((repo / "contracts" / "operations.json").read_text())
    reads = {op["operationId"] for op in ledger if op["class"] == "read"}
    assert READ_OPERATION_IDS == reads


@pytest.mark.asyncio
async def test_unproven_callable_is_rejected_before_any_call() -> None:
    calls = []

    async def fn():
        calls.append(1)

    with pytest.raises(ValueError, match="refusing to retry"):
        await with_retries(fn)
    assert calls == []


@pytest.mark.asyncio
async def test_write_operation_id_is_rejected() -> None:
    async def fn():
        return "x"

    with pytest.raises(ValueError, match="refusing to retry"):
        await with_retries(fn, operation_id="sendMessage")


@pytest.mark.asyncio
async def test_read_operation_id_is_accepted() -> None:
    async def fn():
        return "ok"

    assert await with_retries(fn, operation_id="listChannels") == "ok"


@pytest.mark.asyncio
async def test_safe_marker_is_accepted() -> None:
    @mark_safe_to_retry
    async def fn():
        return "ok"

    assert is_safe_to_retry(fn)
    assert await with_retries(fn) == "ok"


@pytest.mark.asyncio
async def test_unsafe_override_is_accepted_and_greppable() -> None:
    async def fn():
        return "ok"

    assert await with_retries(fn, unsafe_allow_write_retry=True) == "ok"


@pytest.mark.asyncio
async def test_transient_error_retries_then_succeeds() -> None:
    sleep = SleepRecorder()
    attempts = []

    async def fn():
        attempts.append(1)
        if len(attempts) < 3:
            raise _sdk_error(503)
        return "recovered"

    result = await with_retries(
        fn,
        operation_id="listChannels",
        sleep=sleep,
        rng=lambda: 0.5,  # jitter factor exactly 1.0
    )
    assert result == "recovered"
    assert len(attempts) == 3
    # base 250ms * 2^0, 2^1 with jitter 1.0
    assert sleep.delays == [0.25, 0.5]


@pytest.mark.asyncio
async def test_permanent_error_raises_immediately() -> None:
    attempts = []

    async def fn():
        attempts.append(1)
        raise _sdk_error(401)

    with pytest.raises(PumbleSDKError):
        await with_retries(fn, operation_id="listChannels")
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_attempts_exhaust_and_last_error_raises() -> None:
    sleep = SleepRecorder()
    attempts = []

    async def fn():
        attempts.append(1)
        raise _sdk_error(500)

    with pytest.raises(PumbleSDKError):
        await with_retries(fn, operation_id="listChannels", max_attempts=3, sleep=sleep)
    assert len(attempts) == 3
    assert len(sleep.delays) == 2


@pytest.mark.asyncio
async def test_max_delay_caps_backoff() -> None:
    sleep = SleepRecorder()
    attempts = []

    async def fn():
        attempts.append(1)
        raise _sdk_error(500)

    with pytest.raises(PumbleSDKError):
        await with_retries(
            fn,
            operation_id="listChannels",
            max_attempts=6,
            base_ms=1000,
            max_delay_ms=1500,
            sleep=sleep,
            rng=lambda: 0.5,
        )
    assert sleep.delays == [1.0, 1.5, 1.5, 1.5, 1.5]


@pytest.mark.asyncio
async def test_retry_after_delta_seconds_is_respected_and_capped() -> None:
    sleep = SleepRecorder()
    attempts = []

    async def fn():
        attempts.append(1)
        if len(attempts) == 1:
            raise _sdk_error(429, {"Retry-After": "2"})
        if len(attempts) == 2:
            raise _sdk_error(503, {"Retry-After": "60"})
        return "ok"

    result = await with_retries(
        fn,
        operation_id="listChannels",
        max_delay_ms=5000,
        sleep=sleep,
    )
    assert result == "ok"
    assert sleep.delays == [2.0, 5.0]  # second capped at max_delay


@pytest.mark.asyncio
async def test_retry_after_http_date_is_parsed() -> None:
    sleep = SleepRecorder()
    attempts = []
    fixed_now = 1_786_752_000.0  # 2026-08-15T00:00:00Z

    async def fn():
        attempts.append(1)
        if len(attempts) == 1:
            raise _sdk_error(429, {"Retry-After": "Sat, 15 Aug 2026 00:00:03 GMT"})
        return "ok"

    result = await with_retries(
        fn,
        operation_id="listChannels",
        sleep=sleep,
        wall_now=lambda: fixed_now,
    )
    assert result == "ok"
    assert sleep.delays == [3.0]


@pytest.mark.asyncio
async def test_unparseable_retry_after_falls_back_to_backoff() -> None:
    sleep = SleepRecorder()
    attempts = []

    async def fn():
        attempts.append(1)
        if len(attempts) == 1:
            raise _sdk_error(429, {"Retry-After": "soon"})
        return "ok"

    await with_retries(fn, operation_id="listChannels", sleep=sleep, rng=lambda: 0.5)
    assert sleep.delays == [0.25]


@pytest.mark.asyncio
async def test_on_retry_observer_fires_before_sleep() -> None:
    events: list[tuple[int, float]] = []
    sleep = SleepRecorder()
    attempts = []

    async def fn():
        attempts.append(1)
        if len(attempts) < 2:
            raise _sdk_error(500)
        return "ok"

    await with_retries(
        fn,
        operation_id="listChannels",
        sleep=sleep,
        rng=lambda: 0.5,
        on_retry=lambda attempt, delay_ms, error: events.append((attempt, delay_ms)),
    )
    assert events == [(1, 250.0)]


@pytest.mark.asyncio
async def test_cancellation_propagates_from_fn() -> None:
    attempts = []

    async def fn():
        attempts.append(1)
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await with_retries(fn, operation_id="listChannels")
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_cancellation_during_sleep_propagates() -> None:
    async def fn():
        raise _sdk_error(500)

    async def cancelled_sleep(_seconds: float) -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await with_retries(fn, operation_id="listChannels", sleep=cancelled_sleep)


@pytest.mark.asyncio
async def test_custom_retry_statuses_narrow_retries() -> None:
    attempts = []

    async def fn():
        attempts.append(1)
        raise _sdk_error(500)

    with pytest.raises(PumbleSDKError):
        await with_retries(
            fn,
            operation_id="listChannels",
            retry_statuses=frozenset({429}),
        )
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_custom_is_retryable_overrides_default() -> None:
    attempts = []

    async def fn():
        attempts.append(1)
        raise _sdk_error(401)

    with pytest.raises(PumbleSDKError):
        await with_retries(
            fn,
            operation_id="listChannels",
            max_attempts=2,
            is_retryable=lambda error, attempt: True,
            sleep=SleepRecorder(),
        )
    assert len(attempts) == 2
