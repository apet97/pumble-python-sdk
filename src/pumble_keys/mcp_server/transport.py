"""Transport policy: stdio locally, stateless Streamable HTTP remotely.

SSE is superseded and deliberately absent. A non-loopback HTTP bind
fails closed unless a token verifier is configured or the explicit,
noisy ``--unsafe-no-auth`` development flag is set.
"""

from __future__ import annotations

import ipaddress
import sys
from dataclasses import dataclass, field
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 2718
DEFAULT_HTTP_PATH = "/mcp"
DEFAULT_MAX_BODY_BYTES = 4 * 1024 * 1024  # keep the SDK's 4 MiB default

SUPPORTED_TRANSPORTS = ("stdio", "streamable-http")


class TransportConfigError(Exception):
    pass


@dataclass(frozen=True)
class TransportOptions:
    transport: str = "stdio"
    host: str = DEFAULT_HTTP_HOST
    port: int = DEFAULT_HTTP_PORT
    path: str = DEFAULT_HTTP_PATH
    allowed_hosts: tuple[str, ...] = ()
    allowed_origins: tuple[str, ...] = ()
    unsafe_no_auth: bool = False
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    stateless: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


def is_loopback_host(host: str) -> bool:
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_transport(options: TransportOptions, *, has_auth: bool) -> None:
    """Fail closed before any socket binds."""
    if options.transport == "sse":
        raise TransportConfigError(
            "the SSE transport is superseded and not supported; use streamable-http"
        )
    if options.transport not in SUPPORTED_TRANSPORTS:
        raise TransportConfigError(
            f"unsupported transport {options.transport!r}; expected one of: "
            f"{', '.join(SUPPORTED_TRANSPORTS)}"
        )
    if options.transport == "streamable-http" and not is_loopback_host(options.host):
        if not has_auth and not options.unsafe_no_auth:
            raise TransportConfigError(
                f"refusing to bind {options.host}:{options.port} without an "
                "OAuth token verifier; configure one or pass the "
                "development-only --unsafe-no-auth flag"
            )
        if not has_auth and options.unsafe_no_auth:
            sys.stderr.write(
                "WARNING: --unsafe-no-auth set — the MCP server is "
                f"exposed on {options.host}:{options.port} with NO "
                "authorization. Development use only.\n"
            )


def transport_security(options: TransportOptions) -> TransportSecuritySettings:
    """DNS-rebinding protection: Host/Origin allowlists."""
    allowed_hosts = list(options.allowed_hosts) or [
        f"{options.host}:{options.port}",
        f"localhost:{options.port}",
        f"127.0.0.1:{options.port}",
    ]
    allowed_origins = list(options.allowed_origins) or [
        f"http://{host}" for host in allowed_hosts
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def run_server(
    server: MCPServer,
    options: TransportOptions,
    *,
    has_auth: bool,
    runner: Any = None,
) -> None:
    """Validate, then hand off to the official SDK runner.

    ``runner`` injects a fake for tests; the default calls the SDK.
    """
    validate_transport(options, has_auth=has_auth)

    if options.transport == "stdio":
        if runner is not None:
            runner(server, transport="stdio")
            return
        server.run(transport="stdio")
        return

    kwargs: dict[str, Any] = {
        "host": options.host,
        "port": options.port,
        "streamable_http_path": options.path,
        "stateless_http": options.stateless,
        "max_request_body_size": options.max_body_bytes,
        "transport_security": transport_security(options),
        **options.extra,
    }
    if runner is not None:
        runner(server, transport="streamable-http", **kwargs)
        return
    server.run(transport="streamable-http", **kwargs)
