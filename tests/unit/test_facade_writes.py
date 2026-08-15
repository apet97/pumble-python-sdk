"""P15: safe write façades — one attempt, direct-read proof, honest receipts."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.models.errors import PumbleSDKError

CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0002"
MESSAGE_ID = "0" * 20 + "0003"


def sdk_error(status: int) -> PumbleSDKError:
    return PumbleSDKError(
        "API error occurred",
        httpx.Response(
            status,
            text="",
            request=httpx.Request("POST", "https://sanitized.example.invalid"),
        ),
    )


class Recorder:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.value


def message_ref():
    return SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)


def make_raw(**overrides):
    r = {
        "send_message": Recorder(message_ref()),
        "dm_user": Recorder(message_ref()),
        "dm_group": Recorder(message_ref()),
        "send_reply": Recorder(message_ref()),
        "create_channel": Recorder(
            SimpleNamespace(id=CHANNEL_ID, name="fresh-channel")
        ),
        "fetch_message": Recorder(SimpleNamespace(id=MESSAGE_ID, text="t")),
        "get_channel": Recorder(
            SimpleNamespace(channel=SimpleNamespace(id=CHANNEL_ID))
        ),
        "search_messages": Recorder(
            SimpleNamespace(
                result=SimpleNamespace(
                    content=[
                        SimpleNamespace(id="h1", channel_id=CHANNEL_ID),
                        SimpleNamespace(id="h2", channel_id=CHANNEL_ID),
                    ],
                    has_more=False,
                )
            )
        ),
        "list_channels": Recorder(
            [
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id=CHANNEL_ID, name="engineering", channel_type="PUBLIC"
                    )
                )
            ]
        ),
        "list_users": Recorder(
            [
                SimpleNamespace(
                    id=USER_ID, name="Example", email="user-1@example.invalid"
                )
            ]
        ),
    }
    r.update(overrides)
    return SimpleNamespace(
        messages=SimpleNamespace(
            send_message_async=r["send_message"],
            dm_user_async=r["dm_user"],
            dm_group_async=r["dm_group"],
            send_reply_async=r["send_reply"],
            fetch_message_async=r["fetch_message"],
            search_messages_async=r["search_messages"],
        ),
        channels=SimpleNamespace(
            create_channel_async=r["create_channel"],
            get_channel_async=r["get_channel"],
            list_channels_async=r["list_channels"],
        ),
        users=SimpleNamespace(list_users_async=r["list_users"]),
        _recorders=r,
    )


def make_client(**overrides):
    raw = make_raw(**overrides)
    return create_pumble_client(raw=raw), raw._recorders


@pytest.mark.asyncio
async def test_send_resolves_channel_and_verifies_by_direct_read() -> None:
    client, r = make_client()
    receipt = await client.messages.send(channel="engineering", text="hello")
    assert receipt.ok is True
    assert receipt.summary == f"Sent message {MESSAGE_ID} to #engineering."
    assert receipt.ids == {"channel_id": CHANNEL_ID, "message_id": MESSAGE_ID}
    assert receipt.channel.name == "engineering"
    assert receipt.verification.state == "verified"
    # Write ran exactly once with the resolved id; proof is a direct read.
    assert r["send_message"].calls == [
        {"request": {"channel_id": CHANNEL_ID, "text": "hello"}}
    ]
    assert r["fetch_message"].calls == [
        {"message_id": MESSAGE_ID, "channel_id": CHANNEL_ID}
    ]
    assert r["search_messages"].calls == []  # never search as proof


@pytest.mark.asyncio
async def test_send_with_explicit_id_skips_resolution() -> None:
    client, r = make_client()
    receipt = await client.messages.send(channel_id=CHANNEL_ID, text="hi")
    assert receipt.ok is True
    assert receipt.channel is None
    assert r["list_channels"].calls == []
    assert receipt.summary == (f"Sent message {MESSAGE_ID} to channel {CHANNEL_ID}.")


@pytest.mark.asyncio
async def test_send_with_explicit_id_and_validate_target_resolves() -> None:
    client, r = make_client()
    receipt = await client.messages.send(
        channel_id=CHANNEL_ID, validate_target=True, text="hi"
    )
    assert receipt.ok is True
    assert receipt.channel is not None
    assert len(r["list_channels"].calls) == 1


@pytest.mark.asyncio
async def test_send_blank_target_is_invalid_request() -> None:
    client, r = make_client()
    failure = await client.messages.send(channel="  ", text="hi")
    assert isinstance(failure, FacadeFailure)
    assert failure.reason == "invalid_request"
    assert r["send_message"].calls == []


@pytest.mark.asyncio
async def test_send_unresolved_channel_returns_resolver_failure() -> None:
    client, r = make_client()
    failure = await client.messages.send(channel="ghost", text="hi")
    assert isinstance(failure, FacadeFailure)
    assert failure.reason == "not_found"
    assert r["send_message"].calls == []


@pytest.mark.asyncio
async def test_api_rejection_is_failure_value_with_single_attempt() -> None:
    client, r = make_client(
        send_message=Recorder(error=sdk_error(503))  # transient!
    )
    failure = await client.messages.send(channel_id=CHANNEL_ID, text="hi")
    assert isinstance(failure, FacadeFailure)
    assert failure.reason == "api_error"
    assert failure.summary == "Pumble API rejected messages.send."
    # Even a transient 503 gets exactly one attempt — no write retries.
    assert len(r["send_message"].calls) == 1
    assert r["fetch_message"].calls == []


@pytest.mark.asyncio
async def test_write_success_with_failed_verification_is_honest() -> None:
    client, r = make_client(fetch_message=Recorder(error=sdk_error(500)))
    receipt = await client.messages.send(channel_id=CHANNEL_ID, text="hi")
    assert receipt.ok is True  # the write DID succeed
    assert receipt.verification.state == "verification_failed"
    assert "NOT retried" in receipt.verification.detail
    assert "rollback" in receipt.verification.detail
    # One write, one verification read — nothing retried.
    assert len(r["send_message"].calls) == 1
    assert len(r["fetch_message"].calls) == 1


@pytest.mark.asyncio
async def test_dm_user_resolved_and_explicit_paths() -> None:
    client, r = make_client()
    receipt = await client.messages.dm(user="user-1@example.invalid", text="yo")
    assert receipt.ok is True
    assert receipt.summary == f"Sent DM {MESSAGE_ID} to Example."
    assert receipt.ids["user_id"] == USER_ID
    assert r["dm_user"].calls == [{"request": {"user_id": USER_ID, "text": "yo"}}]

    receipt2 = await client.messages.dm(user_id=USER_ID, text="yo")
    assert receipt2.ok is True
    assert receipt2.user is None


@pytest.mark.asyncio
async def test_dm_group_requires_user_ids_and_verifies() -> None:
    client, r = make_client()
    failure = await client.messages.dm_group(user_ids=[], text="all")
    assert isinstance(failure, FacadeFailure)

    receipt = await client.messages.dm_group(user_ids=[USER_ID, CHANNEL_ID], text="all")
    assert receipt.ok is True
    assert receipt.verification.state == "verified"
    assert r["dm_group"].calls == [
        {"request": {"user_ids": [USER_ID, CHANNEL_ID], "text": "all"}}
    ]


@pytest.mark.asyncio
async def test_reply_resolves_and_records_root_id() -> None:
    client, r = make_client()
    receipt = await client.threads.reply(
        channel="engineering", message_id=MESSAGE_ID, text="re"
    )
    assert receipt.ok is True
    assert receipt.ids["root_message_id"] == MESSAGE_ID
    assert receipt.summary == f"Replied with {MESSAGE_ID} in #engineering."
    assert r["send_reply"].calls == [
        {
            "request": {
                "channel_id": CHANNEL_ID,
                "message_id": MESSAGE_ID,
                "text": "re",
            }
        }
    ]


@pytest.mark.asyncio
async def test_reply_blank_root_rejected() -> None:
    client, r = make_client()
    failure = await client.threads.reply(
        channel_id=CHANNEL_ID, message_id=" ", text="re"
    )
    assert isinstance(failure, FacadeFailure)
    assert r["send_reply"].calls == []


@pytest.mark.asyncio
async def test_create_channel_verifies_by_get_channel() -> None:
    client, r = make_client()
    receipt = await client.channels.create(name="fresh-channel", type="PUBLIC")
    assert receipt.ok is True
    assert receipt.summary == f"Created channel #fresh-channel ({CHANNEL_ID})."
    assert receipt.verification.state == "verified"
    assert r["create_channel"].calls == [{"name": "fresh-channel", "type_": "PUBLIC"}]
    assert r["get_channel"].calls == [{"channel_id": CHANNEL_ID}]

    blank = await client.channels.create(name="  ", type="PUBLIC")
    assert isinstance(blank, FacadeFailure)


@pytest.mark.asyncio
async def test_search_recent_bounded_page() -> None:
    client, r = make_client()
    result = await client.search.recent(query="alert")
    assert result["ok"] is True
    assert result["summary"] == 'Found 2 recent messages for "alert".'
    assert result["ids"]["message_ids"] == ["h1", "h2"]
    assert result["ids"]["channel_ids"] == [CHANNEL_ID]
    assert r["search_messages"].calls == [
        {"text": "alert", "limit": 10, "strategy": "MOST_RECENT"}
    ]


@pytest.mark.asyncio
async def test_receipt_serialization_has_no_raw_cause() -> None:
    client, _ = make_client(fetch_message=Recorder(error=sdk_error(500)))
    receipt = await client.messages.send(channel_id=CHANNEL_ID, text="hi")
    dumped = receipt.model_dump(mode="python")
    assert "object" not in dumped["verification"]
