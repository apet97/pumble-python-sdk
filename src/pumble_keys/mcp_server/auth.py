"""Remote authorization: official ``TokenVerifier``/``AuthSettings`` wiring.

The server acts as an OAuth *resource server*. It never implements an
authorization server or custom dynamic client registration — deploy a
standards-compliant AS and point the settings at it. Verification is
provider-neutral: any object satisfying the official ``TokenVerifier``
protocol works (configure a dotted path via
``PUMBLE_MCP_TOKEN_VERIFIER``).
"""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field
from typing import Any, cast

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

__all__ = [
    "AccessToken",
    "AuthSettings",
    "StaticTokenVerifier",
    "TokenVerifier",
    "build_auth_settings",
    "load_token_verifier",
]


def build_auth_settings(
    *,
    issuer_url: str,
    resource_server_url: str,
    required_scopes: list[str] | None = None,
) -> AuthSettings:
    """Protected-resource metadata: issuer, resource URL, scopes."""
    return AuthSettings(
        issuer_url=issuer_url,  # type: ignore[arg-type]
        resource_server_url=resource_server_url,  # type: ignore[arg-type]
        required_scopes=required_scopes,
    )


@dataclass
class StaticTokenVerifier:
    """Development/test verifier over an explicit token table.

    NOT for production: it compares opaque strings. Production
    deployments supply a real verifier (JWKS/introspection) through
    ``load_token_verifier``. Unknown, expired, or wrong-audience tokens
    fail closed (``None`` → HTTP 401 from the SDK middleware).
    """

    tokens: dict[str, AccessToken] = field(default_factory=dict)
    now: Any = time.time

    async def verify_token(self, token: str) -> AccessToken | None:
        access = self.tokens.get(token)
        if access is None:
            return None
        if access.expires_at is not None and access.expires_at <= int(self.now()):
            return None
        return access


def load_token_verifier(spec: str) -> TokenVerifier:
    """Import a verifier from a ``module:attribute`` spec.

    The attribute may be a ``TokenVerifier`` instance or a zero-argument
    factory returning one.
    """
    module_name, _, attribute = spec.partition(":")
    if not module_name or not attribute:
        raise ValueError(
            "token verifier spec must look like 'package.module:attribute'"
        )
    module = importlib.import_module(module_name)
    candidate = getattr(module, attribute)
    if hasattr(candidate, "verify_token"):
        return cast("TokenVerifier", candidate)
    if callable(candidate):
        try:
            verifier = candidate()
        except TypeError as error:
            raise TypeError(f"{spec} did not produce a TokenVerifier") from error
        if hasattr(verifier, "verify_token"):
            return cast("TokenVerifier", verifier)
    raise TypeError(f"{spec} did not produce a TokenVerifier (no verify_token)")
