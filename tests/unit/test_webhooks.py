"""P20: webhook ingress — signature, timestamps, body limit, dispatch codes."""

from __future__ import annotations

import asyncio
import json

import pytest

from pumble_keys.pumble_app.webhooks import (
    PUMBLE_REQUEST_SIGNATURE_HEADER,
    PUMBLE_REQUEST_TIMESTAMP_HEADER,
    create_webhook_handler,
    sign_pumble_request,
)

SECRET = "test-signing-secret-not-real"
NOW_MS = 1_786_752_000_000.0
WID = "0" * 20 + "0001"

EVENT_BODY = json.dumps(
    {"ty": "NEW_MESSAGE", "wId": WID, "mId": "0" * 20 + "0002", "tx": "[redacted]"}
).encode()


def signed_headers(
    body: bytes,
    *,
    timestamp: str | None = None,
    secret: str = SECRET,
) -> dict[str, str]:
    ts = timestamp if timestamp is not None else str(int(NOW_MS))
    return {
        PUMBLE_REQUEST_TIMESTAMP_HEADER: ts,
        PUMBLE_REQUEST_SIGNATURE_HEADER: sign_pumble_request(
            signing_secret=secret, timestamp=ts, raw_body=body
        ),
    }


def make_handler(**kwargs):
    events = []

    async def on_event(event):
        events.append(event)

    handler = create_webhook_handler(
        signing_secret=SECRET,
        on_event=on_event,
        now_ms=lambda: NOW_MS,
        **kwargs,
    )
    return handler, events


def test_blank_secret_rejected() -> None:
    with pytest.raises(ValueError, match="signing_secret"):
        create_webhook_handler(signing_secret="  ")


@pytest.mark.asyncio
async def test_valid_delivery_dispatches_and_returns_204() -> None:
    handler, events = make_handler()
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY))
    assert result.status == 204
    assert len(events) == 1
    assert events[0].type == "NEW_MESSAGE"


@pytest.mark.asyncio
async def test_timestamp_in_seconds_is_accepted() -> None:
    handler, _events = make_handler()
    seconds = str(int(NOW_MS / 1000))
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY, timestamp=seconds))
    assert result.status == 204


@pytest.mark.asyncio
async def test_stale_and_future_timestamps_rejected() -> None:
    handler, events = make_handler()
    for offset in (-301_000, 301_000):
        ts = str(int(NOW_MS + offset))
        result = await handler(EVENT_BODY, signed_headers(EVENT_BODY, timestamp=ts))
        assert result.status == 401
        assert "stale timestamp" in result.body
    assert events == []


@pytest.mark.asyncio
async def test_missing_headers_rejected() -> None:
    handler, _events = make_handler()
    result = await handler(EVENT_BODY, {})
    assert result.status == 401
    assert "missing timestamp or signature" in result.body


@pytest.mark.asyncio
async def test_bad_timestamp_rejected() -> None:
    handler, _events = make_handler()
    headers = signed_headers(EVENT_BODY, timestamp="soon")
    result = await handler(EVENT_BODY, headers)
    assert result.status == 401
    assert "bad timestamp" in result.body


@pytest.mark.asyncio
async def test_wrong_secret_rejected() -> None:
    handler, events = make_handler()
    headers = signed_headers(EVENT_BODY, secret="other-secret")
    result = await handler(EVENT_BODY, headers)
    assert result.status == 401
    assert events == []


@pytest.mark.asyncio
async def test_malformed_hex_signature_rejected() -> None:
    handler, _events = make_handler()
    headers = signed_headers(EVENT_BODY)
    headers[PUMBLE_REQUEST_SIGNATURE_HEADER] = "zzzz-not-hex"
    result = await handler(EVENT_BODY, headers)
    assert result.status == 401


@pytest.mark.asyncio
async def test_tampered_body_rejected() -> None:
    handler, _events = make_handler()
    headers = signed_headers(EVENT_BODY)
    tampered = EVENT_BODY + b" "
    result = await handler(tampered, headers)
    assert result.status == 401


@pytest.mark.asyncio
async def test_body_over_limit_is_413_before_verification() -> None:
    handler, _events = make_handler(max_body_bytes=10)
    result = await handler(b"x" * 11, {})
    assert result.status == 413


@pytest.mark.asyncio
async def test_malformed_json_is_400_after_valid_signature() -> None:
    handler, _events = make_handler()
    body = b"{not json"
    result = await handler(body, signed_headers(body))
    assert result.status == 400
    assert result.body == "Malformed JSON body"


@pytest.mark.asyncio
async def test_unsupported_payload_is_400() -> None:
    handler, _events = make_handler()
    body = json.dumps({"ty": "SOMETHING_ELSE"}).encode()
    result = await handler(body, signed_headers(body))
    assert result.status == 400
    assert result.body == "Unsupported Pumble webhook payload"


