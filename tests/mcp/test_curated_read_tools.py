"""P27: curated read tools — manifest, bounds, compact payloads, failures."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server
from tests.mcp.harness import mcp_session, structured

CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0002"
MESSAGE_ID = "0" * 20 + "0003"
KEY = "test-key-not-real"

EXPECTED_TOOLS = [
    "whoami",
    "find_channel",
    "find_user",
    "list_channels",
    "search_messages",
    "get_channel_context",
    "get_thread_context",
    "send_message_preview",
    "send_message_confirmed",
    "reply_to_thread_preview",
    "reply_to_thread_confirmed",
]


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
    return SimpleNamespace(
        id=mid,
        channel_id=CHANNEL_ID,
        author=USER_ID,
        text="[redacted] text",
        timestamp_milli=1_786_752_000_000,
        thread_root_info=None,
        timestamp=None,
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
        "list_users": Recorder(
            [SimpleNamespace(id=USER_ID, name="User 1", email="user-1@example.invalid")]
        ),
        "list_channels": Recorder(
            [
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id=CHANNEL_ID,
                        name="engineering",
                        channel_type="PUBLIC",
                    )
                ),
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id="0" * 20 + "0009",
                        name="random",
                        channel_type="PUBLIC",
                    )
                ),
            ]
        ),
        "search_messages": Recorder(
            SimpleNamespace(
                result=SimpleNamespace(
                    content=[fake_message()],
                    total_elements=1,
                    has_more=False,
                )
            )
        ),
        "list_messages": Recorder(
            SimpleNamespace(
                result=SimpleNamespace(
                    messages=[fake_message()],
                    has_more_before=True,
                    has_more_after=None,
                )
            )
        ),
        "fetch_message": Recorder(
            SimpleNamespace(
                id=MESSAGE_ID,
                channel_id=CHANNEL_ID,
                author=USER_ID,
                text="root text",
                timestamp=__import__("datetime").datetime(
                    2026, 8, 15, tzinfo=__import__("datetime").timezone.utc
                ),
                timestamp_milli=1_786_752_000_000,
                thread_root_info=SimpleNamespace(reply_count=2),
            )
        ),
        "fetch_thread_replies": Recorder(
            SimpleNamespace(
                result=[
                    SimpleNamespace(
                        id="r1",
                        channel_id=CHANNEL_ID,
                        author="0" * 20 + "0007",
                        text="reply text",
                        timestamp=__import__("datetime").datetime(
                            2026,
                            8,
                            15,
                            tzinfo=__import__("datetime").timezone.utc,
                        ),
                        timestamp_milli=1_786_752_000_001,
                    )
                ]
            )
        ),
    }
    r.update(overrides)
    return SimpleNamespace(
        users=SimpleNamespace(
            my_info_async=r["my_info"], list_users_async=r["list_users"]
        ),
        channels=SimpleNamespace(list_channels_async=r["list_channels"]),
        messages=SimpleNamespace(
            search_messages_async=r["search_messages"],
            list_messages_async=r["list_messages"],
            fetch_message_async=r["fetch_message"],
            fetch_thread_replies_async=r["fetch_thread_replies"],
        ),
        _recorders=r,
    )


def make_server(**overrides):
    from pumble_keys.extensions.client import create_pumble_client

    raw = make_raw(**overrides)
    return (
        create_server(
            McpConfig(api_key=KEY),
            client_factory=lambda _c: create_pumble_client(raw=raw),
        ),
        raw._recorders,
    )


@pytest.mark.asyncio
async def test_manifest_names_order_and_annotations() -> None:
    server, _ = make_server()
    tools = await server.list_tools()
    assert [tool.name for tool in tools] == EXPECTED_TOOLS
    for tool in tools:
        if tool.name.endswith("_confirmed"):
            continue  # write annotations proven in test_curated_write_tools
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.idempotent_hint is True
        assert tool.annotations.open_world_hint is False


@pytest.mark.asyncio
async def test_limit_schema_bounds() -> None:
    server, _ = make_server()
    tools = {tool.name: tool for tool in await server.list_tools()}
    limit_schema = tools["list_channels"].input_schema["properties"]["limit"]
    assert limit_schema["default"] == 10
    assert limit_schema["maximum"] == 50
    assert limit_schema["minimum"] == 1


@pytest.mark.asyncio
async def test_whoami_compact_and_no_secret() -> None:
    server, _ = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool("whoami", {})
    payload = structured(result)
    assert payload == {
        "ok": True,
        "id": USER_ID,
        "name": "User 1",
        "email": "user-1@example.invalid",
        "role": "MEMBER",
    }
    assert KEY not in json.dumps(payload)


@pytest.mark.asyncio
async def test_find_channel_success_and_failure_value() -> None:
    server, _ = make_server()
    async with mcp_session(server) as session:
        found = await session.call_tool("find_channel", {"query": "engineering"})
        missing = await session.call_tool("find_channel", {"query": "ghost"})
    assert found.is_error is False
    assert structured(found)["channel"]["id"] == CHANNEL_ID

    # Normal not-found is a structured value, not a protocol error.
    assert missing.is_error is False
    assert structured(missing)["ok"] is False
    assert structured(missing)["reason"] == "not_found"


@pytest.mark.asyncio
async def test_find_user_ambiguity_choices_capped() -> None:
    users = [
        SimpleNamespace(id=f"{i:024d}", name="Twin", email=f"t{i}@example.invalid")
        for i in range(1, 9)
    ]
    server, _ = make_server(list_users=Recorder(users))
    async with mcp_session(server) as session:
        result = await session.call_tool("find_user", {"query": "Twin"})
    payload = structured(result)
    assert payload["reason"] == "ambiguous"
    assert len(payload["choices"]) == 5
    assert all(choice["label"] for choice in payload["choices"])


@pytest.mark.asyncio
async def test_list_channels_filter_and_truncation() -> None:
    server, _ = make_server()
    async with mcp_session(server) as session:
        all_channels = await session.call_tool("list_channels", {})
        filtered = await session.call_tool(
            "list_channels", {"name_contains": "eng", "limit": 1}
        )
    assert structured(all_channels)["count"] == 2
    assert structured(filtered)["channels"][0]["name"] == "engineering"
    assert structured(filtered)["truncated"] is False


@pytest.mark.asyncio
async def test_search_requires_a_filter_and_stays_bounded() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        empty = await session.call_tool("search_messages", {})
        page = await session.call_tool("search_messages", {"text": "alert", "limit": 5})
    assert structured(empty)["reason"] == "invalid_request"
    assert recorders["search_messages"].calls == [{"text": "alert", "limit": 5}]
    payload = structured(page)
    assert payload["count"] == 1
    assert payload["hits"][0]["id"] == MESSAGE_ID
    # One page only: never an exhaustive walk.
    assert len(recorders["search_messages"].calls) == 1


@pytest.mark.asyncio
async def test_search_over_limit_is_rejected_by_schema() -> None:
    server, _ = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool("search_messages", {"text": "x", "limit": 51})
    assert result.is_error is True  # schema bound, not a Pumble call


@pytest.mark.asyncio
async def test_get_channel_context_cursor_and_resource_uri() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool(
            "get_channel_context", {"channel": "engineering", "limit": 1}
        )
    payload = structured(result)
    assert payload["channel_id"] == CHANNEL_ID
    assert payload["messages"][0]["text"] == "[redacted] text"
    assert payload["next_cursor"] == MESSAGE_ID  # has_more_before was true
    assert payload["resource_uri"] == f"pumble://channel/{CHANNEL_ID}"
    assert recorders["list_messages"].calls == [{"channel_id": CHANNEL_ID, "limit": 1}]


@pytest.mark.asyncio
async def test_get_thread_context_compact() -> None:
    server, _ = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool(
            "get_thread_context",
            {"channel": "engineering", "message_id": MESSAGE_ID},
        )
    payload = structured(result)
    assert payload["root"]["id"] == MESSAGE_ID
    assert payload["replies"][0]["id"] == "r1"
    assert payload["participants"] == [USER_ID, "0" * 20 + "0007"]
    assert payload["reply_count"] == 2
    assert payload["resource_uri"] == (f"pumble://thread/{CHANNEL_ID}/{MESSAGE_ID}")


@pytest.mark.asyncio
async def test_api_failure_is_structured_value() -> None:
    server, _ = make_server(my_info=Recorder(error=ConnectionError("down")))
    async with mcp_session(server) as session:
        result = await session.call_tool("whoami", {})
    assert result.is_error is False
    assert structured(result)["reason"] == "transport_error"


@pytest.mark.asyncio
async def test_no_oversized_payloads() -> None:
    big_channel_list = Recorder(
        [
            SimpleNamespace(
                channel=SimpleNamespace(
                    id=f"{i:024d}", name=f"chan-{i}", channel_type="PUBLIC"
                )
            )
            for i in range(500)
        ]
    )
    server, _ = make_server(list_channels=big_channel_list)
    async with mcp_session(server) as session:
        result = await session.call_tool("list_channels", {"limit": 50})
    payload = structured(result)
    assert payload["count"] == 50
    assert payload["truncated"] is True
