"""Users namespace: reads and resolution. Status writes arrive in P17."""

from __future__ import annotations

from typing import Any

from pumble_keys.extensions.find import find_user_by_email
from pumble_keys.extensions.resolve import ResolveUserResult, resolve_user


class Users:
    """``client.users`` — list, groups, find, resolve."""

    def __init__(
        self, raw: Any, guard: Any, resolver_client: Any, facade_find: Any
    ) -> None:
        self._raw = raw
        self._guard = guard
        self._resolver_client = resolver_client
        self._facade_find = facade_find

    async def list(self, **options: Any) -> Any:
        return await self._guard(
            "listUsers", self._raw.users.list_users_async(**options)
        )

    async def list_groups(self, **options: Any) -> Any:
        return await self._guard(
            "listUserGroups", self._raw.users.list_user_groups_async(**options)
        )

    async def find_by_email(
        self, email: str, *, case_insensitive: bool = True
    ) -> Any | None:
        return await find_user_by_email(
            self._resolver_client, email, case_insensitive=case_insensitive
        )

    async def resolve(self, input_value: str, **options: Any) -> ResolveUserResult:
        return await resolve_user(self._resolver_client, input_value, **options)

    async def find(self, input_value: str, **options: Any) -> Any:
        """Structured find: success summary/ids/user or a façade failure."""
        return await self._facade_find(input_value, **options)
