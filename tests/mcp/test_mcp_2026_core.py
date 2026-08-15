"""P32: discover, cache hints, deterministic catalogs, routing headers."""

from __future__ import annotations

import json

import httpx
import pytest
from mcp.client.client import Client
from mcp.server.transport_security import TransportSecuritySettings

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.middleware import (
    HeaderToolPolicy,
    MethodMetricsMiddleware,
)
from pumble_keys.mcp_server.profiles import Profile
from pumble_keys.mcp_server.server import create_server
from tests.mcp.harness import mcp_session

KEY = "test-key-not-real"
HOST = "good.example.invalid"
RPC_HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
}


class FakeClient:
    async def aclose(self) -> None:
        return None


def make_server(profile: Profile = Profile.CURATED, tmp_path=None, **kwargs):
    extra = {}
    if profile is Profile.READWRITE:
        extra = {
            "allow_raw_writes": True,
            "audit_log_path": str(tmp_path / "audit.jsonl"),
        }
    return create_server(
        McpConfig(api_key=KEY, profile=profile, **extra),
        client_factory=lambda _c: FakeClient(),
        **kwargs,
    )


async def catalog_bytes(server) -> str:
    payload = {
        "tools": [tool.name for tool in await server.list_tools()],
        "resources": [str(r.uri) for r in await server.list_resources()],
        "templates": [t.uri_template for t in await server.list_resource_templates()],
        "prompts": [p.name for p in await server.list_prompts()],
    }
    return json.dumps(payload, sort_keys=True)


class TestDiscoverAndCatalogs:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "profile",
        [
            Profile.CURATED,
            Profile.CURATED_INTERACTIVE,
            Profile.READONLY,
            Profile.READWRITE,
        ],
    )
    async def test_discover_snapshot_per_profile(self, profile, tmp_path) -> None:
        server = make_server(profile, tmp_path)
        async with Client(server, mode="auto") as client:
            discover = await client.session.discover()
            listed = await client.list_tools()
            server_info = client.server_info
        assert server_info is not None
        assert server_info.name == "pumble-keys"
        assert "2026-07-28" in discover.supported_versions
        capabilities = discover.capabilities
        assert capabilities.tools is not None
        assert capabilities.prompts is not None
        assert capabilities.resources is not None
        assert capabilities.completions is not None
        # No deprecated capabilities are advertised.
        dumped = discover.model_dump()
        assert dumped.get("capabilities", {}).get("logging") is None
        assert [t.name for t in listed.tools] == [
            t.name for t in await server.list_tools()
        ]

    @pytest.mark.asyncio
    async def test_modern_discover_then_call_without_initialize(self) -> None:
        # The modern per-request-envelope path: no initialize handshake,
        # discover then call, entirely SDK-provided.
        server = make_server()
        async with Client(server, mode="2026-07-28") as client:
            tools = await client.list_tools()
            assert len(tools.tools) > 0

    @pytest.mark.asyncio
    async def test_legacy_handshake_fixture_still_works(self) -> None:
        # Dual-era support: the memory-stream harness speaks the legacy
        # initialize handshake against the very same server object.
        server = make_server()
        async with mcp_session(server) as session:
            listed = await session.list_tools()
        assert [t.name for t in listed.tools] == [
            t.name for t in await server.list_tools()
        ]

    @pytest.mark.asyncio
    async def test_catalogs_byte_stable_across_fresh_servers(self, tmp_path) -> None:
        for profile in (Profile.CURATED, Profile.READONLY):
            first = await catalog_bytes(make_server(profile, tmp_path))
            second = await catalog_bytes(make_server(profile, tmp_path))
            assert first == second

    @pytest.mark.asyncio
    async def test_repeated_list_calls_identical_in_one_session(self) -> None:
        server = make_server()
        async with mcp_session(server) as session:
            first = await session.list_tools()
            second = await session.list_tools()
        assert [t.name for t in first.tools] == [t.name for t in second.tools]


class TestCacheHints:
    @pytest.mark.asyncio
    async def test_catalog_results_carry_private_conservative_ttl(self) -> None:
        server = make_server()
        async with Client(server, mode="auto") as client:
            tools = await client.list_tools()
            prompts = await client.list_prompts()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            discover = await client.session.discover()
        for result in (tools, prompts, resources, templates, discover):
            assert result.ttl_ms == 60_000, type(result).__name__
            assert result.cache_scope == "private", type(result).__name__

    @pytest.mark.asyncio
    async def test_live_resource_reads_are_short_private(self) -> None:
        server = make_server()
        async with Client(server, mode="auto") as client:
            read = await client.read_resource("pumble://knowledge/index.md")
        assert read.ttl_ms == 5_000
        assert read.cache_scope == "private"


class TestRoutingHeaders:
    def http_app(self, server, denied=frozenset()):
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[HOST],
            allowed_origins=[f"http://{HOST}"],
        )
        app = server.streamable_http_app(
            stateless_http=True, transport_security=security
        )
        return HeaderToolPolicy(app, denied_tools=denied)

    @pytest.mark.asyncio
    async def test_headers_deny_named_raw_write_before_body_parse(
        self, tmp_path
    ) -> None:
        server = make_server(Profile.READWRITE, tmp_path)
        app = self.http_app(server, denied=frozenset({"raw_delete_message"}))

        body_reads = 0

        async def counting_receive():
            nonlocal body_reads
            body_reads += 1
            return {"type": "http.request", "body": b"{}", "more_body": False}

        sent = []

        async def capture_send(message):
            sent.append(message)

        async with server.session_manager.run():
            await app(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/mcp",
                    "headers": [
                        (b"host", HOST.encode()),
                        (b"mcp-method", b"tools/call"),
                        (b"mcp-name", b"raw_delete_message"),
                    ],
                },
                counting_receive,
                capture_send,
            )
        assert sent[0]["status"] == 403
        assert body_reads == 0  # denied before any body read

    @pytest.mark.asyncio
    async def test_allowed_calls_pass_through_with_headers(self, tmp_path) -> None:
        server = make_server(Profile.READWRITE, tmp_path)
        app = self.http_app(server, denied=frozenset({"raw_delete_message"}))
        async with server.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as client:
                response = await client.post(
                    "/mcp",
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    headers={**RPC_HEADERS, "mcp-method": "tools/list"},
                )
        assert response.status_code == 200


class TestContextMiddleware:
    @pytest.mark.asyncio
    async def test_method_metrics_middleware_counts_routes(self) -> None:
        metrics = MethodMetricsMiddleware()
        server = make_server(middleware=[metrics])
        async with mcp_session(server) as session:
            await session.list_tools()
            await session.list_tools()
            await session.list_prompts()
        assert metrics.method_counts["tools/list"] == 2
        assert metrics.method_counts["prompts/list"] == 1
        assert metrics.method_counts["initialize"] >= 1
