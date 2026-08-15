"""P26: transport policy + HTTP-level security proofs."""

from __future__ import annotations

import httpx
import pytest
from mcp.server.transport_security import TransportSecuritySettings

from pumble_keys.mcp_server.auth import AccessToken, StaticTokenVerifier
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server
from pumble_keys.mcp_server.transport import (
    DEFAULT_MAX_BODY_BYTES,
    TransportConfigError,
    TransportOptions,
    is_loopback_host,
    run_server,
    transport_security,
    validate_transport,
)

HOST = "good.example.invalid"
RPC_HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
}
LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


class FakeClient:
    async def aclose(self) -> None:
        return None


def make_server(**server_kwargs):
    return create_server(
        McpConfig(api_key="test-key-not-real"),
        client_factory=lambda _config: FakeClient(),
        **server_kwargs,
    )


class TestPolicy:
    def test_loopback_detection(self) -> None:
        for host in ("127.0.0.1", "localhost", "::1"):
            assert is_loopback_host(host)
        for host in ("0.0.0.0", "10.0.0.5", "example.invalid"):
            assert not is_loopback_host(host)

    def test_sse_is_rejected(self) -> None:
        with pytest.raises(TransportConfigError, match="SSE.*not supported"):
            validate_transport(TransportOptions(transport="sse"), has_auth=True)

    def test_unknown_transport_rejected(self) -> None:
        with pytest.raises(TransportConfigError, match="unsupported transport"):
            validate_transport(TransportOptions(transport="websocket"), has_auth=True)

    def test_nonloopback_without_auth_fails_closed(self) -> None:
        options = TransportOptions(transport="streamable-http", host="0.0.0.0")
        with pytest.raises(TransportConfigError, match="token verifier"):
            validate_transport(options, has_auth=False)

    def test_nonloopback_with_auth_is_fine(self) -> None:
        validate_transport(
            TransportOptions(transport="streamable-http", host="0.0.0.0"),
            has_auth=True,
        )

    def test_unsafe_no_auth_warns_loudly(self, capsys) -> None:
        validate_transport(
            TransportOptions(
                transport="streamable-http",
                host="0.0.0.0",
                unsafe_no_auth=True,
            ),
            has_auth=False,
        )
        assert "WARNING" in capsys.readouterr().err

    def test_loopback_defaults_need_no_auth(self) -> None:
        validate_transport(
            TransportOptions(transport="streamable-http"), has_auth=False
        )

    def test_transport_security_defaults_and_overrides(self) -> None:
        default = transport_security(TransportOptions())
        assert default.enable_dns_rebinding_protection is True
        assert "127.0.0.1:2718" in default.allowed_hosts

        custom = transport_security(
            TransportOptions(
                allowed_hosts=("mcp.example.invalid",),
                allowed_origins=("https://mcp.example.invalid",),
            )
        )
        assert custom.allowed_hosts == ["mcp.example.invalid"]
        assert custom.allowed_origins == ["https://mcp.example.invalid"]

    def test_run_server_passes_stateless_and_body_limit(self) -> None:
        calls = []

        def runner(_server, **kwargs):
            calls.append(kwargs)

        run_server(
            make_server(),
            TransportOptions(transport="streamable-http"),
            has_auth=False,
            runner=runner,
        )
        kwargs = calls[0]
        assert kwargs["transport"] == "streamable-http"
        assert kwargs["stateless_http"] is True
        assert kwargs["max_request_body_size"] == DEFAULT_MAX_BODY_BYTES
        assert kwargs["port"] == 2718
        assert kwargs["streamable_http_path"] == "/mcp"

    def test_run_server_stdio_default(self) -> None:
        calls = []

        def runner(_server, **kwargs):
            calls.append(kwargs)

        run_server(make_server(), TransportOptions(), has_auth=False, runner=runner)
        assert calls == [{"transport": "stdio"}]


def http_app(server, **overrides):
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[HOST],
        allowed_origins=[f"http://{HOST}"],
    )
    return server.streamable_http_app(
        stateless_http=True, transport_security=security, **overrides
    )


class TestHttpLevel:
    @pytest.mark.asyncio
    async def test_stateless_call_and_host_rejection(self) -> None:
        server = make_server()
        app = http_app(server)
        async with server.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as client:
                ok = await client.post("/mcp", json=LIST_TOOLS, headers=RPC_HEADERS)
                assert ok.status_code == 200
                assert '"tools":[]' in ok.text

                bad_host = await client.post(
                    "/mcp",
                    json=LIST_TOOLS,
                    headers={**RPC_HEADERS, "host": "evil.example.invalid"},
                )
                assert bad_host.status_code == 421

                bad_origin = await client.post(
                    "/mcp",
                    json=LIST_TOOLS,
                    headers={
                        **RPC_HEADERS,
                        "origin": "http://evil.example.invalid",
                    },
                )
                assert bad_origin.status_code == 403

    @pytest.mark.asyncio
    async def test_oversized_body_is_413(self) -> None:
        server = make_server()
        app = http_app(server, max_request_body_size=64)
        async with server.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as client:
                response = await client.post(
                    "/mcp",
                    content=b"x" * 128,
                    headers=RPC_HEADERS,
                )
                assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_bearer_required_and_verified_when_auth_configured(
        self,
    ) -> None:
        verifier = StaticTokenVerifier(
            tokens={
                "good-token-not-real": AccessToken(
                    token="good-token-not-real",
                    client_id="client-1",
                    scopes=["pumble:read"],
                )
            }
        )
        from pumble_keys.mcp_server.auth import build_auth_settings

        server = make_server(
            token_verifier=verifier,
            auth=build_auth_settings(
                issuer_url="https://issuer.example.invalid",
                resource_server_url=f"http://{HOST}/mcp",
                required_scopes=["pumble:read"],
            ),
        )
        app = http_app(server)
        async with server.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as client:
                missing = await client.post(
                    "/mcp", json=LIST_TOOLS, headers=RPC_HEADERS
                )
                assert missing.status_code == 401

                wrong = await client.post(
                    "/mcp",
                    json=LIST_TOOLS,
                    headers={
                        **RPC_HEADERS,
                        "authorization": "Bearer wrong-token",
                    },
                )
                assert wrong.status_code == 401

                good = await client.post(
                    "/mcp",
                    json=LIST_TOOLS,
                    headers={
                        **RPC_HEADERS,
                        "authorization": "Bearer good-token-not-real",
                    },
                )
                assert good.status_code == 200
