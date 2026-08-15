"""Shared in-memory MCP client harness for server tests.

Runs the real server loop (initialize handshake, lifespan, request
context) over memory streams — no sockets.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import anyio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams


@asynccontextmanager
async def mcp_session(server):
    low = server._lowlevel_server
    async with (
        create_client_server_memory_streams() as (
            (client_read, client_write),
            (server_read, server_write),
        ),
        anyio.create_task_group() as task_group,
    ):

        async def run_server() -> None:
            await low.run(
                server_read,
                server_write,
                low.create_initialization_options(),
                raise_exceptions=False,
            )

        task_group.start_soon(run_server)
        async with ClientSession(client_read, client_write) as session:
            await session.initialize()
            yield session
        task_group.cancel_scope.cancel()


def structured(result):
    """Unwrap the SDK's {"result": ...} envelope for union-typed tools."""
    payload = result.structured_content
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload
