"""P11: preflight — read-only target resolution before a write."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from pumble_keys.extensions.preflight import preflight_resolvers
from pumble_keys.extensions.resolve import ResolveFailure, ResolveSuccess


@dataclass
class Recorder:
    channel_inputs: Any = None
    user_inputs: Any = None

    def __post_init__(self) -> None:
        self.channel_inputs = []
        self.user_inputs = []

    def channel_resolver(self, result):
        async def resolve(value: str):
            self.channel_inputs.append(value)
            return result

        return resolve

    def user_resolver(self, result):
        async def resolve(value: str):
            self.user_inputs.append(value)
            return result

        return resolve


CHANNEL = ResolveSuccess(value="channel-object")
USER = ResolveSuccess(value="user-object")
NOT_FOUND = ResolveFailure(reason="not_found", candidates=())


@pytest.mark.asyncio
async def test_channel_only_success() -> None:
    rec = Recorder()
    result = await preflight_resolvers(
        channel="#eng",
        resolve_channel=rec.channel_resolver(CHANNEL),
        resolve_user=rec.user_resolver(USER),
    )
    assert result.ok is True
    assert result.channel is CHANNEL
    assert result.user is None
    assert rec.channel_inputs == ["#eng"]
    assert rec.user_inputs == []


@pytest.mark.asyncio
async def test_both_targets_success() -> None:
    rec = Recorder()
    result = await preflight_resolvers(
        channel="#eng",
        user="user-1@example.invalid",
        resolve_channel=rec.channel_resolver(CHANNEL),
        resolve_user=rec.user_resolver(USER),
    )
    assert result.ok is True
    assert result.channel is CHANNEL
    assert result.user is USER


@pytest.mark.asyncio
async def test_any_failure_fails_preflight_and_keeps_results() -> None:
    rec = Recorder()
    result = await preflight_resolvers(
        channel="#eng",
        user="ghost",
        resolve_channel=rec.channel_resolver(CHANNEL),
        resolve_user=rec.user_resolver(NOT_FOUND),
    )
    assert result.ok is False
    assert result.channel is CHANNEL  # kept for diagnostics
    assert result.user is NOT_FOUND


@pytest.mark.asyncio
async def test_no_targets_is_trivially_ok() -> None:
    rec = Recorder()
    result = await preflight_resolvers(
        resolve_channel=rec.channel_resolver(CHANNEL),
        resolve_user=rec.user_resolver(USER),
    )
    assert result.ok is True
    assert result.channel is None
    assert result.user is None
    assert rec.channel_inputs == []
    assert rec.user_inputs == []


@pytest.mark.asyncio
async def test_resolvers_run_concurrently() -> None:
    started: list[str] = []
    release = asyncio.Event()

    async def resolve_channel(_value: str):
        started.append("channel")
        await release.wait()
        return CHANNEL

    async def resolve_user(_value: str):
        started.append("user")
        release.set()  # user resolver unblocks the channel resolver
        return USER

    result = await asyncio.wait_for(
        preflight_resolvers(
            channel="#eng",
            user="u",
            resolve_channel=resolve_channel,
            resolve_user=resolve_user,
        ),
        timeout=1,
    )
    assert result.ok is True
    assert set(started) == {"channel", "user"}
