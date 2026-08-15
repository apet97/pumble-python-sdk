"""Hand-written MCP server (official ``mcp`` SDK v2, protocol 2026-07-28).

The server is composed from one deterministic factory
(``pumble_keys.mcp_server.server.create_server``); profiles decide which
tools, resources, prompts, and extensions register.
"""

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.profiles import Profile
from pumble_keys.mcp_server.server import create_server

__all__ = ["McpConfig", "Profile", "create_server"]
