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
    # P36 Apps extension tools register first (extension consumption
    # happens at server construction, before the profile registrars).
    "open_pumble_workspace",
    "pumble_ui_bootstrap",
    "pumble_ui_channel_page",
    "pumble_ui_thread",
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


@pytest.mark.parametrize(
    ("tool", "arguments", "overrides"),
    [
        ("whoami", {}, {"my_info": "error"}),
        ("find_channel", {"query": "ghost"}, {}),
        ("find_user", {"query": "ghost"}, {}),
        ("list_channels", {}, {"list_channels": "error"}),
        ("search_messages", {"text": "x"}, {"search_messages": "error"}),
        ("get_channel_context", {"channel": "engineering"}, {"list_messages": "error"}),
        (
            "get_thread_context",
            {"channel": "engineering", "message_id": MESSAGE_ID},
            {"fetch_message": "error"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_every_read_tool_maps_facade_failure_to_curated_failure(
    tool: str, arguments: dict, overrides: dict
) -> None:
    recorders = {name: Recorder(error=ConnectionError("down")) for name in overrides}
    server, _ = make_server(**recorders)
    async with mcp_session(server) as session:
        result = await session.call_tool(tool, arguments)
    assert result.is_error is False
    payload = structured(result)
    assert payload["ok"] is False
    assert payload["reason"] in ("transport_error", "not_found")
    assert payload["summary"]
    assert payload["next_actions"]


@pytest.mark.asyncio
async def test_search_resolves_from_user_and_in_channel_filters() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool(
            "search_messages",
            {"text": "alert", "from_user": "User 1", "in_channel": "engineering"},
        )
    payload = structured(result)
    assert payload["count"] == 1
    assert recorders["search_messages"].calls == [
        {
            "text": "alert",
            "limit": 10,
            "from_": [USER_ID],
            "in_": [CHANNEL_ID],
        }
    ]


@pytest.mark.asyncio
async def test_search_from_user_resolve_failure_stops_the_search() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool(
            "search_messages", {"text": "alert", "from_user": "ghost"}
        )
    payload = structured(result)
    assert payload["ok"] is False
    assert payload["reason"] == "not_found"
    assert recorders["search_messages"].calls == []


@pytest.mark.asyncio
async def test_search_in_channel_resolve_failure_stops_the_search() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool(
            "search_messages", {"text": "alert", "in_channel": "ghost"}
        )
    payload = structured(result)
    assert payload["ok"] is False
    assert payload["reason"] == "not_found"
    assert recorders["search_messages"].calls == []


@pytest.mark.asyncio
async def test_search_by_sender_alone_sends_no_text() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool("search_messages", {"from_user": "User 1"})
    payload = structured(result)
    assert payload["count"] == 1
    assert recorders["search_messages"].calls == [{"limit": 10, "from_": [USER_ID]}]


@pytest.mark.asyncio
async def test_get_channel_context_forwards_cursor() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool(
            "get_channel_context",
            {"channel": "engineering", "limit": 2, "cursor": "m-9"},
        )
    assert structured(result)["channel_id"] == CHANNEL_ID
    assert recorders["list_messages"].calls == [
        {"channel_id": CHANNEL_ID, "limit": 2, "cursor": "m-9"}
    ]


def make_server_with_client_patch(patch):
    """Server whose façade client is patched at the seam.

    The patched coroutines return a FacadeFailure without a real
    suspension, so failure branches after resolver/gather awaits are
    also traced under coverage. Observed on 3.11.11: lines after an
    await were not traced when an exception was raised and caught below
    the suspension point (mechanism not fully diagnosed).
    """
    from pumble_keys.extensions.client import create_pumble_client

    def factory(_config):
        client = create_pumble_client(raw=make_raw())
        patch(client)
        return client

    return create_server(McpConfig(api_key=KEY), client_factory=factory)


def facade_failure():
    from pumble_keys.extensions.results import FacadeFailure

    return FacadeFailure(
        reason="api_error",
        summary="Pumble API operation failed.",
        next_actions=("Retry after correcting the request.",),
    )


async def _call_patched(patch, tool: str, arguments: dict):
    server = make_server_with_client_patch(patch)
    async with mcp_session(server) as session:
        result = await session.call_tool(tool, arguments)
    assert result.is_error is False
    return structured(result)


@pytest.mark.asyncio
async def test_find_user_success_is_compact() -> None:
    server, _ = make_server()
    async with mcp_session(server) as session:
        result = await session.call_tool("find_user", {"query": "User 1"})
    payload = structured(result)
    assert payload["ok"] is True
    assert payload["user"] == {
        "id": USER_ID,
        "name": "User 1",
        "email": "user-1@example.invalid",
    }


@pytest.mark.asyncio
async def test_find_user_maps_facade_seam_failure() -> None:
    async def find(_query, **_kwargs):
        return facade_failure()

    def patch(client):
        client.users.find = find

    payload = await _call_patched(patch, "find_user", {"query": "anyone"})
    assert payload["ok"] is False
    assert payload["reason"] == "api_error"


@pytest.mark.asyncio
async def test_get_channel_context_maps_channel_find_failure() -> None:
    async def find(_query, **_kwargs):
        return facade_failure()

    def patch(client):
        client.channels.find = find

    payload = await _call_patched(patch, "get_channel_context", {"channel": "x"})
    assert payload["ok"] is False
    assert payload["reason"] == "api_error"


@pytest.mark.asyncio
async def test_get_thread_context_maps_channel_find_failure() -> None:
    async def find(_query, **_kwargs):
        return facade_failure()

    def patch(client):
        client.channels.find = find

    payload = await _call_patched(
        patch, "get_thread_context", {"channel": "x", "message_id": MESSAGE_ID}
    )
    assert payload["ok"] is False
    assert payload["reason"] == "api_error"


@pytest.mark.asyncio
async def test_get_thread_context_maps_thread_failure() -> None:
    async def get_context(**_kwargs):
        return facade_failure()

    def patch(client):
        client.threads.get_context = get_context

    payload = await _call_patched(
        patch,
        "get_thread_context",
        {"channel": "engineering", "message_id": MESSAGE_ID},
    )
    assert payload["ok"] is False
    assert payload["reason"] == "api_error"


def test_to_failure_skips_non_dict_choices() -> None:
    from pumble_keys.extensions.results import FacadeFailure
    from pumble_keys.mcp_server.tools.read import to_failure

    failure = FacadeFailure(
        reason="ambiguous",
        summary="ambiguous input",
        choices=("junk-string", {"id": "1", "label": "keep me"}),
        next_actions=("pick one",),
    )
    out = to_failure(failure)
    assert [choice.label for choice in out.choices] == ["keep me"]
