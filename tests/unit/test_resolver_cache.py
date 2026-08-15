"""P11: resolver cache — TTL, foreground refresh, clear, disabled passthrough."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from pumble_keys.extensions.resolver_cache import ResolverCache


class FakeClock:
    def __init__(self) -> None:
        self.time = 0.0

    def __call__(self) -> float:
        return self.time


@dataclass
class FakeSource:
    channels_calls: int = 0
    users_calls: int = 0
    fail_channels: bool = False
    delay: float = 0.0
    channels_value: list = field(default_factory=lambda: ["channel-entry"])
    users_value: list = field(default_factory=lambda: ["user-entry"])

    async def list_channels(self):
        self.channels_calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_channels:
            raise ConnectionError("load failed")
        return self.channels_value

    async def list_users(self):
        self.users_calls += 1
        return self.users_value


def make(**kwargs):
    clock = FakeClock()
    source = FakeSource()
    cache = ResolverCache(source, now=clock, **kwargs)
    return cache, source, clock


@pytest.mark.asyncio
async def test_disabled_mode_makes_no_cache_reads_or_writes() -> None:
    cache, source, _clock = make(enabled=False)
    await cache.list_channels()
    await cache.list_channels()
    await cache.list_users()
    assert source.channels_calls == 2  # every call hits the source
    assert cache.info() == {"channels": "empty", "users": "empty"}
    assert cache.metrics() == {"hits": 0, "misses": 0, "evictions": 0}


@pytest.mark.asyncio
async def test_second_read_is_a_hit_without_source_call() -> None:
    cache, source, _clock = make()
    assert await cache.list_channels() == ["channel-entry"]
    assert await cache.list_channels() == ["channel-entry"]
    assert source.channels_calls == 1
    assert cache.metrics() == {"hits": 1, "misses": 1, "evictions": 0}
    assert cache.info()["channels"] == "loaded"


@pytest.mark.asyncio
async def test_ttl_expiry_triggers_foreground_reload() -> None:
    cache, source, clock = make(ttl_s=10)
    await cache.list_channels()
    clock.time = 5.0
    await cache.list_channels()  # fresh
    assert source.channels_calls == 1
    clock.time = 11.0
    await cache.list_channels()  # stale → reload in the foreground
    assert source.channels_calls == 2


@pytest.mark.asyncio
async def test_refresh_on_miss_false_serves_stale() -> None:
    cache, source, clock = make(ttl_s=10, refresh_on_miss=False)
    await cache.list_channels()
    clock.time = 100.0
    assert await cache.list_channels() == ["channel-entry"]
    assert source.channels_calls == 1
    assert cache.metrics()["hits"] == 1


@pytest.mark.asyncio
async def test_clear_evicts_and_counts() -> None:
    cache, source, _clock = make()
    await cache.list_channels()
    await cache.list_users()
    cache.clear()
    assert cache.info() == {"channels": "empty", "users": "empty"}
    assert cache.metrics()["evictions"] == 2
    await cache.list_channels()
    assert source.channels_calls == 2


@pytest.mark.asyncio
async def test_clear_single_kind() -> None:
    cache, _source, _clock = make()
    await cache.list_channels()
    await cache.list_users()
    cache.clear("users")
    assert cache.info() == {"channels": "loaded", "users": "empty"}
    assert cache.metrics()["evictions"] == 1


@pytest.mark.asyncio
async def test_explicit_refresh_reloads_both_in_foreground() -> None:
    cache, source, _clock = make()
    await cache.list_channels()
    await cache.refresh()
    assert source.channels_calls == 2
    assert source.users_calls == 1
    assert cache.info() == {"channels": "loaded", "users": "loaded"}


@pytest.mark.asyncio
async def test_failed_load_evicts_itself() -> None:
    cache, source, _clock = make()
    source.fail_channels = True
    with pytest.raises(ConnectionError):
        await cache.list_channels()
    assert cache.info()["channels"] == "empty"
    source.fail_channels = False
    assert await cache.list_channels() == ["channel-entry"]
    assert source.channels_calls == 2


@pytest.mark.asyncio
async def test_concurrent_callers_share_one_load() -> None:
    cache, source, _clock = make()
    source.delay = 0.01
    results = await asyncio.gather(
        cache.list_channels(), cache.list_channels(), cache.list_channels()
    )
    assert results == [["channel-entry"]] * 3
    assert source.channels_calls == 1


@pytest.mark.asyncio
async def test_cache_stores_source_objects_not_labels() -> None:
    cache, source, _clock = make()
    sentinel = object()
    source.channels_value = [sentinel]
    result = await cache.list_channels()
    assert result[0] is sentinel
