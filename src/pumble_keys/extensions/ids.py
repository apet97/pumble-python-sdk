"""Validated opaque ID aliases for Pumble entity references.

The generated SDK uses plain ``str`` for every ID. These ``NewType``
aliases let callers tag IDs at the boundary so a static type checker
rejects a channel ID passed in a message-ID slot. The ``as_*`` helpers
validate only the 24-character-hex shape; they never verify that an ID
exists in Pumble.

Ported from ``extensions/branded-ids.ts``.
"""

from __future__ import annotations

import re
from typing import Any, NewType

ChannelId = NewType("ChannelId", str)
MessageId = NewType("MessageId", str)
ScheduledMessageId = NewType("ScheduledMessageId", str)
UserId = NewType("UserId", str)
UserGroupId = NewType("UserGroupId", str)
WorkspaceId = NewType("WorkspaceId", str)

PumbleId = (
    ChannelId | MessageId | ScheduledMessageId | UserId | UserGroupId | WorkspaceId
)

_HEX24 = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)


def is_pumble_id_like(value: Any) -> bool:
    """Non-raising shape check. Does NOT verify the ID exists in Pumble."""
    return isinstance(value, str) and _HEX24.fullmatch(value) is not None


def _assert_hex24(value: Any, what: str) -> str:
    if not is_pumble_id_like(value):
        raise ValueError(f"{what}: expected a 24-character hex string, got: {value!r}")
    return value


def as_channel_id(value: str) -> ChannelId:
    """Tag a raw string as a ``ChannelId``. Raises ``ValueError`` on shape mismatch."""
    return ChannelId(_assert_hex24(value, "as_channel_id"))


def as_message_id(value: str) -> MessageId:
    """Tag a raw string as a ``MessageId``. Raises ``ValueError`` on shape mismatch."""
    return MessageId(_assert_hex24(value, "as_message_id"))


def as_scheduled_message_id(value: str) -> ScheduledMessageId:
    """Tag a raw string as a ``ScheduledMessageId``. Raises ``ValueError`` on shape mismatch."""
    return ScheduledMessageId(_assert_hex24(value, "as_scheduled_message_id"))


def as_user_id(value: str) -> UserId:
    """Tag a raw string as a ``UserId``. Raises ``ValueError`` on shape mismatch."""
    return UserId(_assert_hex24(value, "as_user_id"))


def as_user_group_id(value: str) -> UserGroupId:
    """Tag a raw string as a ``UserGroupId``. Raises ``ValueError`` on shape mismatch."""
    return UserGroupId(_assert_hex24(value, "as_user_group_id"))


def as_workspace_id(value: str) -> WorkspaceId:
    """Tag a raw string as a ``WorkspaceId``. Raises ``ValueError`` on shape mismatch."""
    return WorkspaceId(_assert_hex24(value, "as_workspace_id"))


def unbrand(id_value: PumbleId) -> str:
    """Escape hatch — return the plain string. Identity at runtime."""
    return str(id_value)
