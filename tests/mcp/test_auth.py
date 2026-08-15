"""P26: auth building blocks — verifier behavior and settings."""

from __future__ import annotations

import pytest

from pumble_keys.mcp_server.auth import (
    AccessToken,
    StaticTokenVerifier,
    build_auth_settings,
    load_token_verifier,
)


def token(**overrides) -> AccessToken:
    payload = {
        "token": "good-token-not-real",
        "client_id": "client-1",
        "scopes": ["pumble:read"],
    }
    payload.update(overrides)
    return AccessToken(**payload)


@pytest.mark.asyncio
async def test_static_verifier_accepts_known_token() -> None:
    verifier = StaticTokenVerifier(tokens={"good-token-not-real": token()})
    access = await verifier.verify_token("good-token-not-real")
    assert access is not None
    assert access.scopes == ["pumble:read"]


@pytest.mark.asyncio
async def test_static_verifier_fails_closed_on_unknown_token() -> None:
    verifier = StaticTokenVerifier()
    assert await verifier.verify_token("anything") is None


@pytest.mark.asyncio
async def test_static_verifier_rejects_expired_token() -> None:
    verifier = StaticTokenVerifier(
        tokens={"t": token(token="t", expires_at=1_000)},
        now=lambda: 2_000,
    )
    assert await verifier.verify_token("t") is None

    fresh = StaticTokenVerifier(
        tokens={"t": token(token="t", expires_at=3_000)},
        now=lambda: 2_000,
    )
    assert await fresh.verify_token("t") is not None


def test_build_auth_settings_metadata() -> None:
    settings = build_auth_settings(
        issuer_url="https://issuer.example.invalid",
        resource_server_url="https://mcp.example.invalid/mcp",
        required_scopes=["pumble:read", "pumble:write"],
    )
    assert str(settings.issuer_url).rstrip("/") == "https://issuer.example.invalid"
    assert str(settings.resource_server_url) == ("https://mcp.example.invalid/mcp")
    assert settings.required_scopes == ["pumble:read", "pumble:write"]
    # No homemade registration endpoint / DCR configuration.
    assert settings.client_registration_options is None


NOT_A_VERIFIER = "just a module-level string"


def make_verifier() -> StaticTokenVerifier:
    """Zero-argument factory used by the factory-spec test."""
    return StaticTokenVerifier()


def test_load_token_verifier_dotted_path() -> None:
    verifier = load_token_verifier("pumble_keys.mcp_server.auth:StaticTokenVerifier")
    assert hasattr(verifier, "verify_token")


def test_load_token_verifier_bad_specs() -> None:
    with pytest.raises(ValueError, match="module:attribute"):
        load_token_verifier("no-colon")
    with pytest.raises(TypeError, match="TokenVerifier"):
        load_token_verifier("json:dumps")


def test_load_token_verifier_zero_arg_factory() -> None:
    verifier = load_token_verifier(f"{__name__}:make_verifier")
    assert isinstance(verifier, StaticTokenVerifier)
    assert hasattr(verifier, "verify_token")


def test_load_token_verifier_factory_result_without_verify_token() -> None:
    # ``time.time`` is callable and returns a float — no ``verify_token``.
    with pytest.raises(TypeError, match="TokenVerifier"):
        load_token_verifier("time:time")


def test_load_token_verifier_non_callable_attribute() -> None:
    with pytest.raises(TypeError, match="TokenVerifier"):
        load_token_verifier(f"{__name__}:NOT_A_VERIFIER")
