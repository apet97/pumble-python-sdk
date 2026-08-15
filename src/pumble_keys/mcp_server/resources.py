"""MCP resources: bounded live context, packaged knowledge, event guides.

- ``pumble://me`` — compact current identity.
- ``pumble://channels`` — bounded channel catalog.
- ``pumble://channel/{channel_id}`` — compact recent messages.
- ``pumble://thread/{channel_id}/{message_id}`` — compact thread.
- ``pumble://knowledge/{+path}`` — packaged Markdown with strict path
  containment (resolved beneath the knowledge root; no traversal,
  absolute paths, symlink escapes, or unsupported extensions).
- ``pumble://events/{name}`` — typed example/schema guidance for the
  seven Pumble webhook events.

Live payloads are compact and bounded; static knowledge is
deterministic and versioned with the package.
"""

from __future__ import annotations

import json
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.tools.read import compact_message, state_of

CHANNEL_CATALOG_LIMIT = 100
CHANNEL_MESSAGE_LIMIT = 20
THREAD_REPLY_LIMIT = 50
KNOWLEDGE_EXTENSIONS = frozenset({".md", ".txt"})

EVENT_GUIDES: dict[str, dict[str, Any]] = {
    "NEW_MESSAGE": {
        "description": "A message was posted.",
        "fields": {
            "aId": "author user/app id",
            "cId": "channel id",
            "mId": "message id",
            "tx": "message text",
            "eph": "true for ephemeral messages",
        },
        "example": {
            "ty": "NEW_MESSAGE",
            "wId": "0" * 20 + "0001",
            "aId": "0" * 20 + "0002",
            "cId": "0" * 20 + "0003",
            "mId": "0" * 20 + "0004",
            "tx": "[redacted]",
            "eph": False,
        },
    },
    "UPDATED_MESSAGE": {
        "description": "A message was edited.",
        "fields": {"mId": "message id", "cId": "channel id", "e": "edited"},
        "example": {
            "ty": "UPDATED_MESSAGE",
            "cId": "0" * 20 + "0003",
            "mId": "0" * 20 + "0004",
            "tx": "[redacted]",
            "e": True,
        },
    },
    "REACTION_ADDED": {
        "description": "A reaction was added to a message.",
        "fields": {
            "cId": "channel id",
            "mId": "message id",
            "uId": "reacting user id",
            "rc": "reaction code, e.g. :+1:",
        },
        "example": {
            "ty": "REACTION_ADDED",
            "cId": "0" * 20 + "0003",
            "mId": "0" * 20 + "0004",
            "uId": "0" * 20 + "0002",
            "rc": ":+1:",
        },
    },
    "CHANNEL_CREATED": {
        "description": "A channel was created.",
        "fields": {
            "cId": "channel id",
            "cN": "channel name",
            "cT": "channel type",
            "cU": "member user ids",
        },
        "example": {
            "ty": "CHANNEL_CREATED",
            "cId": "0" * 20 + "0003",
            "cN": "example-channel",
            "cT": "PUBLIC",
        },
    },
    "APP_UNINSTALLED": {
        "description": "The app was uninstalled from a workspace.",
        "fields": {"app": "app id", "workspace": "workspace id"},
        "example": {
            "ty": "APP_UNINSTALLED",
            "app": "0" * 20 + "0005",
            "workspace": "0" * 20 + "0001",
        },
    },
    "APP_UNAUTHORIZED": {
        "description": "A user revoked the app's authorization.",
        "fields": {
            "app": "app id",
            "workspaceUser": "user id",
            "accessGranted": "false on revoke",
        },
        "example": {
            "ty": "APP_UNAUTHORIZED",
            "app": "0" * 20 + "0005",
            "workspaceUser": "0" * 20 + "0002",
            "accessGranted": False,
        },
    },
    "WORKSPACE_USER_JOINED": {
        "description": "A user joined the workspace.",
        "fields": {
            "uId": "user id",
            "uN": "user name",
            "uE": "user email",
            "ro": "role",
        },
        "example": {
            "ty": "WORKSPACE_USER_JOINED",
            "wId": "0" * 20 + "0001",
            "uId": "0" * 20 + "0002",
            "uN": "User 1",
            "uE": "user-1@example.invalid",
            "ro": "MEMBER",
        },
    },
}


def knowledge_root() -> Path:
    return Path(str(importlib_resources.files("pumble_keys.knowledge")))


