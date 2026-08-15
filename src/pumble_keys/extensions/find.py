"""Convenience lookups over the un-paginated user/channel listings.

Ported from ``extensions/find.ts``. Both listings are bounded (a Pumble
workspace has dozens-to-hundreds of channels, not millions), so a single
SDK call is cheap. ``find_*`` is a thin naming convenience; the
deterministic resolvers in ``resolve.py`` remain the canonical path.
"""

from __future__ import annotations

from typing import Any

from pumble_keys.extensions.resolve import (
    ResolveChannelClient,
    ResolveUserClient,
)


def _normalise(value: str, case_insensitive: bool) -> str:
    trimmed = value.strip()
    return trimmed.lower() if case_insensitive else trimmed


async def find_user_by_email(
    client: ResolveUserClient,
    email: str,
    *,
    case_insensitive: bool = True,
) -> Any | None:
    """Find a workspace user by email. Returns ``None`` if no match.

    Pumble has no server-side user search by email — this walks
    ``listUsers`` and matches client-side.
    """
    target = _normalise(email, case_insensitive)
    users = await client.list_users()
    for user in users:
        candidate = getattr(user, "email", None)
        if isinstance(candidate, str) and (
            _normalise(candidate, case_insensitive) == target
        ):
            return user
    return None


async def find_channel_by_name(
    client: ResolveChannelClient,
    name: str,
    *,
    case_insensitive: bool = True,
) -> Any | None:
    """Find a channel by name. Returns ``None`` if no match.

    Channel names are unique within a workspace, so a found result is
    unambiguous.
    """
    target = _normalise(name, case_insensitive)
    entries = await client.list_channels()
    for entry in entries:
        channel = getattr(entry, "channel", None)
        candidate = getattr(channel, "name", None)
        if isinstance(candidate, str) and (
            _normalise(candidate, case_insensitive) == target
        ):
            return channel
    return None
