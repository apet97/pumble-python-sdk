"""The one Pumble MCP App: extension factory and packaged UI asset.

`create_apps_extension` builds the official ``Apps()`` extension with
exactly one ``ui://`` resource — the self-contained HTML built from
``app/`` (P35) and packaged under ``app_assets/`` — plus the tools from
``app_tools``. The resource declares a strict CSP (no external connect
or resource domains) and requests no iframe permissions; the metadata
is the modern nested ``_meta.ui`` form only.
"""

from __future__ import annotations

from importlib import resources as importlib_resources

from mcp.server.apps import Apps, ResourceCsp

from pumble_keys.mcp_server.app_tools import (
    APP_RESOURCE_URI,
    register_app_tools,
)
from pumble_keys.mcp_server.config import McpConfig


def load_app_html() -> str:
    """The packaged single-file app HTML."""
    root = importlib_resources.files("pumble_keys.mcp_server.app_assets")
    return (root / "index.html").read_text(encoding="utf-8")


def create_apps_extension(_config: McpConfig) -> Apps:
    """One discoverable interactive app with a strict, closed CSP."""
    apps = Apps()
    register_app_tools(apps)
    apps.add_html_resource(
        APP_RESOURCE_URI,
        load_app_html(),
        name="pumble-workspace-app",
        title="Pumble workspace",
        description=(
            "Interactive Pumble workspace: browse, search, and send "
            "with preview/confirm."
        ),
        csp=ResourceCsp(connect_domains=[], resource_domains=[]),
    )
    return apps
