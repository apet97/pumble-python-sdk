"""Identity namespace: the authenticated principal."""

from __future__ import annotations

from typing import Any


class Identity:
    """``client.identity`` — who owns the API key."""

    def __init__(self, raw: Any, guard: Any) -> None:
        self._raw = raw
        self._guard = guard

    async def me(self, **options: Any) -> Any:
        """Fetch the authenticated user (generated ``models.User``)."""
        return await self._guard("myInfo", self._raw.users.my_info_async(**options))
