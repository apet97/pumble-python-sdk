"""P36: the one MCP App — opening tool, ui:// resource, app-only helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.client.client import Client
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.mcp_server.app import load_app_html
from pumble_keys.mcp_server.app_tools import (
    APP_RESOURCE_URI,
    OPEN_TOOL_NAME,
)
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.profiles import Profile
from pumble_keys.mcp_server.server import create_server

KEY = "test-key-not-real"
CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0009"
APP_ONLY_TOOLS = [
    "pumble_ui_bootstrap",
    "pumble_ui_channel_page",
    "pumble_ui_thread",
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


def fake_message(mid="m-1"):
    return SimpleNamespace(
        id=mid,
        channel_id=CHANNEL_ID,
        author=USER_ID,
        text="hello",
        timestamp_milli=1_786_752_000_000,
    )


def make_raw(**overrides):
    me = SimpleNamespace(
        id=USER_ID, name="Probe User", email="probe@example.invalid", role="MEMBER"
    )
    r = {
        "my_info": Recorder(me),
        "list_users": Recorder([me]),
        "list_channels": Recorder(
            [
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id=CHANNEL_ID,
                        name="engineering",
                        channel_type="PUBLIC",
                    )
                )
            ]
        ),
        "list_messages": Recorder(
            SimpleNamespace(result=SimpleNamespace(messages=[], has_more_before=False))
        ),
    }
    r.update(overrides)
    # The default raw mock deliberately has NO thread surface: the
    # existing thread-failure test relies on its absence. Overrides add it.
    messages = SimpleNamespace(list_messages_async=r["list_messages"])
    if "fetch_message" in r:
        messages.fetch_message_async = r["fetch_message"]
    if "fetch_thread_replies" in r:
        messages.fetch_thread_replies_async = r["fetch_thread_replies"]
    return SimpleNamespace(
        users=SimpleNamespace(
            my_info_async=r["my_info"],
            list_users_async=r["list_users"],
        ),
        channels=SimpleNamespace(list_channels_async=r["list_channels"]),
        messages=messages,
        _recorders=r,
    )


def make_server(profile: Profile = Profile.CURATED):
    return create_server(
        McpConfig(api_key=KEY, profile=profile),
        client_factory=lambda _c: create_pumble_client(raw=make_raw()),
    )


def make_server_and_recorders(**overrides):
    raw = make_raw(**overrides)
    server = create_server(
        McpConfig(api_key=KEY, profile=Profile.CURATED),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )
    return server, raw._recorders


@pytest.mark.asyncio
async def test_extension_advertised_on_app_profiles_only() -> None:
    curated = make_server()
    async with Client(curated, mode="auto") as client:
        discover = await client.session.discover()
    assert EXTENSION_ID in (discover.capabilities.extensions or {})

    readonly = make_server(Profile.READONLY)
    async with Client(readonly, mode="auto") as client:
        discover = await client.session.discover()
    assert EXTENSION_ID not in (discover.capabilities.extensions or {})
    names = {tool.name for tool in await readonly.list_tools()}
    assert OPEN_TOOL_NAME not in names
    assert not names.intersection(APP_ONLY_TOOLS)


@pytest.mark.asyncio
async def test_opening_tool_binding_and_visibility() -> None:
    server = make_server()
    async with Client(server, mode="auto") as client:
        listed = await client.list_tools()
    tools = {tool.name: tool for tool in listed.tools}

    opening = tools[OPEN_TOOL_NAME]
    ui = (opening.meta or {})["ui"]
    assert ui["resourceUri"] == APP_RESOURCE_URI
    # Modern nested metadata only — no pre-GA flat key.
    assert "ui/resourceUri" not in (opening.meta or {})
    assert opening.annotations.read_only_hint is True
    assert "visibility" not in ui  # model-visible

    for name in APP_ONLY_TOOLS:
        ui = (tools[name].meta or {})["ui"]
        assert ui["resourceUri"] == APP_RESOURCE_URI
        assert ui["visibility"] == ["app"]


@pytest.mark.asyncio
async def test_ui_resource_mime_csp_and_content() -> None:
    server = make_server()
    async with Client(server, mode="auto") as client:
        listed = await client.list_resources()
        resources = {str(r.uri): r for r in listed.resources}
        resource = resources[APP_RESOURCE_URI]
        assert resource.mime_type == APP_MIME_TYPE
        ui = (resource.meta or {})["ui"]
        assert ui["csp"] == {"connectDomains": [], "resourceDomains": []}
        assert "permissions" not in ui

        read = await client.read_resource(APP_RESOURCE_URI)
        content = read.contents[0]
        assert content.mime_type == APP_MIME_TYPE
        assert content.text == load_app_html()
        assert content.text.lstrip().lower().startswith("<!doctype html")


def test_packaged_asset_matches_the_built_app() -> None:
    built = Path(__file__).resolve().parents[2] / "app" / "dist" / "index.html"
    if not built.exists():
        pytest.skip("app/dist/index.html not built in this environment")
    packaged = hashlib.sha256(load_app_html().encode()).hexdigest()
    assert hashlib.sha256(built.read_bytes()).hexdigest() == packaged


@pytest.mark.asyncio
async def test_opening_tool_fallback_without_apps_support() -> None:
    server = make_server()
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(OPEN_TOOL_NAME, {})
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["identity"] == {"id": USER_ID, "name": "Probe User"}
    assert payload["channel_count"] == 1
    assert payload["capabilities"]["apps"] is False
    # Text fallback for non-UI clients mirrors the structured payload.
    text = result.content[0].text
    assert "Probe User" in text
    assert json.loads(text)["ok"] is True


@pytest.mark.asyncio
async def test_channel_page_helper_passes_cursor_and_limits() -> None:
    server = make_server()
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_channel_page",
            {"channel_id": CHANNEL_ID, "cursor": "m-5", "limit": 10},
        )
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["channel_id"] == CHANNEL_ID
    assert payload["messages"] == []
    assert payload["next_cursor"] is None


@pytest.mark.asyncio
async def test_thread_helper_failure_stays_a_value() -> None:
    server = make_server()
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_thread",
            {"channel_id": CHANNEL_ID, "message_id": "m-missing"},
        )
    # The mock raw client has no thread surface: the façade categorizes
    # the error into a structured value; the call itself never errors.
    assert result.is_error is not True
    assert result.structured_content["ok"] is False


@pytest.mark.asyncio
async def test_bootstrap_returns_identity_channels_and_user_map() -> None:
    server, _ = make_server_and_recorders()
    async with Client(server, mode="auto") as client:
        result = await client.call_tool("pumble_ui_bootstrap", {})
    payload = result.structured_content
    assert payload == {
        "ok": True,
        "identity": {"id": USER_ID, "name": "Probe User"},
        "channels": [
            {"id": CHANNEL_ID, "name": "engineering", "channel_type": "PUBLIC"}
        ],
        "users": {USER_ID: "Probe User"},
    }


@pytest.mark.asyncio
async def test_bootstrap_identity_failure_is_a_value() -> None:
    server, _ = make_server_and_recorders(
        my_info=Recorder(error=ConnectionError("down"))
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool("pumble_ui_bootstrap", {})
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["reason"] == "transport_error"


@pytest.mark.asyncio
async def test_bootstrap_user_map_skips_blank_ids_and_names() -> None:
    me = SimpleNamespace(
        id=USER_ID, name="Probe User", email="probe@example.invalid", role="MEMBER"
    )
    blank = SimpleNamespace(id="", name="", email="")
    server, _ = make_server_and_recorders(list_users=Recorder([blank, me]))
    async with Client(server, mode="auto") as client:
        result = await client.call_tool("pumble_ui_bootstrap", {})
    assert result.structured_content["users"] == {USER_ID: "Probe User"}


@pytest.mark.asyncio
async def test_bootstrap_user_list_failure_degrades_to_empty_map() -> None:
    server, _ = make_server_and_recorders(
        list_users=Recorder(error=ConnectionError("down"))
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool("pumble_ui_bootstrap", {})
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["users"] == {}
    assert payload["channels"][0]["id"] == CHANNEL_ID


@pytest.mark.asyncio
async def test_bootstrap_channel_list_failure_is_a_value() -> None:
    server, _ = make_server_and_recorders(
        list_channels=Recorder(error=ConnectionError("down"))
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool("pumble_ui_bootstrap", {})
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["reason"] == "transport_error"


@pytest.mark.asyncio
async def test_opening_tool_identity_failure_is_a_value() -> None:
    server, _ = make_server_and_recorders(
        my_info=Recorder(error=ConnectionError("down"))
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(OPEN_TOOL_NAME, {})
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["reason"] == "transport_error"


@pytest.mark.asyncio
async def test_opening_tool_channel_failure_drops_channel_count() -> None:
    server, _ = make_server_and_recorders(
        list_channels=Recorder(error=ConnectionError("down"))
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(OPEN_TOOL_NAME, {})
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["channel_count"] is None
    assert payload["summary"] == "Pumble workspace ready for Probe User."


@pytest.mark.asyncio
async def test_channel_page_helper_without_cursor_omits_it() -> None:
    server, recorders = make_server_and_recorders()
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_channel_page",
            {"channel_id": CHANNEL_ID, "limit": 5},
        )
    assert result.structured_content["ok"] is True
    assert recorders["list_messages"].calls == [{"channel_id": CHANNEL_ID, "limit": 5}]


@pytest.mark.asyncio
async def test_channel_page_helper_failure_is_a_value() -> None:
    server, _ = make_server_and_recorders(
        list_messages=Recorder(error=ConnectionError("down"))
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_channel_page", {"channel_id": CHANNEL_ID}
        )
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["reason"] == "transport_error"


@pytest.mark.asyncio
async def test_channel_page_helper_sets_next_cursor_when_more_before() -> None:
    server, _ = make_server_and_recorders(
        list_messages=Recorder(
            SimpleNamespace(
                result=SimpleNamespace(
                    messages=[fake_message("m-1"), fake_message("m-2")],
                    has_more_before=True,
                )
            )
        )
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_channel_page", {"channel_id": CHANNEL_ID}
        )
    payload = result.structured_content
    assert payload["ok"] is True
    assert [message["id"] for message in payload["messages"]] == ["m-1", "m-2"]
    assert payload["next_cursor"] == "m-2"


def thread_surface():
    """Raw-thread mock shape mirroring tests/unit/test_threads.py."""
    root = SimpleNamespace(
        id="m-root",
        channel_id=CHANNEL_ID,
        author=USER_ID,
        text="root text",
        timestamp=datetime(2026, 8, 15, tzinfo=UTC),
        timestamp_milli=1_786_752_000_000,
        thread_root_info=SimpleNamespace(reply_count=1),
    )
    reply = SimpleNamespace(
        id="r1",
        channel_id=CHANNEL_ID,
        author="0" * 20 + "0007",
        text="reply text",
        timestamp=datetime(2026, 8, 15, tzinfo=UTC),
        timestamp_milli=1_786_752_000_001,
        thread_root_info=None,
    )
    return {
        "fetch_message": Recorder(root),
        "fetch_thread_replies": Recorder(SimpleNamespace(result=[reply])),
    }


@pytest.mark.asyncio
async def test_thread_helper_success_compacts_root_and_replies() -> None:
    server, _ = make_server_and_recorders(**thread_surface())
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_thread",
            {"channel_id": CHANNEL_ID, "message_id": "m-root"},
        )
    payload = result.structured_content
    assert payload["ok"] is True
    assert payload["channel_id"] == CHANNEL_ID
    assert payload["root"]["id"] == "m-root"
    assert [reply["id"] for reply in payload["replies"]] == ["r1"]
    assert payload["participants"] == [USER_ID, "0" * 20 + "0007"]


@pytest.mark.asyncio
async def test_thread_helper_facade_failure_maps_to_curated_failure() -> None:
    # Patch the façade seam directly: the returned FacadeFailure reaches
    # the tool without a real suspension, so the branch is also traced
    # under coverage. Observed on 3.11.11: lines after an await were not
    # traced when an exception was raised and caught below the
    # suspension point (mechanism not fully diagnosed).
    from pumble_keys.extensions.results import FacadeFailure

    def factory(_config):
        client = create_pumble_client(raw=make_raw())

        async def get_context(**_kwargs):
            return FacadeFailure(
                reason="api_error",
                summary="Pumble API operation fetchThreadReplies failed.",
                next_actions=("Retry after correcting the request.",),
            )

        client.threads.get_context = get_context
        return client

    server = create_server(
        McpConfig(api_key=KEY, profile=Profile.CURATED), client_factory=factory
    )
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_thread",
            {"channel_id": CHANNEL_ID, "message_id": "m-root"},
        )
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["reason"] == "api_error"


@pytest.mark.asyncio
async def test_thread_helper_transport_failure_is_a_value() -> None:
    surface = thread_surface()
    surface["fetch_message"] = Recorder(error=ConnectionError("down"))
    server, _ = make_server_and_recorders(**surface)
    async with Client(server, mode="auto") as client:
        result = await client.call_tool(
            "pumble_ui_thread",
            {"channel_id": CHANNEL_ID, "message_id": "m-root"},
        )
    assert result.is_error is not True
    payload = result.structured_content
    assert payload["ok"] is False
    assert payload["reason"] == "transport_error"
