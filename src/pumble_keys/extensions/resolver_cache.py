"""Optional in-memory cache for the resolver listings.

Ported from ``extensions/resolver-cache.ts``. Off by default at the
client level; when enabled it is TTL-bounded per entry type, refreshes
only in the foreground (no daemon, no background task), stores the
source objects (not labels), and never persists.

Python differences from the TS source, both plan-mandated:

- the clock is injectable monotonic time (TS used ``Date.now()``);
- ``clear`` accepts an optional entry type so channel/user-affecting
  writes can invalidate narrowly (P15/P17).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, Literal

CacheKind = Literal["channels", "users"]
ResolverCacheState = Literal["empty", "loaded"]


@dataclass
class _Entry:
    task: asyncio.Task[list[Any]]
    loaded_at: float


class ResolverCache:
    """Caches ``list_channels``/``list_users`` results around a source client.

    The cache object itself satisfies the resolver client protocols, so
    it can be passed anywhere the raw source is accepted. Concurrent
    callers share one in-flight load; a failed load evicts itself.
    """

    def __init__(
        self,
        source: Any,
        *,
        enabled: bool = True,
        ttl_s: float | None = None,
        refresh_on_miss: bool = True,
        now: Callable[[], float] = monotonic,
    ) -> None:
        self._source = source
        self._enabled = enabled
        self._ttl_s = ttl_s
        self._refresh_on_miss = refresh_on_miss
        self._now = now
        self._entries: dict[CacheKind, _Entry | None] = {
            "channels": None,
            "users": None,
        }
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    async def list_channels(self) -> list[Any]:
        if not self._enabled:
            return await self._source.list_channels()
        return await self._cached("channels")

    async def list_users(self) -> list[Any]:
        if not self._enabled:
            return await self._source.list_users()
        return await self._cached("users")

    def clear(self, kind: CacheKind | None = None) -> None:
        """Evict cached entries — both kinds, or one when named."""
        kinds: tuple[CacheKind, ...] = (kind,) if kind else ("channels", "users")
        for key in kinds:
            if self._entries[key] is not None:
                self._evictions += 1
            self._entries[key] = None

    async def refresh(self) -> None:
        """Foreground reload of both listings. Raises on load failure."""
        channels = self._load("channels")
        users = self._load("users")
        await asyncio.gather(channels, users)

    def info(self) -> dict[str, ResolverCacheState]:
        return {
            "channels": "empty" if self._entries["channels"] is None else "loaded",
            "users": "empty" if self._entries["users"] is None else "loaded",
        }

    def metrics(self) -> dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
        }

    def _fresh(self, entry: _Entry) -> bool:
        return self._ttl_s is None or self._now() - entry.loaded_at <= self._ttl_s

    async def _cached(self, kind: CacheKind) -> list[Any]:
        entry = self._entries[kind]
        if entry is not None and (self._fresh(entry) or not self._refresh_on_miss):
            self._hits += 1
            return await asyncio.shield(entry.task)
        return await asyncio.shield(self._load(kind))

    def _load(self, kind: CacheKind) -> asyncio.Task[list[Any]]:
        self._misses += 1
        entry_box: list[_Entry] = []

        async def loader() -> list[Any]:
            try:
                if kind == "channels":
                    return await self._source.list_channels()
                return await self._source.list_users()
            except BaseException:
                if entry_box and self._entries[kind] is entry_box[0]:
                    self._entries[kind] = None
                raise

        task = asyncio.ensure_future(loader())
        entry = _Entry(task=task, loaded_at=self._now())
        entry_box.append(entry)
        self._entries[kind] = entry
        return task
