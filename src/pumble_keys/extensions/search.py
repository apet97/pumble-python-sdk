"""Defensive exhaustive message search.

Ported from ``extensions/search-all.ts``. Pumble paginates
``searchMessages`` by the ``beforeTs`` cursor (epoch ms, strictly less
than), but server-side timestamps are truncated to seconds, so two
messages sharing a ``timestampMilli`` can straddle a page boundary. The
naive cursor can re-request an already-seen page forever.

This async generator walks pages defensively:

- dedupes by message ID; never yields the same hit twice;
- overlaps same-second page boundaries (up to 3 attempts) when a page
  ends with multiple hits at the minimum timestamp, then advances the
  cursor to ``min_ts - 1``;
- stops on: empty page, repeated first ID (server loop), a full page
  with zero new IDs, ``hasMore == false`` with a short page, missing
  timestamps, or a non-advancing cursor;
- enforces a hard page cap (default 10,000);
- fetches lazily — breaking out of ``async for`` stops all requests;
- cancellation (``asyncio.CancelledError``) propagates untouched.

This is an SDK API, not a default MCP tool: the model-facing search
tool stays one bounded page.
"""

from __future__ import annotations

import math
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

HARD_PAGE_CAP = 10_000
_OVERLAP_ATTEMPT_CAP = 3

SearchPageFetcher = Callable[[dict[str, Any]], Awaitable[Any]]
PageObserver = Callable[[Any, dict[str, int]], Awaitable[None] | None]


class PageCapExceededError(RuntimeError):
    """The walk hit the hard page cap — a probable server loop."""

    def __init__(self, helper: str, cap: int) -> None:
        super().__init__(
            f"{helper}: exceeded {cap} pages — refusing to continue "
            "(possible server loop)"
        )


def _timestamp_of(hit: Any) -> int | None:
    value = getattr(hit, "timestamp_milli", None)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    return None


def _id_of(item: Any) -> str | None:
    value = getattr(item, "id", None)
    return value if isinstance(value, str) else None


async def _observe(
    on_page: PageObserver | None, page: Any, info: dict[str, int]
) -> None:
    if on_page is None:
        return
    outcome = on_page(page, info)
    if outcome is not None and isinstance(outcome, Awaitable):
        await outcome


async def search_all_messages(
    search: SearchPageFetcher,
    request: dict[str, Any],
    *,
    max_results: int | None = None,
    max_pages: int | None = None,
    on_page: PageObserver | None = None,
) -> AsyncGenerator[Any, None]:
    """Yield every search hit for ``request`` across every page.

    ``search`` is an async callable taking a request dict (snake_case
    keys, e.g. ``{"text": ..., "before_ts": ...}``) and returning a page
    whose ``.result`` has ``content`` / ``has_more``. ``on_page`` fires
    once per fetched page with ``{"page_index", "new_in_page",
    "yielded"}``; raising from it aborts the walk.
    """
    page_cap = max_pages if max_pages is not None else HARD_PAGE_CAP
    seen: set[str] = set()
    limit = request.get("limit") or 10
    cursor: int | None = request.get("before_ts")
    prev_first_id: str | None = None
    page_index = 0
    yielded = 0

    while True:
        if page_index >= page_cap:
            raise PageCapExceededError("search_all_messages", page_cap)

        page_req = dict(request)
        if cursor is not None:
            page_req["before_ts"] = cursor
        page = await search(page_req)
        page_index += 1

        result = getattr(page, "result", None)
        content = list(getattr(result, "content", None) or [])
        if not content:
            return

        first_id = _id_of(content[0])
        if first_id is not None and first_id == prev_first_id:
            return  # server returned the exact same page again
        prev_first_id = first_id

        # Pass 1: min timestamp and new-id count, so on_page sees
        # accurate numbers before any yield.
        new_in_page = 0
        min_ts: int | None = None
        min_ts_count = 0
        for hit in content:
            ts = _timestamp_of(hit)
            if ts is not None:
                if min_ts is None or ts < min_ts:
                    min_ts = ts
                    min_ts_count = 1
                elif ts == min_ts:
                    min_ts_count += 1
            hit_id = _id_of(hit)
            if hit_id is not None and hit_id not in seen:
                new_in_page += 1

        await _observe(
            on_page,
            page,
            {
                "page_index": page_index,
                "new_in_page": new_in_page,
                "yielded": yielded,
            },
        )

        # Pass 2: yield new hits in server order (newest first).
        for hit in content:
            hit_id = _id_of(hit)
            if hit_id is None or hit_id in seen:
                continue
            seen.add(hit_id)
            yielded += 1
            yield hit
            if max_results is not None and yielded >= max_results:
                return

        if new_in_page == 0:
            return  # spinning: a page with zero new ids after dedupe

        has_more = getattr(result, "has_more", None)

        if min_ts_count > 1 and has_more is not False:
            # Same-second boundary: overlap with beforeTs = min_ts + 1000.
            overlap_cursor = min_ts + 1000  # type: ignore[operator]
            overlap_attempts = 0
            while overlap_attempts < _OVERLAP_ATTEMPT_CAP:
                if page_index >= page_cap:
                    raise PageCapExceededError("search_all_messages", page_cap)
                overlap_page = await search({**request, "before_ts": overlap_cursor})
                page_index += 1
                overlap_attempts += 1

                overlap_result = getattr(overlap_page, "result", None)
                overlap_content = list(getattr(overlap_result, "content", None) or [])
                if not overlap_content:
                    break

                new_in_overlap = sum(
                    1
                    for hit in overlap_content
                    if (hit_id := _id_of(hit)) is not None and hit_id not in seen
                )

                await _observe(
                    on_page,
                    overlap_page,
                    {
                        "page_index": page_index,
                        "new_in_page": new_in_overlap,
                        "yielded": yielded,
                    },
                )

                for hit in overlap_content:
                    hit_id = _id_of(hit)
                    if hit_id is None or hit_id in seen:
                        continue
                    seen.add(hit_id)
                    yielded += 1
                    yield hit
                    if max_results is not None and yielded >= max_results:
                        return

                if new_in_overlap == 0:
                    break

        if has_more is False and len(content) < limit:
            return
        if has_more is False and new_in_page == 0:
            return  # unreachable belt-and-braces, mirrors the TS guard

        if min_ts is None:
            return  # no usable timestamps — cursor cannot advance

        next_cursor = min_ts - 1
        if cursor is not None and next_cursor >= cursor:
            return  # cursor failed to advance
        cursor = next_cursor
