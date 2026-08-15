"""The seven curated read tools.

Registered in this exact order: ``whoami``, ``find_channel``,
``find_user``, ``list_channels``, ``search_messages``,
``get_channel_context``, ``get_thread_context``. All are read-only and
idempotent; none performs a write. Limits default to 10 and cap at 50.
Normal ambiguity/not-found/API failures return structured values.
"""

from __future__ import annotations

from typing import Annotated, Any

import pydantic
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.models import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ChannelContextResult,
    ChannelInfo,
    Choice,
    CompactMessage,
    CuratedFailure,
    FindChannelResult,
    FindUserResult,
    ListChannelsResult,
    SearchResult,
    ThreadContextResult,
    UserInfo,
    WhoamiResult,
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)

Limit = Annotated[int, pydantic.Field(ge=1, le=MAX_LIMIT)]


def state_of(ctx: Context) -> Any:
    return ctx.request_context.lifespan_context


def to_failure(failure: FacadeFailure) -> CuratedFailure:
    choices = []
    for choice in failure.choices:
        if isinstance(choice, dict):
            choices.append(
                Choice(
                    id=str(choice.get("id", "")),
                    label=str(choice.get("label", "")),
                    name=choice.get("name"),
                    email=choice.get("email"),
                )
            )
    return CuratedFailure(
        reason=failure.reason,
        summary=failure.summary,
        choices=choices,
        next_actions=list(failure.next_actions),
    )


def compact_message(message: Any) -> CompactMessage:
    return CompactMessage(
        id=message.id,
        channel_id=message.channel_id,
        author=message.author,
        text=message.text,
        timestamp_milli=getattr(message, "timestamp_milli", None),
    )


