"""Async curated client façade over the generated raw SDK.

Ported from ``extensions/client.ts``. ``create_pumble_client`` wires
the generated ``PumbleSDK`` (the raw escape hatch stays reachable at
``client.raw``), the optional resolver cache, and the read namespaces.
Write façades land in P15–P17.

The façade is async-only. The generated raw SDK remains the supported
sync surface; no nested event loops fake sync behavior here.

Safety invariant: the generated client is constructed WITHOUT a global
``retry_config``. Generated writes honor a client-wide retry config, so
installing one would silently retry writes (see docs/RAW_API.md).
"""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any, Literal, Self
from urllib.parse import urlparse

import pydantic

from pumble_keys.extensions.channels import Channels
from pumble_keys.extensions.display import display_channel, display_user
from pumble_keys.extensions.identity import Identity
from pumble_keys.extensions.messages import Messages
from pumble_keys.extensions.operations import operation_failure
from pumble_keys.extensions.pagination import list_all_messages
from pumble_keys.extensions.preflight import (
    PreflightResult,
    preflight_resolvers,
)
from pumble_keys.extensions.resolver_cache import ResolverCache
from pumble_keys.extensions.results import FacadeFailure, create_facade_failure
from pumble_keys.extensions.search import search_all_messages
from pumble_keys.extensions.threads import get_thread_context
from pumble_keys.extensions.users import Users
from pumble_keys.extensions.writes import FacadeWrites

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ChannelSummary(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    id: str
    name: str
    channel_type: str


class UserSummary(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    id: str
    email: str
    name: str


class FindChannelSuccess(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    ok: Literal[True] = True
    summary: str
    ids: dict[str, str]
    channel: ChannelSummary


class FindUserSuccess(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    ok: Literal[True] = True
    summary: str
    ids: dict[str, str]
    user: UserSummary


class _RawResolverSource:
    """Adapts the generated async operations to the resolver protocols."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw

    async def list_channels(self) -> list[Any]:
        return await self._raw.channels.list_channels_async()

    async def list_users(self) -> list[Any]:
        return await self._raw.users.list_users_async()


class CacheNamespace:
    """``client.cache`` — explicit control over the resolver cache."""

    def __init__(self, cache: ResolverCache) -> None:
        self._cache = cache

    def clear(self, kind: Any = None) -> None:
        self._cache.clear(kind)

    async def refresh(self) -> None:
        await self._cache.refresh()

    def info(self) -> dict[str, str]:
        return dict(self._cache.info())

    def metrics(self) -> dict[str, int]:
        return self._cache.metrics()


class Search:
    """``client.search`` — one bounded page, or the defensive full walk."""

    def __init__(self, raw: Any, guard: Any, writes: Any) -> None:
        self._raw = raw
        self._guard = guard
        self.recent = writes.search_recent

    async def page(self, **options: Any) -> Any:
        """One bounded search page, normalized to ``SearchMessagesResult``."""
        response = await self._guard(
            "searchMessages", self._raw.messages.search_messages_async(**options)
        )
        return getattr(response, "result", response)

    def all(self, request: dict[str, Any], **options: Any) -> Any:
        """Exhaustive defensive walk (SDK-only; never a default MCP tool)."""

        async def fetch(page_request: dict[str, Any]) -> Any:
            return await self._raw.messages.search_messages_async(**page_request)

        return search_all_messages(fetch, request, **options)


class Threads:
    """``client.threads`` — compact context, replies, and the safe reply."""

    def __init__(self, raw: Any, guard: Any, writes: Any) -> None:
        self._raw = raw
        self._guard = guard
        self.reply = writes.reply_to_thread

    async def get_context(
        self,
        *,
        channel_id: str,
        message_id: str,
        reply_limit: int | None = None,
    ) -> Any:
        async def fetch_message(request: dict[str, Any]) -> Any:
            return await self._raw.messages.fetch_message_async(**request)

        async def fetch_replies(request: dict[str, Any]) -> Any:
            return await self._raw.messages.fetch_thread_replies_async(**request)

        try:
            return await get_thread_context(
                fetch_message=fetch_message,
                fetch_thread_replies=fetch_replies,
                channel_id=channel_id,
                message_id=message_id,
                reply_limit=reply_limit,
            )
        except (asyncio.CancelledError, ValueError):
            raise
        except Exception as error:  # noqa: BLE001 — categorized into a value
            return operation_failure(
                "Pumble API operation fetchThreadReplies failed.", error
            )

    async def list_replies(self, **options: Any) -> Any:
        response = await self._guard(
            "fetchThreadReplies",
            self._raw.messages.fetch_thread_replies_async(**options),
        )
        return getattr(response, "result", response)


class ScheduledReads:
    """``client.scheduled`` — reads only; the write façade arrives in P16."""

    def __init__(self, raw: Any, guard: Any) -> None:
        self._raw = raw
        self._guard = guard

    async def list(self, **options: Any) -> Any:
        response = await self._guard(
            "fetchScheduledMessages",
            self._raw.scheduled_messages.fetch_scheduled_messages_async(**options),
        )
        return getattr(response, "result", response)

    async def get(self, **options: Any) -> Any:
        return await self._guard(
            "fetchScheduledMessage",
            self._raw.scheduled_messages.fetch_scheduled_message_async(**options),
        )


class Messaging(Messages):
    """``client.messages`` with history walk and safe write façades."""

    def __init__(self, raw: Any, guard: Any, writes: Any) -> None:
        super().__init__(raw, guard)
        self.send = writes.send_message
        self.dm = writes.dm_user
        self.dm_group = writes.dm_group

    def all(self, request: dict[str, Any] | None = None, **options: Any) -> Any:
        async def fetch(page_request: dict[str, Any]) -> Any:
            return await self._raw.messages.list_messages_async(**page_request)

        return list_all_messages(fetch, request, **options)


class PumbleClient:
    """Curated async façade; the raw generated SDK stays at ``.raw``."""

    def __init__(self, raw: Any, *, resolver_cache: ResolverCache) -> None:
        self.raw = raw
        self._resolver_cache = resolver_cache
        self.cache = CacheNamespace(resolver_cache)

        guard = self._guard
        self.identity = Identity(raw, guard)
        self.channels = Channels(
            raw, guard, resolver_cache, self._resolve_facade_channel
        )
        self.users = Users(raw, guard, resolver_cache, self._resolve_facade_user)
        writes = FacadeWrites(
            raw=raw,
            resolve_facade_channel=self._resolve_facade_channel,
            resolve_facade_user=self._resolve_facade_user,
        )
        self.messages = Messaging(raw, guard, writes)
        self.search = Search(raw, guard, writes)
        self.threads = Threads(raw, guard, writes)
        self.scheduled = ScheduledReads(raw, guard)
        self.channels.create = writes.create_channel

    async def _guard(self, operation_id: str, awaitable: Any) -> Any:
        """Run one generated call; normal errors become failure values."""
        try:
            return await awaitable
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 — categorized into a value
            return operation_failure(
                f"Pumble API operation {operation_id} failed.", error
            )

    async def _resolve_facade_channel(
        self, input_value: str, **options: Any
    ) -> FindChannelSuccess | FacadeFailure:
        result = await self.channels.resolve(input_value, **options)
        if not result.ok:
            return create_facade_failure(
                "Channel",
                input_value,
                reason=result.reason,
                candidates=[vars(c) for c in result.candidates],
            )
        channel = ChannelSummary(
            id=result.value.id,
            name=result.value.name,
            channel_type=str(result.value.channel_type),
        )
        return FindChannelSuccess(
            summary=f"Found channel {display_channel(channel)}.",
            ids={"channel_id": channel.id},
            channel=channel,
        )

    async def _resolve_facade_user(
        self, input_value: str, **options: Any
    ) -> FindUserSuccess | FacadeFailure:
        result = await self.users.resolve(input_value, **options)
        if not result.ok:
            return create_facade_failure(
                "User",
                input_value,
                reason=result.reason,
                candidates=[vars(c) for c in result.candidates],
            )
        user = UserSummary(
            id=result.value.id, email=result.value.email, name=result.value.name
        )
        return FindUserSuccess(
            summary=f"Found user {display_user(user)}.",
            ids={"user_id": user.id},
            user=user,
        )

    async def preflight(
        self, *, channel: str | None = None, user: str | None = None
    ) -> PreflightResult:
        """Resolve intended write targets without performing any write."""
        return await preflight_resolvers(
            channel=channel,
            user=user,
            resolve_channel=self._resolve_facade_channel,
            resolve_user=self._resolve_facade_user,
        )

    async def aclose(self) -> None:
        """Close the generated client's HTTP resources."""
        aexit = getattr(self.raw, "__aexit__", None)
        if aexit is not None:
            await aexit(None, None, None)

    async def __aenter__(self) -> Self:
        aenter = getattr(self.raw, "__aenter__", None)
        if aenter is not None:
            await aenter()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


def _validate_base_url(server_url: str | None) -> None:
    if server_url is None:
        return
    parsed = urlparse(server_url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS:
        return
    raise ValueError(
        "create_pumble_client: server_url must use HTTPS (plain HTTP is "
        "allowed only for localhost testing)."
    )


def _normalize_cache_options(options: Any) -> dict[str, Any]:
    if options is True:
        return {"enabled": True}
    if options is False or options is None:
        return {"enabled": False}
    return {
        "enabled": options.get("enabled", True),
        "ttl_s": options.get("ttl_s"),
        "refresh_on_miss": options.get("refresh_on_miss", True),
    }


def create_pumble_client(
    api_key: str | None = None,
    *,
    server_url: str | None = None,
    timeout_ms: int | None = None,
    resolver_cache: bool | dict[str, Any] | None = False,
    raw: Any = None,
) -> PumbleClient:
    """Build the curated async client.

    ``raw`` injects a prebuilt (or fake) generated client for tests; in
    that mode ``api_key`` is ignored. The API key is installed only in
    the generated client's ``ApiKey`` header mechanism — it is never
    stored on the façade.
    """
    if raw is None:
        if api_key is None or not api_key.strip():
            raise ValueError("create_pumble_client: api_key must not be blank")
        _validate_base_url(server_url)
        from pumble_keys import PumbleSDK

        kwargs: dict[str, Any] = {"api_key_auth": api_key}
        if server_url is not None:
            kwargs["server_url"] = server_url
        if timeout_ms is not None:
            kwargs["timeout_ms"] = timeout_ms
        # Never pass retry_config: generated writes would honor it.
        raw = PumbleSDK(**kwargs)

    cache_options = _normalize_cache_options(resolver_cache)
    cache = ResolverCache(_RawResolverSource(raw), **cache_options)
    return PumbleClient(raw, resolver_cache=cache)
