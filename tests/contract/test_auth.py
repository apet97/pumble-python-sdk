"""P06: authentication contract — `ApiKey` header and server URL."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
PRODUCTION_URL = "https://pumble-api-keys.addons.marketplace.cake.com"


def test_spec_declares_apikey_header_security() -> None:
    spec = yaml.safe_load((REPO / "PumbleOpenApi.yaml").read_text())
    schemes = spec["components"]["securitySchemes"]
    assert len(schemes) == 1
    (scheme,) = schemes.values()
    assert scheme["type"] == "apiKey"
    assert scheme["in"] == "header"
    assert scheme["name"] == "ApiKey"


def test_generated_security_targets_apikey_header() -> None:
    from pumble_keys.models import Security

    field = Security.model_fields["api_key_auth"]
    security_meta = [
        meta.security
        for meta in field.metadata
        if getattr(meta, "security", None) is not None
    ]
    assert len(security_meta) == 1
    assert security_meta[0].scheme_type == "apiKey"
    assert security_meta[0].sub_type == "header"
    assert security_meta[0].field_name == "ApiKey"


def test_request_serializes_apikey_header_and_no_authorization() -> None:
    from pumble_keys import PumbleSDK
    from pumble_keys.utils import get_security

    sdk = PumbleSDK(api_key_auth="test-key-not-real")
    security = sdk.sdk_configuration.security
    resolved = security() if callable(security) else security
    headers, query_params = get_security(resolved)
    assert headers == {"ApiKey": "test-key-not-real"}
    assert query_params == {}
    assert "Authorization" not in headers


def test_default_server_is_production_url() -> None:
    from pumble_keys import PumbleSDK
    from pumble_keys.sdkconfiguration import SERVERS

    assert SERVERS == [PRODUCTION_URL]
    sdk = PumbleSDK(api_key_auth="test-key-not-real")
    url, _ = sdk.sdk_configuration.get_server_details()
    assert url == PRODUCTION_URL


def test_server_url_is_overridable() -> None:
    from pumble_keys import PumbleSDK

    sdk = PumbleSDK(
        api_key_auth="test-key-not-real", server_url="http://localhost:9999"
    )
    url, _ = sdk.sdk_configuration.get_server_details()
    assert url == "http://localhost:9999"
