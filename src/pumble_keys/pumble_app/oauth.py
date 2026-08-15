"""Pumble OAuth helpers: consent URL, access-token request, callback check.

Ported from ``extensions/app/oauth.ts``. These helpers cover Pumble's
app-installation OAuth flow; they are unrelated to MCP OAuth (P26).
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

PUMBLE_OAUTH_CONSENT_URL = "https://app.pumble.com/access-request"
PUMBLE_OAUTH_ACCESS_TOKEN_URL = "https://api-ga.pumble.com/oauth2/access"


def _required(name: str, value: str) -> str:
    if not value.strip():
        raise ValueError(f"Pumble OAuth {name} must not be empty")
    return value


def create_pumble_oauth_authorization_url(
    *,
    client_id: str,
    redirect_url: str,
    user_scopes: list[str] | tuple[str, ...] = (),
    bot_scopes: list[str] | tuple[str, ...] = (),
    default_workspace_id: str | None = None,
    state: str | None = None,
    is_reinstall: bool = False,
    consent_url: str = PUMBLE_OAUTH_CONSENT_URL,
) -> str:
    """Build the consent URL. Bot scopes get the ``bot:`` prefix."""
    if len(user_scopes) + len(bot_scopes) == 0:
        raise ValueError(
            "Pumble OAuth authorization URL requires at least one user or bot scope"
        )

    params: list[tuple[str, str]] = [
        ("redirectUrl", _required("redirectUrl", redirect_url)),
        ("clientId", _required("clientId", client_id)),
        (
            "scopes",
            ",".join([*user_scopes, *(f"bot:{scope}" for scope in bot_scopes)]),
        ),
    ]
    if default_workspace_id is not None:
        params.append(("defaultWorkspaceId", default_workspace_id))
    if state is not None:
        params.append(("state", state))
    if is_reinstall:
        params.append(("isReinstall", "true"))

    parts = urlsplit(consent_url)
    existing = parse_qs(parts.query, keep_blank_values=True)
    merged = [
        (key, value) for key, values in existing.items() for value in values
    ] + params
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(merged),
            parts.fragment,
        )
    )


@dataclass(frozen=True)
class PumbleOAuthAccessTokenRequest:
    """POST this as multipart/form-data to exchange the code."""

    url: str
    method: str
    form: dict[str, str]


def create_pumble_oauth_access_token_request(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    token_url: str = PUMBLE_OAUTH_ACCESS_TOKEN_URL,
) -> PumbleOAuthAccessTokenRequest:
    """Build the access-token form request (fields ``client-id``,
    ``client-secret``, ``code``)."""
    return PumbleOAuthAccessTokenRequest(
        url=token_url,
        method="POST",
        form={
            "client-id": _required("clientId", client_id),
            "client-secret": _required("clientSecret", client_secret),
            "code": _required("code", code),
        },
    )


@dataclass(frozen=True)
class PumbleOAuthCallback:
    code: str
    state: str | None = None


def verify_pumble_oauth_callback(
    callback_url: str,
    *,
    expected_state: str | None = None,
) -> PumbleOAuthCallback:
    """Extract and verify the callback ``code``/``state``.

    State comparison is constant-time.
    """
    parts = urlsplit(callback_url)
    query = parse_qs(parts.query, keep_blank_values=True)
    codes = query.get("code", [])
    code = codes[0] if codes else ""
    if not code:
        raise ValueError("Pumble OAuth callback is missing code")

    states = query.get("state", [])
    state = states[0] if states else None
    if expected_state is not None and (
        state is None
        or not hmac.compare_digest(
            state.encode("utf-8"), expected_state.encode("utf-8")
        )
    ):
        raise ValueError("Pumble OAuth callback state mismatch")

    return PumbleOAuthCallback(code=code, state=state)
