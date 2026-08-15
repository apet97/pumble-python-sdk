"""P18: testing helpers — sanitizer contract, body hash, mock transport."""

from __future__ import annotations

import httpx
import pytest

from pumble_keys import PumbleSDK
from pumble_keys.testing import (
    FakeClock,
    MockFixture,
    create_fixture_body_hash,
    create_mock_pumble_transport,
    make_channel,
    make_channel_list_entry,
    make_message,
    make_message_ref,
    make_user,
    sanitize_pumble_fixture_value,
)

LIVE_ID = "abcdefabcdefabcdefabcdef"


class TestSanitizer:
    def test_ids_become_sequential_placeholders(self) -> None:
        out = sanitize_pumble_fixture_value(
            {"a": LIVE_ID, "b": LIVE_ID, "c": "bbccddeeff00112233445566"}
        )
        assert out["a"] == "1".zfill(24)
        assert out["b"] == "1".zfill(24)  # repeated id keeps its placeholder
        assert out["c"] == "2".zfill(24)

    def test_placeholder_ids_pass_through(self) -> None:
        placeholder = "0" * 20 + "0007"
        assert sanitize_pumble_fixture_value(placeholder) == placeholder

    def test_emails_and_names(self) -> None:
        out = sanitize_pumble_fixture_value(
            {
                "email": "real.person@example.com",
                "name": "Real Person",
                "role": "MEMBER",
            }
        )
        assert out["email"] == "user-1@example.invalid"
        assert out["name"] == "User 1"

    def test_non_user_name_gets_stable_digest(self) -> None:
        out = sanitize_pumble_fixture_value({"name": "My Secret Channel"})
        again = sanitize_pumble_fixture_value({"name": "My Secret Channel"})
        assert out["name"].startswith("example-name-")
        assert out == again  # deterministic

    def test_text_fields_redacted_and_avatar_paths_fixed(self) -> None:
        out = sanitize_pumble_fixture_value(
            {
                "text": "private content",
                "description": "notes",
                "fullPath": "https://cdn.example.com/avatar.png",
                "harmless": "keep me",
            }
        )
        assert out["text"] == "[redacted]"
        assert out["description"] == "[redacted]"
        assert out["fullPath"] == "https://example.invalid/redacted-avatar.png"
        assert out["harmless"] == "keep me"

    def test_embedded_ids_and_emails_in_free_strings(self) -> None:
        out = sanitize_pumble_fixture_value(
            {"note": f"by real.person@example.com in {LIVE_ID}"}
        )
        assert "example.com" not in out["note"]
        assert LIVE_ID not in out["note"]


class TestBodyHash:
    def test_key_order_does_not_change_hash(self) -> None:
        a = create_fixture_body_hash({"b": 2, "a": [{"y": 1, "x": 2}]})
        b = create_fixture_body_hash({"a": [{"x": 2, "y": 1}], "b": 2})
        assert a == b

    def test_different_bodies_differ(self) -> None:
        assert create_fixture_body_hash({"a": 1}) != create_fixture_body_hash({"a": 2})

    def test_empty_body(self) -> None:
        assert create_fixture_body_hash(None) == create_fixture_body_hash(None)


class TestFactories:
    def test_factories_build_valid_generated_models(self) -> None:
        assert make_user().email.endswith("@example.invalid")
        assert make_channel(name="other").name == "other"
        assert make_channel_list_entry().channel.id == make_channel().id
        assert make_message().text == "[redacted]"
        assert make_message_ref().channel_id == make_channel().id


class TestFakeClock:
    def test_advance_and_read(self) -> None:
        clock = FakeClock()
        assert clock() == 0.0
        clock.advance(1.5)
        assert clock() == 1.5
        assert clock.now_ms() == 1500
        with pytest.raises(ValueError):
            clock.advance(-1)


class TestMockTransport:
    def make_sdk(self, fixtures):
        transport = create_mock_pumble_transport(fixtures)
        return PumbleSDK(
            api_key_auth="test-key-not-real",
            client=httpx.Client(transport=transport),
            async_client=httpx.AsyncClient(transport=transport),
        )

    def test_generated_sdk_call_hits_fixture(self) -> None:
        fixtures = [
            MockFixture(
                path="/listChannels",
                response=[
                    make_channel_list_entry().model_dump(
                        by_alias=True, exclude_none=True, mode="json"
                    )
                ],
            )
        ]
        sdk = self.make_sdk(fixtures)
        entries = sdk.channels.list_channels()
        assert entries[0].channel.name == "example-channel"

    def test_post_body_matching_and_fifo(self) -> None:
        ref = make_message_ref().model_dump(by_alias=True, mode="json")
        body = {"channelId": make_channel().id, "text": "[redacted]"}
        fixtures = [
            MockFixture(path="/sendMessage", method="POST", body=body, response=ref)
        ]
        sdk = self.make_sdk(fixtures)
        result = sdk.messages.send_message(request=body)
        assert result.id == make_message_ref().id

    def test_miss_raises_instead_of_network(self) -> None:
        sdk = self.make_sdk([])
        with pytest.raises(Exception) as excinfo:
            sdk.channels.list_channels()
        assert "Mock Pumble fetch miss" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_client_shares_fixtures(self) -> None:
        fixtures = [
            MockFixture(
                path="/myInfo",
                response=make_user().model_dump(
                    by_alias=True, exclude_none=True, mode="json"
                ),
            )
        ]
        sdk = self.make_sdk(fixtures)
        user = await sdk.users.my_info_async()
        assert user.email == "user-1@example.invalid"
