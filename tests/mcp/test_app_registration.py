"""P36: the one MCP App — opening tool, ui:// resource, app-only helpers."""

from __future__ import annotations

import hashlib
import json
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
    def __init__(self, value=None) -> None:
        self.value = value
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.value


def make_raw():
    me = SimpleNamespace(
        id=USER_ID, name="Probe User", email="probe@example.invalid", role="MEMBER"
    )
    return SimpleNamespace(
        users=SimpleNamespace(
            my_info_async=Recorder(me),
            list_users_async=Recorder([me]),
        ),
        channels=SimpleNamespace(
            list_channels_async=Recorder(
                [
                    SimpleNamespace(
                        channel=SimpleNamespace(
                            id=CHANNEL_ID,
                            name="engineering",
                            channel_type="PUBLIC",
                        )
                    )
                ]
            )
        ),
        messages=SimpleNamespace(
            list_messages_async=Recorder(SimpleNamespace(result=[])),
        ),
    )


def make_server(profile: Profile = Profile.CURATED):
    return create_server(
        McpConfig(api_key=KEY, profile=profile),
        client_factory=lambda _c: create_pumble_client(raw=make_raw()),
    )


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
