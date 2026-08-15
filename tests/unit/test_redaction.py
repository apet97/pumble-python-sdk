"""P07: redaction is deterministic, catches secrets, spares ordinary text."""

from __future__ import annotations

from pumble_keys.extensions.redaction import (
    REDACTED,
    redact_debug_headers,
    redact_debug_value,
    redact_sensitive_text,
)

CANARY_ID = "abcdefabcdefabcdefabcdef"


class TestRedactSensitiveText:
    def test_pmb_token_is_redacted(self) -> None:
        out = redact_sensitive_text("key is pmb_AbC-123_xyz here")
        assert "pmb_" not in out
        assert out == "key is [redacted] here"

    def test_bearer_and_basic_credentials(self) -> None:
        assert (
            redact_sensitive_text("Authorization: Bearer abc.DEF-123")
            == "Authorization: Bearer [redacted]"
        )
        assert "[redacted]" in redact_sensitive_text("Basic dXNlcjpwYXNz")

    def test_key_value_assignments(self) -> None:
        for text in (
            "api-key: sekret123",
            "api_key=sekret123",
            'token = "sekret123"',
            "secret: 'sekret123'",
            "password=hunter2",
            "access_token=abc123",
            "refresh-token: abc123",
        ):
            out = redact_sensitive_text(text)
            assert "sekret123" not in out and "hunter2" not in out, text
            assert "abc123" not in out, text
            assert "[redacted]" in out, text

    def test_ordinary_text_is_untouched(self) -> None:
        text = "The deploy finished; tokens of appreciation to the team."
        assert redact_sensitive_text(text) == text

    def test_deterministic(self) -> None:
        text = "pmb_secret and password=x"
        assert redact_sensitive_text(text) == redact_sensitive_text(text)


class TestRedactDebugValue:
    def test_secret_named_keys_redacted_whole(self) -> None:
        for key in ("apiKey", "api_key", "authorization", "x-signature", "cookie"):
            assert redact_debug_value("value", key) == REDACTED

    def test_body_text_keys_redacted_whole(self) -> None:
        for key in ("text", "tx", "message", "description"):
            assert redact_debug_value("private message", key) == REDACTED

    def test_configured_sensitive_keys(self) -> None:
        assert (
            redact_debug_value(
                "value", "customField", sensitive_keys=frozenset({"customField"})
            )
            == REDACTED
        )

    def test_emails_and_hex_ids_scrubbed_from_strings(self) -> None:
        out = redact_debug_value(f"by real.person@example.com in {CANARY_ID}")
        assert "example.com" not in out
        assert CANARY_ID not in out
        assert out == f"by {REDACTED} in {REDACTED}"

    def test_nested_structures(self) -> None:
        payload = {
            "channel": {"id": CANARY_ID, "name": "general"},
            "items": [{"token": "sekret"}, "plain"],
            "count": 3,
        }
        out = redact_debug_value(payload)
        assert out["channel"]["id"] == REDACTED
        assert out["channel"]["name"] == "general"
        assert out["items"][0]["token"] == REDACTED
        assert out["items"][1] == "plain"
        assert out["count"] == 3

    def test_non_string_scalars_pass_through(self) -> None:
        assert redact_debug_value(42, "token") == 42
        assert redact_debug_value(None, "password") is None
        assert redact_debug_value(True) is True


class TestRedactDebugHeaders:
    def test_apikey_header_redacted_and_lowercased(self) -> None:
        out = redact_debug_headers({"ApiKey": "sekret", "Accept": "application/json"})
        assert out == {"apikey": REDACTED, "accept": "application/json"}

    def test_nonsecret_header_value_still_scrubs_ids(self) -> None:
        out = redact_debug_headers({"X-Trace": CANARY_ID})
        assert out == {"x-trace": REDACTED}
