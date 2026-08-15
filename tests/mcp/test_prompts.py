"""P30: prompts — deterministic output, escaping, no secrets, safe guidance."""

from __future__ import annotations

import json

import pytest

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.prompts import PROMPT_NAMES
from pumble_keys.mcp_server.server import create_server
from tests.mcp.harness import mcp_session

CHANNEL_ID = "0" * 20 + "0001"
MESSAGE_ID = "0" * 20 + "0002"
KEY = "test-key-not-real"


class FakeClient:
    async def aclose(self) -> None:
        return None


def make_server():
    return create_server(
        McpConfig(api_key=KEY),
        client_factory=lambda _c: FakeClient(),
    )


def prompt_text(result) -> str:
    return result.messages[0].content.text


@pytest.mark.asyncio
async def test_prompt_list_is_deterministic() -> None:
    server = make_server()
    names = [prompt.name for prompt in await server.list_prompts()]
    assert names == list(PROMPT_NAMES)
    again = make_server()
    assert [p.name for p in await again.list_prompts()] == names


@pytest.mark.asyncio
async def test_summarize_thread_snapshot_and_focus() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        default = await session.get_prompt(
            "summarize_thread",
            {"channel_id": CHANNEL_ID, "message_id": MESSAGE_ID},
        )
        focused = await session.get_prompt(
            "summarize_thread",
            {
                "channel_id": CHANNEL_ID,
                "message_id": MESSAGE_ID,
                "focus": "release readiness",
            },
        )
    text = prompt_text(default)
    assert f"pumble://thread/{CHANNEL_ID}/{MESSAGE_ID}" in text
    assert "key decisions, blockers, owners, and unresolved questions" in text
    assert "do not invent" in text.lower()
    assert "release readiness" in prompt_text(focused)


@pytest.mark.asyncio
async def test_draft_reply_never_sends() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        result = await session.get_prompt(
            "draft_reply",
            {"channel_id": CHANNEL_ID, "message_id": MESSAGE_ID},
        )
    text = prompt_text(result)
    assert "Do not send the reply yourself" in text
    assert "reply_to_thread_preview" in text
    assert "explicit user confirmation" in text


@pytest.mark.asyncio
async def test_write_pumble_handler_is_python_guidance() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        result = await session.get_prompt(
            "write_pumble_handler", {"event": "NEW_MESSAGE"}
        )
    text = prompt_text(result)
    assert "Python async handler" in text
    assert "PumbleApp" in text
    assert "pumble://events/NEW_MESSAGE" in text
    assert "asgi_app" in text
    # No TypeScript syntax leaks.
    assert "typescript" not in text.lower()
    assert "import {" not in text


@pytest.mark.asyncio
async def test_debug_webhook_escapes_payload_and_asks_no_secrets() -> None:
    server = make_server()
    payload = json.dumps({"ty": "NEW_MESSAGE", "tx": "[redacted]"})
    async with mcp_session(server) as session:
        result = await session.get_prompt(
            "debug_pumble_webhook", {"payload_json": payload}
        )
    text = prompt_text(result)
    assert payload in text
    assert "Never ask for signing secrets or API keys" in text

    async with mcp_session(server) as session:
        with pytest.raises(Exception, match="parseable JSON"):
            await session.get_prompt(
                "debug_pumble_webhook", {"payload_json": "{broken"}
            )


@pytest.mark.asyncio
async def test_no_secrets_in_any_prompt_output() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        outputs = [
            prompt_text(
                await session.get_prompt(
                    "summarize_thread",
                    {"channel_id": CHANNEL_ID, "message_id": MESSAGE_ID},
                )
            ),
            prompt_text(
                await session.get_prompt(
                    "write_pumble_handler", {"event": "NEW_MESSAGE"}
                )
            ),
        ]
    for text in outputs:
        assert KEY not in text
