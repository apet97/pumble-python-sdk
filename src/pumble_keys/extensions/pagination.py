"""Defensive channel-history pagination.

Ported from ``extensions/list-all-messages.ts``. Same defensive shape
as ``search_all_messages`` but for the channel-scrollback endpoint:
opaque message-ID cursors (not timestamps), walking backward by default
with ``hasMoreBefore`` as the stop signal.

Stops on: empty page, a page with zero new IDs, the strategy's
``hasMore*`` flag not true, a missing last-message ID, or a
non-advancing (repeated) cursor. Hard page cap 10,000. Fetches lazily;
cancellation propagates untouched.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from pumble_keys.extensions.search import (
    HARD_PAGE_CAP,
    PageCapExceededError,
    PageObserver,
    _id_of,
    _observe,
)

ListPageFetcher = Callable[[dict[str, Any]], Awaitable[Any]]


async def list_all_messages(
    list_messages: ListPageFetcher,
    request: dict[str, Any] | None = None,
    *,
    max_results: int | None = None,
    max_pages: int | None = None,
    on_page: PageObserver | None = None,
) -> AsyncGenerator[Any, None]:
    """Walk a channel's history, deduping by ID with cursor-loop protection.

    ``list_messages`` is an async callable taking a request dict
    (snake_case keys, e.g. ``{"channel_id": ..., "cursor": ...}``) and
    returning a page whose ``.result`` has ``messages`` /
    ``has_more_before`` / ``has_more_after``.
    """
    request = dict(request or {})
    page_cap = max_pages if max_pages is not None else HARD_PAGE_CAP
    seen: set[str] = set()
    base_req = {**request, "strategy": request.get("strategy") or "BEFORE"}
    cursor: str | None = request.get("cursor")
    prev_cursor: str | None = None
    page_index = 0
    yielded = 0

    while True:
        if page_index >= page_cap:
            raise PageCapExceededError("list_all_messages", page_cap)

        page_req = dict(base_req)
        if cursor is not None:
            page_req["cursor"] = cursor
        page = await list_messages(page_req)
        page_index += 1

        result = getattr(page, "result", None)
        messages = list(getattr(result, "messages", None) or [])
        if not messages:
            return

        new_in_page = sum(
            1
            for message in messages
            if (message_id := _id_of(message)) is not None and message_id not in seen
        )

        await _observe(
            on_page,
            page,
            {
                "page_index": page_index,
                "new_in_page": new_in_page,
                "yielded": yielded,
            },
        )

        for message in messages:
            message_id = _id_of(message)
            if message_id is None or message_id in seen:
                continue
            seen.add(message_id)
            yielded += 1
            yield message
            if max_results is not None and yielded >= max_results:
                return

        if new_in_page == 0:
            return

        strategy = str(base_req.get("strategy"))
        has_more = (
            getattr(result, "has_more_after", None)
            if strategy == "AFTER"
            else getattr(result, "has_more_before", None)
        )
        if has_more is not True:
            return

        last_id = _id_of(messages[-1])
        if last_id is None:
            return
        if prev_cursor is not None and last_id == prev_cursor:
            return
        prev_cursor = last_id
        cursor = last_id
