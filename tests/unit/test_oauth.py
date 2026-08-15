"""P22: Pumble OAuth helpers — URL building, form request, callback checks."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from pumble_keys.pumble_app.oauth import (
    PUMBLE_OAUTH_ACCESS_TOKEN_URL,
    PUMBLE_OAUTH_CONSENT_URL,
    create_pumble_oauth_access_token_request,
    create_pumble_oauth_authorization_url,
    verify_pumble_oauth_callback,
)


def params_of(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query, keep_blank_values=True)


def test_authorization_url_defaults_and_scope_joining() -> None:
    url = create_pumble_oauth_authorization_url(
        client_id="client-1",
        redirect_url="https://app.example.invalid/callback?x=1",
        user_scopes=["messages:read"],
        bot_scopes=["messages:write", "channels:read"],
    )
    assert url.startswith(PUMBLE_OAUTH_CONSENT_URL)
    params = params_of(url)
    assert params["clientId"] == ["client-1"]
    assert params["redirectUrl"] == ["https://app.example.invalid/callback?x=1"]
    assert params["scopes"] == ["messages:read,bot:messages:write,bot:channels:read"]
    assert "defaultWorkspaceId" not in params
    assert "state" not in params
    assert "isReinstall" not in params


def test_authorization_url_optional_fields() -> None:
    url = create_pumble_oauth_authorization_url(
        client_id="client-1",
        redirect_url="https://app.example.invalid/cb",
        user_scopes=["messages:read"],
        default_workspace_id="0" * 20 + "0001",
        state="opaque-state",
        is_reinstall=True,
    )
    params = params_of(url)
    assert params["defaultWorkspaceId"] == ["0" * 20 + "0001"]
    assert params["state"] == ["opaque-state"]
    assert params["isReinstall"] == ["true"]


def test_authorization_url_requires_a_scope() -> None:
    with pytest.raises(ValueError, match="at least one user or bot scope"):
        create_pumble_oauth_authorization_url(
            client_id="c", redirect_url="https://x.example.invalid"
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"client_id": " ", "redirect_url": "https://x.example.invalid"},
        {"client_id": "c", "redirect_url": "   "},
    ],
)
def test_authorization_url_blank_fields_rejected(kwargs) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        create_pumble_oauth_authorization_url(user_scopes=["messages:read"], **kwargs)


def test_access_token_request_form_fields() -> None:
    request = create_pumble_oauth_access_token_request(
        client_id="client-1", client_secret="secret-1", code="code-1"
    )
    assert request.url == PUMBLE_OAUTH_ACCESS_TOKEN_URL
    assert request.method == "POST"
    assert request.form == {
        "client-id": "client-1",
        "client-secret": "secret-1",
        "code": "code-1",
    }


def test_access_token_request_blank_fields_rejected() -> None:
    for kwargs in (
        {"client_id": "", "client_secret": "s", "code": "c"},
        {"client_id": "i", "client_secret": " ", "code": "c"},
        {"client_id": "i", "client_secret": "s", "code": ""},
    ):
        with pytest.raises(ValueError, match="must not be empty"):
            create_pumble_oauth_access_token_request(**kwargs)


def test_callback_extraction_and_state() -> None:
    callback = verify_pumble_oauth_callback(
        "https://app.example.invalid/cb?code=abc&state=xyz",
        expected_state="xyz",
    )
    assert callback.code == "abc"
    assert callback.state == "xyz"

    no_state = verify_pumble_oauth_callback("https://app.example.invalid/cb?code=abc")
    assert no_state.state is None


def test_callback_missing_code_rejected() -> None:
    with pytest.raises(ValueError, match="missing code"):
        verify_pumble_oauth_callback("https://app.example.invalid/cb?state=x")


def test_callback_state_mismatch_rejected() -> None:
    for url in (
        "https://app.example.invalid/cb?code=abc&state=wrong",
        "https://app.example.invalid/cb?code=abc",
    ):
        with pytest.raises(ValueError, match="state mismatch"):
            verify_pumble_oauth_callback(url, expected_state="right")


def test_url_encoding_of_special_characters() -> None:
    url = create_pumble_oauth_authorization_url(
        client_id="client 1&x",
        redirect_url="https://x.example.invalid/cb?a=b c",
        user_scopes=["messages:read"],
    )
    params = params_of(url)
    assert params["clientId"] == ["client 1&x"]
    assert params["redirectUrl"] == ["https://x.example.invalid/cb?a=b c"]
