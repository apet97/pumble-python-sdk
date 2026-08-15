"""``pumble-keys-mcp`` — start the MCP server.

Secrets never ride on argv: the API key, confirmation secret, and any
verifier credentials come from the environment (see ``McpConfig``).
Exit codes: 0 clean shutdown, 1 startup/config failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from pumble_keys.mcp_server.auth import (
    build_auth_settings,
    load_token_verifier,
)
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server
from pumble_keys.mcp_server.transport import (
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PATH,
    DEFAULT_HTTP_PORT,
    SUPPORTED_TRANSPORTS,
    TransportConfigError,
    TransportOptions,
    run_server,
)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise UsageError(message)


class UsageError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="pumble-keys-mcp",
        description="Run the Pumble MCP server (stdio or Streamable HTTP).",
        epilog=(
            "Secrets come from the environment only: PUMBLE_API_KEY / "
            "PUMBLE_API_KEY_FILE, PUMBLE_CONFIRMATION_SECRET, and "
            "PUMBLE_MCP_TOKEN_VERIFIER (module:attribute). SSE is not "
            "supported."
        ),
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        help=f"one of: {', '.join(SUPPORTED_TRANSPORTS)} (default: stdio)",
    )
    parser.add_argument("--host", default=DEFAULT_HTTP_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_HTTP_PORT)
    parser.add_argument("--path", default=DEFAULT_HTTP_PATH)
    parser.add_argument(
        "--allowed-host",
        action="append",
        default=[],
        help="Host-header allowlist entry (repeatable)",
    )
    parser.add_argument(
        "--allowed-origin",
        action="append",
        default=[],
        help="Origin-header allowlist entry (repeatable)",
    )
    parser.add_argument(
        "--unsafe-no-auth",
        action="store_true",
        help="DEVELOPMENT ONLY: allow a non-loopback bind without OAuth",
    )
    parser.add_argument("--profile", default=None)
    parser.add_argument("--allow-raw-writes", action="store_true")
    parser.add_argument("--audit-log", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auth-issuer", default=None)
    parser.add_argument("--auth-resource-url", default=None)
    parser.add_argument(
        "--auth-scope", action="append", default=[], help="required scope"
    )
    return parser


def _forbid_secret_flags(argv: list[str]) -> None:
    for arg in argv:
        flag = arg.split("=", 1)[0]
        if flag in ("--api-key", "--api-key-auth", "--confirmation-secret"):
            raise UsageError(
                f"{flag} is not accepted: pass secrets through the "
                "environment, never argv"
            )


def main(argv: list[str] | None = None, *, runner: Any = None) -> int:
    active_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    try:
        _forbid_secret_flags(active_argv)
        args = parser.parse_args(active_argv)

        overrides: dict[str, Any] = {}
        if args.profile is not None:
            overrides["profile"] = args.profile
        if args.allow_raw_writes:
            overrides["allow_raw_writes"] = True
        if args.audit_log is not None:
            overrides["audit_log_path"] = args.audit_log
        if args.dry_run:
            overrides["dry_run"] = True
        config = McpConfig.from_env(**overrides)

        verifier = None
        verifier_spec = os.environ.get("PUMBLE_MCP_TOKEN_VERIFIER")
        if verifier_spec:
            verifier = load_token_verifier(verifier_spec)

        server_kwargs: dict[str, Any] = {}
        if verifier is not None:
            if not (args.auth_issuer and args.auth_resource_url):
                raise UsageError(
                    "a token verifier requires --auth-issuer and "
                    "--auth-resource-url (protected-resource metadata)"
                )
            server_kwargs["token_verifier"] = verifier
            server_kwargs["auth"] = build_auth_settings(
                issuer_url=args.auth_issuer,
                resource_server_url=args.auth_resource_url,
                required_scopes=args.auth_scope or None,
            )

        server = create_server(config, **server_kwargs)
        options = TransportOptions(
            transport=args.transport,
            host=args.host,
            port=args.port,
            path=args.path,
            allowed_hosts=tuple(args.allowed_host),
            allowed_origins=tuple(args.allowed_origin),
            unsafe_no_auth=args.unsafe_no_auth,
        )
        run_server(server, options, has_auth=verifier is not None, runner=runner)
        return 0
    except UsageError as error:
        sys.stderr.write(f"pumble-keys-mcp: {error}\n")
        return 2
    except (TransportConfigError, ValueError) as error:
        sys.stderr.write(f"pumble-keys-mcp: {error}\n")
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
