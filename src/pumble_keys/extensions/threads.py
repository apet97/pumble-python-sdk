"""Compact thread context and safer thread reply.

Ported from ``extensions/thread-context.ts``. ``get_thread_context``
fetches the thread root and one page of replies concurrently and
returns a compact view: no summarizing, no text transformation — only
bulky fields removed and participant IDs extracted in first-seen order.
``reply_to_thread`` requires explicit channel and root-message IDs and
rejects blank text before dispatch; it never retries.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ThreadContextMessage:
    id: str
    channel_id: str
    author: str
    text: str
    timestamp: str
    timestamp_milli: int


@dataclass(frozen=True)
class ThreadContext:
    root: ThreadContextMessage
    replies: tuple[ThreadContextMessage, ...]
    participants: tuple[str, ...]
    reply_count: int


def _require_non_blank(value: str, name: str, helper: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{helper}: {name} is required")


def _reply_limit(value: int | None) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 1
    ):
        raise ValueError("get_thread_context: reply_limit must be a positive number")
    return int(value)


def _compact(message: Any) -> ThreadContextMessage:
    timestamp = message.timestamp
    return ThreadContextMessage(
        id=message.id,
        channel_id=message.channel_id,
        author=message.author,
        text=message.text,
        timestamp=timestamp.isoformat().replace("+00:00", "Z"),
        timestamp_milli=message.timestamp_milli,
    )


def _participants(root: Any, replies: list[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    participants: list[str] = []
    for message in [root, *replies]:
        author = message.author
        if not author.strip() or author in seen:
            continue
        seen.add(author)
        participants.append(author)
    return tuple(participants)


async def get_thread_context(
    *,
    fetch_message: Callable[[dict[str, Any]], Awaitable[Any]],
    fetch_thread_replies: Callable[[dict[str, Any]], Awaitable[Any]],
    channel_id: str,
    message_id: str,
    reply_limit: int | None = None,
) -> ThreadContext:
    """Fetch root and replies concurrently; return the compact context.

    The fetchers are async callables taking request dicts (snake_case
    keys); P14 binds them to the generated async operations.
    """
    _require_non_blank(channel_id, "channel_id", "get_thread_context")
    _require_non_blank(message_id, "message_id", "get_thread_context")
    limit = _reply_limit(reply_limit)

    replies_request: dict[str, Any] = {
        "channel_id": channel_id,
        "root_message_id": message_id,
    }
    if limit is not None:
        replies_request["limit"] = limit

    root, replies_page = await asyncio.gather(
        fetch_message({"channel_id": channel_id, "message_id": message_id}),
        fetch_thread_replies(replies_request),
    )
    all_replies = list(getattr(replies_page, "result", None) or [])
    replies = all_replies if limit is None else all_replies[:limit]

    thread_root_info = getattr(root, "thread_root_info", None)
    server_count = getattr(thread_root_info, "reply_count", None)
    return ThreadContext(
        root=_compact(root),
        replies=tuple(_compact(reply) for reply in replies),
        participants=_participants(root, replies),
        reply_count=server_count if server_count is not None else len(replies),
    )


async def reply_to_thread(
    *,
    send_reply: Callable[[dict[str, Any]], Awaitable[Any]],
    channel_id: str,
    message_id: str,
    text: str,
    **extra: Any,
) -> Any:
    """Send one thread reply after validating the explicit target. No retry."""
    _require_non_blank(channel_id, "channel_id", "reply_to_thread")
    _require_non_blank(message_id, "message_id", "reply_to_thread")
    _require_non_blank(text, "text", "reply_to_thread")

    return await send_reply(
        {
            "channel_id": channel_id,
            "message_id": message_id,
            "text": text,
            **extra,
        }
    )
