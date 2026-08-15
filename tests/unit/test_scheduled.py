"""P16: scheduled façade — future-only timestamps, receipts, safe cancel."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from pumble_keys.extensions.client import (
    ChannelSummary,
    FindChannelSuccess,
)
from pumble_keys.extensions.results import (
    FacadeFailure,
    create_facade_failure,
)
from pumble_keys.extensions.scheduled import ScheduledFacade
from pumble_keys.models.errors import PumbleSDKError

CHANNEL_ID = "0" * 20 + "0001"
SCHEDULED_ID = "0" * 20 + "0002"
NOW_MS = 1_786_752_000_000


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


async def guard(_operation_id: str, awaitable):
    try:
        return await awaitable
    except Exception as error:  # noqa: BLE001 — test guard mirror
        from pumble_keys.extensions.operations import operation_failure

        return operation_failure("guarded", error)


def channel_summary() -> ChannelSummary:
    return ChannelSummary(id=CHANNEL_ID, name="engineering", channel_type="PUBLIC")


def make_facade(*, resolve_ok=True, **overrides):
    r = {
        "create": Recorder(SimpleNamespace(id=SCHEDULED_ID)),
        "list": Recorder(
            SimpleNamespace(result=SimpleNamespace(scheduled_messages=[]))
        ),
        "get": Recorder(SimpleNamespace(id=SCHEDULED_ID)),
        "edit": Recorder(SimpleNamespace(id=SCHEDULED_ID)),
        "delete": Recorder(None),
    }
    r.update(overrides)
    raw = SimpleNamespace(
        scheduled_messages=SimpleNamespace(
            create_scheduled_message_async=r["create"],
            fetch_scheduled_messages_async=r["list"],
            fetch_scheduled_message_async=r["get"],
            edit_scheduled_message_async=r["edit"],
            delete_scheduled_message_async=r["delete"],
        )
    )

    async def resolver(input_value: str):
        if resolve_ok:
            return FindChannelSuccess(
                summary="Found channel #engineering.",
                ids={"channel_id": CHANNEL_ID},
                channel=channel_summary(),
            )
        return create_facade_failure(
            "Channel", input_value, reason="not_found", candidates=[]
        )

    facade = ScheduledFacade(
        raw=raw,
        guard=guard,
        resolve_facade_channel=resolver,
        now_ms=lambda: NOW_MS,
    )
    return facade, r


@pytest.mark.asyncio
async def test_create_resolves_channel_verifies_and_receipts() -> None:
    facade, r = make_facade()
    receipt = await facade.create(
        channel="engineering", text="later", send_at=NOW_MS + 1
    )
    assert receipt.ok is True
    assert receipt.summary == f"Scheduled message {SCHEDULED_ID} in #engineering."
    assert receipt.ids == {
        "channel_id": CHANNEL_ID,
        "scheduled_message_id": SCHEDULED_ID,
    }
    assert receipt.channel.name == "engineering"
    assert receipt.reference.id == SCHEDULED_ID
    assert receipt.verification.state == "verified"
    assert r["create"].calls == [
        {"channel_id": CHANNEL_ID, "text": "later", "send_at": NOW_MS + 1}
    ]
    assert r["get"].calls == [{"scheduled_message_id": SCHEDULED_ID}]


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [NOW_MS, NOW_MS - 1, 1.5, "soon", None, True])
async def test_create_rejects_past_equal_or_noninteger_send_at(bad) -> None:
    facade, r = make_facade()
    failure = await facade.create(channel_id=CHANNEL_ID, text="later", send_at=bad)
    assert isinstance(failure, FacadeFailure)
    assert failure.reason == "invalid_request"
    assert r["create"].calls == []


@pytest.mark.asyncio
async def test_create_with_explicit_channel_id_skips_resolution() -> None:
    facade, _r = make_facade(resolve_ok=False)  # resolver would fail if called
    receipt = await facade.create(
        channel_id=CHANNEL_ID, text="later", send_at=NOW_MS + 1
    )
    assert receipt.ok is True
    assert receipt.summary == (
        f"Scheduled message {SCHEDULED_ID} in channel {CHANNEL_ID}."
    )
    assert receipt.channel is None


@pytest.mark.asyncio
async def test_create_unresolved_channel_fails_before_write() -> None:
    facade, r = make_facade(resolve_ok=False)
    failure = await facade.create(channel="ghost", text="later", send_at=NOW_MS + 1)
    assert isinstance(failure, FacadeFailure)
    assert failure.reason == "not_found"
    assert r["create"].calls == []


@pytest.mark.asyncio
async def test_create_api_failure_single_attempt() -> None:
    facade, r = make_facade(create=Recorder(error=sdk_error(503)))
    failure = await facade.create(
        channel_id=CHANNEL_ID, text="later", send_at=NOW_MS + 1
    )
    assert isinstance(failure, FacadeFailure)
    assert failure.summary == "Pumble API rejected scheduled.create."
    assert len(r["create"].calls) == 1


@pytest.mark.asyncio
async def test_list_without_channel_and_with_resolved_channel() -> None:
    facade, r = make_facade()
    page = await facade.list(limit=5)
    assert page.scheduled_messages == []
    assert r["list"].calls == [{"limit": 5}]

    await facade.list(channel="engineering")
    assert r["list"].calls[1] == {"channel_id": CHANNEL_ID}


@pytest.mark.asyncio
async def test_get_passthrough_and_guarded_failure() -> None:
    facade, _r = make_facade()
    result = await facade.get(scheduled_message_id=SCHEDULED_ID)
    assert result.id == SCHEDULED_ID

    facade2, _ = make_facade(get=Recorder(error=sdk_error(404)))
    failure = await facade2.get(scheduled_message_id=SCHEDULED_ID)
    assert isinstance(failure, FacadeFailure)


@pytest.mark.asyncio
async def test_edit_receipt_and_verification() -> None:
    facade, r = make_facade()
    receipt = await facade.edit(
        scheduled_message_id=SCHEDULED_ID,
        channel_id=CHANNEL_ID,
        text="new",
        send_at=NOW_MS + 60_000,
    )
    assert receipt.ok is True
    assert receipt.summary == f"Updated scheduled message {SCHEDULED_ID}."
    assert receipt.verification.state == "verified"
    assert r["edit"].calls == [
        {
            "scheduled_message_id": SCHEDULED_ID,
            "channel_id": CHANNEL_ID,
            "text": "new",
            "send_at": NOW_MS + 60_000,
        }
    ]


@pytest.mark.asyncio
async def test_edit_rejects_past_send_at_and_blank_id() -> None:
    facade, r = make_facade()
    past = await facade.edit(
        scheduled_message_id=SCHEDULED_ID,
        channel_id=CHANNEL_ID,
        text="x",
        send_at=NOW_MS,
    )
    assert isinstance(past, FacadeFailure)

    blank = await facade.edit(
        scheduled_message_id=" ",
        channel_id=CHANNEL_ID,
        text="x",
        send_at=NOW_MS + 1,
    )
    assert isinstance(blank, FacadeFailure)
    assert r["edit"].calls == []


@pytest.mark.asyncio
async def test_cancel_receipt_no_retry_no_verification_claim() -> None:
    facade, r = make_facade()
    receipt = await facade.cancel(scheduled_message_id=SCHEDULED_ID)
    assert receipt.ok is True
    assert receipt.summary == f"Canceled scheduled message {SCHEDULED_ID}."
    assert receipt.ids == {"scheduled_message_id": SCHEDULED_ID}
    assert receipt.verification.state == "not_verifiable"
    assert len(r["delete"].calls) == 1

    facade2, r2 = make_facade(delete=Recorder(error=sdk_error(503)))
    failure = await facade2.cancel(scheduled_message_id=SCHEDULED_ID)
    assert isinstance(failure, FacadeFailure)
    assert len(r2["delete"].calls) == 1  # transient error, still one attempt
