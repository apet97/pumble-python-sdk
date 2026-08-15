"""Bounded argument completions for prompts and resource templates.

Completions cover channel names, user names/emails, event names, and
knowledge paths. Results are deterministic (API list order / sorted
static lists), bounded to ``COMPLETION_LIMIT`` values, and never
contain API keys or message text. An empty resolver cache simply
yields fewer suggestions — completions never fail a request.
"""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp_types import Completion, PromptReference, ResourceTemplateReference

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.resources import (
    EVENT_GUIDES,
    KNOWLEDGE_EXTENSIONS,
    knowledge_root,
)

COMPLETION_LIMIT = 20


def _bounded(values: list[str], partial: str) -> Completion:
    needle = partial.lower()
    matches = [value for value in values if needle in value.lower()]
    selected = matches[:COMPLETION_LIMIT]
    return Completion(
        values=selected,
        total=len(matches),
        has_more=len(matches) > COMPLETION_LIMIT,
    )


def knowledge_paths() -> list[str]:
    root = knowledge_root()
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in KNOWLEDGE_EXTENSIONS
    )


async def _channel_names(state: Any) -> list[str]:
    entries = await state.client.channels.list()
    if isinstance(entries, FacadeFailure):
        return []
    return [entry.channel.name for entry in entries]


async def _user_values(state: Any) -> list[str]:
    users = await state.client.users.list()
    if isinstance(users, FacadeFailure):
        return []
    values: list[str] = []
    for user in users:
        if user.name:
            values.append(user.name)
        if user.email:
            values.append(user.email)
    return values


def register(server: MCPServer, _config: McpConfig) -> None:
    @server.completion()
    async def complete(ref: Any, argument: Any, _context: Any) -> Completion | None:
        partial = argument.value or ""

        if isinstance(ref, ResourceTemplateReference):
            template = ref.uri
            if template.startswith("pumble://events/"):
                return _bounded(sorted(EVENT_GUIDES), partial)
            if template.startswith("pumble://knowledge/"):
                return _bounded(knowledge_paths(), partial)
            return None

        if isinstance(ref, PromptReference):
            state = getattr(server, "pumble_app_state", None)
            if ref.name == "write_pumble_handler" and argument.name == "event":
                return _bounded(sorted(EVENT_GUIDES), partial)
            if state is None:
                return None
            if argument.name in ("channel", "channel_id"):
                return _bounded(await _channel_names(state), partial)
            if argument.name in ("user", "from_user"):
                return _bounded(await _user_values(state), partial)
        return None
