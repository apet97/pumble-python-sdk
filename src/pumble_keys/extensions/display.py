"""Stable compact labels for channels, users, and ambiguity choices.

Ported from ``extensions/display.ts`` and the label formatters in
``extensions/resolve.ts``. The label formats are part of the façade
contract; MCP tools and CLI output rely on them staying byte-stable.
"""

from __future__ import annotations

from typing import Protocol


class ChannelLike(Protocol):
    """Anything with a channel name (generated ``Channel`` included)."""

    name: str


class UserLike(Protocol):
    """Anything with a user name and email (generated ``User`` included)."""

    name: str
    email: str


def display_channel(channel: ChannelLike) -> str:
    """Channel name for a receipt summary. Adds a leading ``#`` if missing."""
    name = channel.name
    return name if name.startswith("#") else f"#{name}"


def display_user(user: UserLike) -> str:
    """User label for a receipt summary. Falls back to email for blank names."""
    return user.name if user.name.strip() else user.email


def format_user_candidate_label(*, id: str, email: str, name: str) -> str:
    """Ambiguity-choice label: ``<name> <email> | <id>`` or ``<email> | <id>``."""
    trimmed = name.strip()
    if trimmed:
        return f"{trimmed} {email} | {id}"
    return f"{email} | {id}"


def format_channel_candidate_label(*, id: str, name: str, channel_type: str) -> str:
    """Ambiguity-choice label: ``#<name> | <type> | <id>``."""
    return f"#{name} | {channel_type} | {id}"
