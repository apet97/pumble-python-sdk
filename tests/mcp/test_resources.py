"""P29: resources — bounded payloads, safe paths, deterministic lists."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.resources import (
    EVENT_GUIDES,
    knowledge_root,
    resolve_knowledge_path,
)
from pumble_keys.mcp_server.server import create_server
from tests.mcp.harness import mcp_session

CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0002"
MESSAGE_ID = "0" * 20 + "0003"


class Recorder:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.value


def fake_message(mid=MESSAGE_ID):
    import datetime

    return SimpleNamespace(
        id=mid,
        channel_id=CHANNEL_ID,
        author=USER_ID,
        text="[redacted] text",
        timestamp=datetime.datetime(2026, 8, 15, tzinfo=datetime.UTC),
        timestamp_milli=1_786_752_000_000,
        thread_root_info=None,
    )


def make_raw(**overrides):
    r = {
        "my_info": Recorder(
            SimpleNamespace(
                id=USER_ID,
                name="User 1",
                email="user-1@example.invalid",
                role="MEMBER",
            )
        ),
        "list_channels": Recorder(
            [
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id=f"{i:024d}", name=f"chan-{i}", channel_type="PUBLIC"
                    )
                )
                for i in range(150)
            ]
        ),
        "list_messages": Recorder(
            SimpleNamespace(
                result=SimpleNamespace(
                    messages=[fake_message(f"{i:024d}") for i in range(40)],
                    has_more_before=True,
                    has_more_after=None,
                )
            )
        ),
        "fetch_message": Recorder(fake_message()),
        "fetch_thread_replies": Recorder(SimpleNamespace(result=[fake_message("r1")])),
    }
    r.update(overrides)
    return SimpleNamespace(
        users=SimpleNamespace(
            my_info_async=r["my_info"], list_users_async=Recorder([])
        ),
        channels=SimpleNamespace(list_channels_async=r["list_channels"]),
        messages=SimpleNamespace(
            list_messages_async=r["list_messages"],
            fetch_message_async=r["fetch_message"],
            fetch_thread_replies_async=r["fetch_thread_replies"],
        ),
        _recorders=r,
    )


def make_server(**overrides):
    from pumble_keys.extensions.client import create_pumble_client

    raw = make_raw(**overrides)
    return create_server(
        McpConfig(api_key="test-key-not-real"),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )


async def read_json(session, uri: str):
    result = await session.read_resource(uri)
    content = result.contents[0]
    return content, json.loads(content.text)


@pytest.mark.asyncio
async def test_resource_lists_are_deterministic() -> None:
    server = make_server()
    static = [str(r.uri) for r in await server.list_resources()]
    templates = [t.uri_template for t in await server.list_resource_templates()]
    assert static == [
        "ui://pumble/workspace/v1/index.html",  # P36 Apps extension
        "pumble://me",
        "pumble://channels",
    ]
    assert templates == [
        "pumble://channel/{channel_id}",
        "pumble://thread/{channel_id}/{message_id}",
        "pumble://knowledge/{+path}",
        "pumble://events/{name}",
    ]
    again = make_server()
    assert [str(r.uri) for r in await again.list_resources()] == static
    assert [t.uri_template for t in await again.list_resource_templates()] == templates


@pytest.mark.asyncio
async def test_me_and_channels_are_compact_and_bounded() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        content, me = await read_json(session, "pumble://me")
        assert content.mime_type == "application/json"
        assert me == {
            "ok": True,
            "id": USER_ID,
            "name": "User 1",
            "email": "user-1@example.invalid",
            "role": "MEMBER",
        }

        _content, catalog = await read_json(session, "pumble://channels")
        assert catalog["count"] == 100  # bounded catalog
        assert catalog["truncated"] is True
        assert set(catalog["channels"][0]) == {"id", "name", "channel_type"}


@pytest.mark.asyncio
async def test_channel_and_thread_context_bounded() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        _content, channel = await read_json(session, f"pumble://channel/{CHANNEL_ID}")
        assert channel["channel_id"] == CHANNEL_ID
        assert len(channel["messages"]) == 20  # capped

        _content, thread = await read_json(
            session, f"pumble://thread/{CHANNEL_ID}/{MESSAGE_ID}"
        )
        assert thread["root"]["id"] == MESSAGE_ID
        assert [reply["id"] for reply in thread["replies"]] == ["r1"]
        assert thread["participants"] == [USER_ID]


@pytest.mark.asyncio
async def test_live_resource_failure_is_structured_json() -> None:
    server = make_server(my_info=Recorder(error=ConnectionError("down")))
    async with mcp_session(server) as session:
        _content, payload = await read_json(session, "pumble://me")
    assert payload["ok"] is False
    assert payload["reason"] == "transport_error"


@pytest.mark.asyncio
async def test_knowledge_resource_serves_markdown() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        result = await session.read_resource("pumble://knowledge/index.md")
        content = result.contents[0]
        assert content.mime_type == "text/markdown"
        assert "Pumble MCP server knowledge" in content.text

        nested = await session.read_resource("pumble://knowledge/guides/safe-writes.md")
        assert "preview" in nested.contents[0].text


class TestKnowledgeContainment:
    def test_traversal_rejected(self) -> None:
        for path in (
            "../secrets.md",
            "guides/../../secrets.md",
            "..%2Fsecrets.md",
        ):
            with pytest.raises((ValueError, FileNotFoundError)):
                resolve_knowledge_path(path)

    def test_absolute_and_null_rejected(self) -> None:
        with pytest.raises(ValueError, match="not allowed"):
            resolve_knowledge_path("/etc/passwd")
        with pytest.raises(ValueError, match="not allowed"):
            resolve_knowledge_path("a\x00b.md")
        with pytest.raises(ValueError, match="not allowed"):
            resolve_knowledge_path("")

    def test_unsupported_extension_rejected(self) -> None:
        with pytest.raises(ValueError, match="extension"):
            resolve_knowledge_path("index.py")

    def test_missing_file_rejected(self) -> None:
        with pytest.raises(FileNotFoundError):
            resolve_knowledge_path("missing.md")

    def test_symlink_escape_rejected(self, tmp_path) -> None:
        outside = tmp_path / "outside.md"
        outside.write_text("secret outside content")
        link = knowledge_root() / "escape-link.md"
        try:
            os.symlink(outside, link)
            with pytest.raises(ValueError, match="escapes the root"):
                resolve_knowledge_path("escape-link.md")
        finally:
            if link.is_symlink():
                link.unlink()


@pytest.mark.asyncio
async def test_event_guides_all_seven_and_unknown() -> None:
    server = make_server()
    assert sorted(EVENT_GUIDES) == [
        "APP_UNAUTHORIZED",
        "APP_UNINSTALLED",
        "CHANNEL_CREATED",
        "NEW_MESSAGE",
        "REACTION_ADDED",
        "UPDATED_MESSAGE",
        "WORKSPACE_USER_JOINED",
    ]
    async with mcp_session(server) as session:
        _content, guide = await read_json(session, "pumble://events/NEW_MESSAGE")
        assert guide["event"] == "NEW_MESSAGE"
        assert guide["example"]["ty"] == "NEW_MESSAGE"
        assert "tx" in guide["fields"]

        with pytest.raises(Exception, match="events/MYSTERY"):
            await session.read_resource("pumble://events/MYSTERY")
