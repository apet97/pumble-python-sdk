"""Tools of the one Pumble MCP App.

``open_pumble_workspace`` is the only model-visible entry: it opens the
app and degrades to a structured/text summary for clients without Apps
support. The ``pumble_ui_*`` helpers carry ``visibility: ["app"]`` so
the rich UI data never enlarges the model-visible tool catalog; they go
through the same façade layer as every curated tool — no second read
path, no write capability at all.
"""

from __future__ import annotations

from typing import Annotated, Any

import pydantic
from mcp.server.apps import Apps, client_supports_apps
from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.mcp_server.models import MAX_LIMIT
from pumble_keys.mcp_server.tools.read import (
    compact_message,
    state_of,
    to_failure,
)

APP_RESOURCE_URI = "ui://pumble/workspace/v1/index.html"
OPEN_TOOL_NAME = "open_pumble_workspace"

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)

Limit = Annotated[int, pydantic.Field(ge=1, le=MAX_LIMIT)]

USER_MAP_LIMIT = 200
CHANNEL_LIMIT = 200


def register_app_tools(apps: Apps) -> None:
    @apps.tool(
        resource_uri=APP_RESOURCE_URI,
        name=OPEN_TOOL_NAME,
        description=(
            "Open the interactive Pumble workspace app: browse channels, "
            "read threads, search, and send with preview/confirm. Falls "
            "back to a compact identity/channel summary on hosts without "
            "MCP Apps support."
        ),
        annotations=READ_ONLY,
    )
    async def open_pumble_workspace(ctx: Context) -> dict[str, Any]:
        state = state_of(ctx)
        me = await state.client.identity.me()
        if isinstance(me, FacadeFailure):
            return to_failure(me).model_dump(mode="json")
        entries = await state.client.channels.list()
        channel_count = (
            None if isinstance(entries, FacadeFailure) else len(list(entries))
        )
        summary = f"Pumble workspace ready for {me.name}."
        if channel_count is not None:
            summary = f"Pumble workspace ready for {me.name}: {channel_count} channels."
        return {
            "ok": True,
            "summary": summary,
            "identity": {"id": me.id, "name": me.name},
            "channel_count": channel_count,
            "capabilities": {
                "apps": client_supports_apps(ctx),
                "writes": "preview_confirm",
            },
        }

    @apps.tool(
        resource_uri=APP_RESOURCE_URI,
        visibility=["app"],
        name="pumble_ui_bootstrap",
        description="App-only: identity, channel catalog, and author map.",
        annotations=READ_ONLY,
    )
    async def pumble_ui_bootstrap(ctx: Context) -> dict[str, Any]:
        state = state_of(ctx)
        me = await state.client.identity.me()
        if isinstance(me, FacadeFailure):
            return to_failure(me).model_dump(mode="json")
        entries = await state.client.channels.list()
        if isinstance(entries, FacadeFailure):
            return to_failure(entries).model_dump(mode="json")
        users = await state.client.users.list()
        user_map: dict[str, str] = {}
        if not isinstance(users, FacadeFailure):
            for user in list(users)[:USER_MAP_LIMIT]:
                if user.id and user.name:
                    user_map[user.id] = user.name
        channels = [entry.channel for entry in entries][:CHANNEL_LIMIT]
        return {
            "ok": True,
            "identity": {"id": me.id, "name": me.name},
            "channels": [
                {
                    "id": channel.id,
                    "name": channel.name,
                    "channel_type": str(channel.channel_type),
                }
                for channel in channels
            ],
            "users": user_map,
        }

    @apps.tool(
        resource_uri=APP_RESOURCE_URI,
        visibility=["app"],
        name="pumble_ui_channel_page",
        description="App-only: one page of channel messages by exact id.",
        annotations=READ_ONLY,
    )
    async def pumble_ui_channel_page(
        channel_id: str,
        ctx: Context,
        limit: Limit = MAX_LIMIT,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        client = state_of(ctx).client
        request: dict[str, Any] = {"channel_id": channel_id, "limit": limit}
        if cursor:
            request["cursor"] = cursor
        page = await client.messages.list(**request)
        if isinstance(page, FacadeFailure):
            return to_failure(page).model_dump(mode="json")
        messages = [
            compact_message(message).model_dump()
            for message in list(page.messages)[:limit]
        ]
        has_more_before = getattr(page, "has_more_before", None)
        next_cursor = (
            messages[-1]["id"] if messages and has_more_before is True else None
        )
        return {
            "ok": True,
            "channel_id": channel_id,
            "messages": messages,
            "next_cursor": next_cursor,
        }

    @apps.tool(
        resource_uri=APP_RESOURCE_URI,
        visibility=["app"],
        name="pumble_ui_thread",
        description="App-only: one thread by exact channel and message id.",
        annotations=READ_ONLY,
    )
    async def pumble_ui_thread(
        channel_id: str,
        message_id: str,
        ctx: Context,
        reply_limit: Limit = MAX_LIMIT,
    ) -> dict[str, Any]:
        client = state_of(ctx).client
        context = await client.threads.get_context(
            channel_id=channel_id,
            message_id=message_id,
            reply_limit=reply_limit,
        )
        if isinstance(context, FacadeFailure):
            return to_failure(context).model_dump(mode="json")
        return {
            "ok": True,
            "channel_id": channel_id,
            "root": compact_message(context.root).model_dump(),
            "replies": [
                compact_message(reply).model_dump() for reply in context.replies
            ],
            "participants": list(context.participants),
        }
