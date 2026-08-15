"""Channels namespace: reads and resolution. Writes arrive in P15."""

from __future__ import annotations

from typing import Any

from pumble_keys.extensions.find import find_channel_by_name
from pumble_keys.extensions.resolve import ResolveChannelResult, resolve_channel


class Channels:
    """``client.channels`` — list, get, find, resolve."""

    def __init__(
        self, raw: Any, guard: Any, resolver_client: Any, facade_find: Any
    ) -> None:
        self._raw = raw
        self._guard = guard
        self._resolver_client = resolver_client
        self._facade_find = facade_find

    async def list(self, **options: Any) -> Any:
        """All channels visible to the key (list of ``ChannelListEntry``)."""
        return await self._guard(
            "listChannels", self._raw.channels.list_channels_async(**options)
        )

    async def get(self, **options: Any) -> Any:
        """One channel by ``channel_id`` or ``channel`` name (unwrapped)."""
        response = await self._guard(
            "getChannel", self._raw.channels.get_channel_async(**options)
        )
        return getattr(response, "channel", response)

    async def find_by_name(
        self, name: str, *, case_insensitive: bool = True
    ) -> Any | None:
        return await find_channel_by_name(
            self._resolver_client, name, case_insensitive=case_insensitive
        )

    async def resolve(self, input_value: str, **options: Any) -> ResolveChannelResult:
        return await resolve_channel(self._resolver_client, input_value, **options)

    async def find(self, input_value: str, **options: Any) -> Any:
        """Structured find: success summary/ids/channel or a façade failure."""
        return await self._facade_find(input_value, **options)
