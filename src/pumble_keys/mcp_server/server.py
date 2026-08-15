"""Deterministic MCP server factory.

Every server is composed here: profile-selected registrars add tools,
resources, prompts, and extensions in a checked-in deterministic order.
Later packets (P27–P36) fill the registrar lists; the composition rules
never move out of this factory.

Diagnostics use Python logging (stderr) — never stdout, which belongs
to the MCP stdio wire.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.lifespan import make_lifespan
from pumble_keys.mcp_server.profiles import Profile

SERVER_NAME = "pumble-keys"
SERVER_INSTRUCTIONS = (
    "Unofficial Pumble workspace server. One Pumble workspace per "
    "deployment: every tool acts as the single configured API key. "
    "Normal not-found/ambiguity outcomes come back as structured values, "
    "not protocol errors."
)

# Registrar seats, filled by later packets in this fixed order:
#   P27 curated reads, P28 curated writes, P33 interactive,
#   P31 raw read/write + dry-run, P29 resources, P30 prompts/completions,
#   P36 app tools + Apps extension.
Registrar = Callable[[MCPServer, McpConfig], None]


def _register_curated_reads(server: MCPServer, config: McpConfig) -> None:
    from pumble_keys.mcp_server.tools import read

    read.register(server, config)


_CURATED_REGISTRARS: list[Registrar] = [_register_curated_reads]
_INTERACTIVE_REGISTRARS: list[Registrar] = []
_READONLY_REGISTRARS: list[Registrar] = []
_READWRITE_REGISTRARS: list[Registrar] = []


def registrars_for(profile: Profile) -> list[Registrar]:
    if profile is Profile.CURATED:
        return list(_CURATED_REGISTRARS)
    if profile is Profile.CURATED_INTERACTIVE:
        return [*_CURATED_REGISTRARS, *_INTERACTIVE_REGISTRARS]
    if profile is Profile.READONLY:
        return list(_READONLY_REGISTRARS)
    return [*_READONLY_REGISTRARS, *_READWRITE_REGISTRARS]


def create_server(
    config: McpConfig,
    *,
    client_factory: Any = None,
    **server_kwargs: Any,
) -> MCPServer:
    """Compose one server for the configured profile.

    ``client_factory`` injects a fake Pumble client for tests. Extra
    ``server_kwargs`` (e.g. ``token_verifier``/``auth`` in P26) pass
    through to ``MCPServer``.
    """
    server = MCPServer(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        lifespan=make_lifespan(config, client_factory=client_factory),
        log_level="WARNING",
        **server_kwargs,
    )
    for registrar in registrars_for(config.profile):
        registrar(server, config)
    return server