def register(server: MCPServer, _config: McpConfig) -> None:
    @server.tool(
        name="whoami",
        description="Who owns this API key (compact identity; no token).",
        annotations=READ_ONLY,
    )
    async def whoami(ctx: Context) -> WhoamiResult | CuratedFailure:
        client = state_of(ctx).client
        me = await client.identity.me()
        if isinstance(me, FacadeFailure):
            return to_failure(me)
        return WhoamiResult(
            id=me.id,
            name=me.name,
            email=me.email,
            role=str(getattr(me, "role", "") or "") or None,
        )

    @server.tool(
        name="find_channel",
        description=(
            "Resolve a channel by name or id. Ambiguity returns at most "
            "five labeled choices."
        ),
        annotations=READ_ONLY,
    )
    async def find_channel(
        query: str, ctx: Context
    ) -> FindChannelResult | CuratedFailure:
        client = state_of(ctx).client
        found = await client.channels.find(query)
        if isinstance(found, FacadeFailure):
            return to_failure(found)
        return FindChannelResult(
            summary=found.summary,
            channel=ChannelInfo(
                id=found.channel.id,
                name=found.channel.name,
                channel_type=found.channel.channel_type,
            ),
        )

    @server.tool(
        name="find_user",
        description=(
            "Resolve a user by id, email, or name. Ambiguity returns at "
            "most five labeled choices."
        ),
        annotations=READ_ONLY,
    )
    async def find_user(query: str, ctx: Context) -> FindUserResult | CuratedFailure:
        client = state_of(ctx).client
        found = await client.users.find(query)
        if isinstance(found, FacadeFailure):
            return to_failure(found)
        return FindUserResult(
            summary=found.summary,
            user=UserInfo(
                id=found.user.id,
                name=found.user.name,
                email=found.user.email,
            ),
        )

    @server.tool(
        name="list_channels",
        description="List channels (compact; default 10, max 50).",
        annotations=READ_ONLY,
    )
    async def list_channels(
        ctx: Context,
        limit: Limit = DEFAULT_LIMIT,
        name_contains: str | None = None,
    ) -> ListChannelsResult | CuratedFailure:
        client = state_of(ctx).client
        entries = await client.channels.list()
        if isinstance(entries, FacadeFailure):
            return to_failure(entries)
        channels = [entry.channel for entry in entries]
        if name_contains:
            needle = name_contains.lower()
            channels = [
                channel for channel in channels if needle in channel.name.lower()
            ]
        selected = channels[:limit]
        return ListChannelsResult(
            channels=[
                ChannelInfo(
                    id=channel.id,
                    name=channel.name,
                    channel_type=str(channel.channel_type),
                )
                for channel in selected
            ],
            count=len(selected),
            truncated=len(channels) > limit,
        )

    @server.tool(
        name="search_messages",
        description=(
            "One bounded page of message search. At least one of text, "
            "from_user, or in_channel is required; never exhaustive."
        ),
        annotations=READ_ONLY,
    )
    async def search_messages(
        ctx: Context,
        text: str | None = None,
        from_user: str | None = None,
        in_channel: str | None = None,
        limit: Limit = DEFAULT_LIMIT,
    ) -> SearchResult | CuratedFailure:
        if not any(value and value.strip() for value in (text, from_user, in_channel)):
            return CuratedFailure(
                reason="invalid_request",
                summary=(
                    "search_messages requires at least one of text, "
                    "from_user, or in_channel."
                ),
                next_actions=["Pass a query, a sender, or a channel."],
            )
        client = state_of(ctx).client
        request: dict[str, Any] = {"limit": limit}
        if text and text.strip():
            request["text"] = text
        if from_user and from_user.strip():
            found = await client.users.find(from_user)
            if isinstance(found, FacadeFailure):
                return to_failure(found)
            request["from_"] = [found.user.id]
        if in_channel and in_channel.strip():
            found = await client.channels.find(in_channel)
            if isinstance(found, FacadeFailure):
                return to_failure(found)
            request["in_"] = [found.channel.id]

        page = await client.search.page(**request)
        if isinstance(page, FacadeFailure):
            return to_failure(page)
        hits = [compact_message(hit) for hit in list(page.content)[:limit]]
        return SearchResult(
            hits=hits,
            count=len(hits),
            total_elements=getattr(page, "total_elements", None),
            has_more=getattr(page, "has_more", None),
        )

    @server.tool(
        name="get_channel_context",
        description=(
            "Compact recent messages for one channel with an explicit next cursor."
        ),
        annotations=READ_ONLY,
    )
    async def get_channel_context(
        channel: str,
        ctx: Context,
        limit: Limit = DEFAULT_LIMIT,
        cursor: str | None = None,
    ) -> ChannelContextResult | CuratedFailure:
        client = state_of(ctx).client
        found = await client.channels.find(channel)
        if isinstance(found, FacadeFailure):
            return to_failure(found)
        channel_id = found.channel.id

        request: dict[str, Any] = {"channel_id": channel_id, "limit": limit}
        if cursor:
            request["cursor"] = cursor
        page = await client.messages.list(**request)
        if isinstance(page, FacadeFailure):
            return to_failure(page)
        messages = [compact_message(message) for message in list(page.messages)[:limit]]
        has_more_before = getattr(page, "has_more_before", None)
        next_cursor = messages[-1].id if messages and has_more_before is True else None
        return ChannelContextResult(
            channel_id=channel_id,
            messages=messages,
            next_cursor=next_cursor,
            resource_uri=f"pumble://channel/{channel_id}",
        )

    @server.tool(
        name="get_thread_context",
        description=("Compact thread: root, up to 50 replies, participant ids."),
        annotations=READ_ONLY,
    )
    async def get_thread_context(
        channel: str,
        message_id: str,
        ctx: Context,
        reply_limit: Limit = MAX_LIMIT,
    ) -> ThreadContextResult | CuratedFailure:
        client = state_of(ctx).client
        found = await client.channels.find(channel)
        if isinstance(found, FacadeFailure):
            return to_failure(found)
        channel_id = found.channel.id

        context = await client.threads.get_context(
            channel_id=channel_id,
            message_id=message_id,
            reply_limit=reply_limit,
        )
        if isinstance(context, FacadeFailure):
            return to_failure(context)
        return ThreadContextResult(
            channel_id=channel_id,
            root=CompactMessage(
                id=context.root.id,
                channel_id=context.root.channel_id,
                author=context.root.author,
                text=context.root.text,
                timestamp_milli=context.root.timestamp_milli,
            ),
            replies=[
                CompactMessage(
                    id=reply.id,
                    channel_id=reply.channel_id,
                    author=reply.author,
                    text=reply.text,
                    timestamp_milli=reply.timestamp_milli,
                )
                for reply in context.replies
            ],
            participants=list(context.participants),
            reply_count=context.reply_count,
            resource_uri=f"pumble://thread/{channel_id}/{message_id}",
        )