@pytest.mark.asyncio
async def test_malformed_envelope_body_is_400() -> None:
    handler, _events = make_handler()
    body = json.dumps({"eventType": "NEW_MESSAGE", "body": "{oops"}).encode()
    result = await handler(body, signed_headers(body))
    assert result.status == 400
    assert result.body == "Malformed Pumble event body"


@pytest.mark.asyncio
async def test_handler_error_is_500_with_on_error() -> None:
    errors = []

    async def failing(event):
        raise RuntimeError("handler exploded")

    handler = create_webhook_handler(
        signing_secret=SECRET,
        handlers={"NEW_MESSAGE": failing},
        on_error=errors.append,
        now_ms=lambda: NOW_MS,
    )
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY))
    assert result.status == 500
    assert isinstance(errors[0], RuntimeError)


@pytest.mark.asyncio
async def test_typed_handler_map_receives_matching_event() -> None:
    seen = []

    handler = create_webhook_handler(
        signing_secret=SECRET,
        handlers={"NEW_MESSAGE": seen.append},
        now_ms=lambda: NOW_MS,
    )
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY))
    assert result.status == 204
    assert seen[0].body.tx == "[redacted]"


@pytest.mark.asyncio
async def test_list_valued_headers_are_accepted() -> None:
    handler, events = make_handler()
    headers = {key: [value] for key, value in signed_headers(EVENT_BODY).items()}
    result = await handler(EVENT_BODY, headers)
    assert result.status == 204
    assert len(events) == 1


@pytest.mark.asyncio
async def test_empty_list_header_rejected() -> None:
    handler, _events = make_handler()
    headers: dict[str, object] = dict(signed_headers(EVENT_BODY))
    headers[PUMBLE_REQUEST_TIMESTAMP_HEADER] = []
    result = await handler(EVENT_BODY, headers)
    assert result.status == 401
    assert "missing timestamp or signature" in result.body


@pytest.mark.asyncio
async def test_non_finite_timestamps_rejected() -> None:
    handler, _events = make_handler()
    for ts in ("nan", "inf"):
        result = await handler(EVENT_BODY, signed_headers(EVENT_BODY, timestamp=ts))
        assert result.status == 401
        assert "bad timestamp" in result.body


@pytest.mark.asyncio
async def test_hex_signature_of_wrong_length_rejected() -> None:
    handler, _events = make_handler()
    headers = signed_headers(EVENT_BODY)
    truncated = headers[PUMBLE_REQUEST_SIGNATURE_HEADER][:-2]
    headers[PUMBLE_REQUEST_SIGNATURE_HEADER] = truncated
    result = await handler(EVENT_BODY, headers)
    assert result.status == 401


def test_nonpositive_body_limit_rejected() -> None:
    with pytest.raises(ValueError, match="max_body_bytes"):
        create_webhook_handler(signing_secret=SECRET, max_body_bytes=0)


@pytest.mark.asyncio
async def test_cancelled_handler_propagates() -> None:
    async def cancelling(event):
        raise asyncio.CancelledError

    handler = create_webhook_handler(
        signing_secret=SECRET,
        on_event=cancelling,
        now_ms=lambda: NOW_MS,
    )
    with pytest.raises(asyncio.CancelledError):
        await handler(EVENT_BODY, signed_headers(EVENT_BODY))


@pytest.mark.asyncio
async def test_handler_error_is_500_without_on_error() -> None:
    async def failing(event):
        raise RuntimeError("handler exploded")

    handler = create_webhook_handler(
        signing_secret=SECRET,
        on_event=failing,
        now_ms=lambda: NOW_MS,
    )
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY))
    assert result.status == 500
    assert result.body == "Webhook handler failed"


@pytest.mark.asyncio
async def test_raising_on_error_callback_still_returns_500() -> None:
    async def failing(event):
        raise RuntimeError("handler exploded")

    def bad_on_error(error: BaseException) -> None:
        raise ValueError("reporter exploded")

    handler = create_webhook_handler(
        signing_secret=SECRET,
        on_event=failing,
        on_error=bad_on_error,
        now_ms=lambda: NOW_MS,
    )
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY))
    assert result.status == 500


@pytest.mark.asyncio
async def test_plain_sync_on_event_is_awaited_free_and_returns_204() -> None:
    seen = []

    def on_event(event) -> None:
        seen.append(event)

    handler = create_webhook_handler(
        signing_secret=SECRET,
        on_event=on_event,
        now_ms=lambda: NOW_MS,
    )
    result = await handler(EVENT_BODY, signed_headers(EVENT_BODY))
    assert result.status == 204
    assert seen[0].type == "NEW_MESSAGE"
