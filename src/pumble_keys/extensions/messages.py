"""Messages namespace: reads. Safe write façades arrive in P15."""

from __future__ import annotations

from typing import Any


class Messages:
    """``client.messages`` — get and list channel messages."""

    def __init__(self, raw: Any, guard: Any) -> None:
        self._raw = raw
        self._guard = guard

    async def get(self, **options: Any) -> Any:
        """One message by ID (generated ``models.Message``)."""
        return await self._guard(
            "fetchMessage", self._raw.messages.fetch_message_async(**options)
        )

    async def list(self, **options: Any) -> Any:
        """One page of channel history, normalized to ``MessageList``."""
        response = await self._guard(
            "listMessages", self._raw.messages.list_messages_async(**options)
        )
        return getattr(response, "result", response)
