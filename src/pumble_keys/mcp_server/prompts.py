"""The four curated prompts.

Ported from the TypeScript curated prompts with the handler guidance
rewritten for Python (async ``PumbleApp``, Pydantic events, ASGI) —
never TypeScript syntax. Prompts are deterministic; ``draft_reply``
drafts only and never implies a message was sent.
"""

from __future__ import annotations

import json

from mcp.server import MCPServer

from pumble_keys.mcp_server.config import McpConfig

PROMPT_NAMES = (
    "summarize_thread",
    "draft_reply",
    "write_pumble_handler",
    "debug_pumble_webhook",
)


def _thread_uri(channel_id: str, message_id: str) -> str:
    return f"pumble://thread/{channel_id}/{message_id}"


def register(server: MCPServer, _config: McpConfig) -> None:
    @server.prompt(
        name="summarize_thread",
        description="Summarize a Pumble thread from its curated thread resource.",
    )
    def summarize_thread(channel_id: str, message_id: str, focus: str = "") -> str:
        effective_focus = (
            focus.strip() or "key decisions, blockers, owners, and unresolved questions"
        )
        return (
            f"Read {_thread_uri(channel_id, message_id)} before answering.\n"
            f"Summarize the thread with focus on {effective_focus}.\n"
            "Report only facts from the thread; do not invent participants "
            "or decisions.\n"
            "Do not send messages or modify Pumble. If follow-up "
            "communication is needed, draft it for the user only."
        )

    @server.prompt(
        name="draft_reply",
        description="Draft a safe Pumble thread reply without sending it.",
    )
    def draft_reply(channel_id: str, message_id: str, reply_goal: str = "") -> str:
        goal = reply_goal.strip() or "write a concise, context-aware reply"
        return (
            f"Read {_thread_uri(channel_id, message_id)} before drafting.\n"
            f"Draft a thread reply that satisfies this goal: {goal}.\n"
            "Do not send the reply yourself and do not claim it was sent.\n"
            "If the user chooses to send, call reply_to_thread_preview "
            "first, show the preview and confirmation token, and only after "
            "explicit user confirmation call reply_to_thread_confirmed with "
            "the unchanged request, preview, and token."
        )

    @server.prompt(
        name="write_pumble_handler",
        description="Generate a typed Python handler skeleton for a Pumble event.",
    )
    def write_pumble_handler(event: str) -> str:
        return (
            f'Write a Python async handler for Pumble event "{event}".\n'
            "\n"
            "1. Read the typed payload guide via the MCP resource "
            f"`pumble://events/{event}`.\n"
            "2. Use `pumble_keys.pumble_app.PumbleApp` and register the "
            "handler with `@app.event(...)`; the handler receives a typed "
            f"Pydantic `Notification*` body for {event} and a context "
            "dict.\n"
            "3. Mount the webhook ingress with `app.asgi_app()` or "
            "`app.starlette_route(path)`; signature verification is built "
            "in — never parse the body before it.\n"
            "4. Handle errors explicitly: return early on missing fields, "
            "and let unexpected exceptions surface (the receiver maps them "
            "to HTTP 500 and your on_error callback).\n"
            "5. Do not call `ack()` or assume slash-command semantics — "
            "those belong to the upstream OAuth-app SDK, not the API-Keys "
            "add-on."
        )

    @server.prompt(
        name="debug_pumble_webhook",
        description=(
            "Walk through an unknown Pumble webhook payload using the "
            "curated MCP knowledge resources."
        ),
    )
    def debug_pumble_webhook(payload_json: str) -> str:
        try:
            json.loads(payload_json)
        except ValueError as error:
            raise ValueError("payload_json must be parseable JSON") from error
        return (
            "Identify this Pumble payload step by step:\n"
            "\n"
            "```json\n"
            f"{payload_json}\n"
            "```\n"
            "\n"
            "1. Identify the event from the top-level `ty` (or `eventType`) "
            "discriminator; the compact field glossary is `aId` author, "
            "`cId` channel, `mId` message, `tx` text, `eph` ephemeral, "
            "`wId` workspace.\n"
            "2. Read the matching `pumble://events/{name}` resource and map "
            "the payload fields to the typed `Notification*` shape.\n"
            "3. Call out which fields are present, missing, or suspicious "
            "(wrong shape, mismatched id format, redacted-looking "
            "values).\n"
            "4. Never ask for signing secrets or API keys in chat; "
            "signature problems are diagnosed from the timestamp and "
            "signature headers plus the raw-body handling rules in "
            "`pumble://knowledge/guides/safe-writes.md`.\n"
            "5. Output: the event type, the parsed key fields, and any "
            "anomalies you found."
        )
