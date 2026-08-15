"""Read-only target resolution before a write.

Ported from ``extensions/resolver-preflight.ts``. Resolves the requested
channel and/or user concurrently and reports success only when every
requested target resolved. Reusable by the SDK façade, CLI, MCP tools,
and the MCP App — no write happens here.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PreflightResult:
    """``ok`` is true only when every requested target resolved.

    ``channel``/``user`` hold the underlying resolve results (success or
    failure) when requested, ``None`` otherwise.
    """

    ok: bool
    channel: Any | None = None
    user: Any | None = None


async def preflight_resolvers(
    *,
    channel: str | None = None,
    user: str | None = None,
    resolve_channel: Callable[[str], Awaitable[Any]],
    resolve_user: Callable[[str], Awaitable[Any]],
) -> PreflightResult:
    """Resolve requested targets concurrently; no write is performed."""

    async def maybe(
        value: str | None, resolver: Callable[[str], Awaitable[Any]]
    ) -> Any | None:
        return None if value is None else await resolver(value)

    channel_result, user_result = await asyncio.gather(
        maybe(channel, resolve_channel),
        maybe(user, resolve_user),
    )
    failed = (channel_result is not None and not channel_result.ok) or (
        user_result is not None and not user_result.ok
    )
    return PreflightResult(ok=not failed, channel=channel_result, user=user_result)