def resolve_knowledge_path(path: str) -> Path:
    """Strict containment: the resolved file must stay under the root."""
    if not path or path.startswith(("/", "\\")) or "\x00" in path:
        raise ValueError(f"knowledge path not allowed: {path!r}")
    root = knowledge_root().resolve()
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"knowledge path escapes the root: {path!r}")
    if candidate.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
        raise ValueError(f"unsupported knowledge extension: {path!r}")
    if not candidate.is_file():
        raise FileNotFoundError(f"knowledge file not found: {path!r}")
    return candidate


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _failure_payload(failure: FacadeFailure) -> str:
    return _json({"ok": False, "reason": failure.reason, "summary": failure.summary})


def register(server: MCPServer, _config: McpConfig) -> None:
    def server_state() -> Any:
        state = getattr(server, "pumble_app_state", None)
        if state is None:
            raise RuntimeError("server lifespan is not running")
        return state

    @server.resource(
        "pumble://me",
        name="me",
        description="Compact identity of the configured API key.",
        mime_type="application/json",
    )
    async def me() -> str:
        client = server_state().client
        identity = await client.identity.me()
        if isinstance(identity, FacadeFailure):
            return _failure_payload(identity)
        return _json(
            {
                "ok": True,
                "id": identity.id,
                "name": identity.name,
                "email": identity.email,
                "role": str(getattr(identity, "role", "") or "") or None,
            }
        )

    @server.resource(
        "pumble://channels",
        name="channels",
        description=(f"Bounded channel catalog (first {CHANNEL_CATALOG_LIMIT})."),
        mime_type="application/json",
    )
    async def channels() -> str:
        client = server_state().client
        entries = await client.channels.list()
        if isinstance(entries, FacadeFailure):
            return _failure_payload(entries)
        all_channels = [entry.channel for entry in entries]
        selected = all_channels[:CHANNEL_CATALOG_LIMIT]
        return _json(
            {
                "ok": True,
                "channels": [
                    {
                        "id": channel.id,
                        "name": channel.name,
                        "channel_type": str(channel.channel_type),
                    }
                    for channel in selected
                ],
                "count": len(selected),
                "truncated": len(all_channels) > CHANNEL_CATALOG_LIMIT,
            }
        )

    @server.resource(
        "pumble://channel/{channel_id}",
        name="channel-context",
        description=(f"Compact recent messages (last {CHANNEL_MESSAGE_LIMIT})."),
        mime_type="application/json",
    )
    async def channel_context(channel_id: str, ctx: Context) -> str:
        client = state_of(ctx).client
        page = await client.messages.list(
            channel_id=channel_id, limit=CHANNEL_MESSAGE_LIMIT
        )
        if isinstance(page, FacadeFailure):
            return _failure_payload(page)
        messages = [
            compact_message(message).model_dump()
            for message in list(page.messages)[:CHANNEL_MESSAGE_LIMIT]
        ]
        return _json({"ok": True, "channel_id": channel_id, "messages": messages})

    @server.resource(
        "pumble://thread/{channel_id}/{message_id}",
        name="thread-context",
        description=(f"Compact thread context (up to {THREAD_REPLY_LIMIT} replies)."),
        mime_type="application/json",
    )
    async def thread_context(channel_id: str, message_id: str, ctx: Context) -> str:
        client = state_of(ctx).client
        context = await client.threads.get_context(
            channel_id=channel_id,
            message_id=message_id,
            reply_limit=THREAD_REPLY_LIMIT,
        )
        if isinstance(context, FacadeFailure):
            return _failure_payload(context)
        return _json(
            {
                "ok": True,
                "channel_id": channel_id,
                "root": context.root.__dict__,
                "replies": [reply.__dict__ for reply in context.replies],
                "participants": list(context.participants),
                "reply_count": context.reply_count,
            }
        )

    @server.resource(
        "pumble://knowledge/{+path}",
        name="knowledge",
        description="Packaged server documentation (Markdown).",
        mime_type="text/markdown",
    )
    async def knowledge(path: str) -> str:
        return resolve_knowledge_path(path).read_text(encoding="utf-8")

    @server.resource(
        "pumble://events/{name}",
        name="event-guide",
        description=(
            "Field guide and sanitized example for one of the seven "
            "Pumble webhook events."
        ),
        mime_type="application/json",
    )
    async def event_guide(name: str) -> str:
        guide = EVENT_GUIDES.get(name)
        if guide is None:
            raise ValueError(
                f"unknown event {name!r}; expected one of: "
                + ", ".join(sorted(EVENT_GUIDES))
            )
        return _json({"event": name, **guide})
