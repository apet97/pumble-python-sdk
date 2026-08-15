"""P21: PumbleApp — verification wired to routing, decorator, error callback."""

from __future__ import annotations

import json

import httpx
import pytest

from pumble_keys.pumble_app.app import PumbleApp
from pumble_keys.pumble_app.router import PumbleEventHandlerError
from pumble_keys.pumble_app.webhooks import (
    PUMBLE_REQUEST_SIGNATURE_HEADER,
    PUMBLE_REQUEST_TIMESTAMP_HEADER,
    sign_pumble_request,
)

SECRET = "test-signing-secret-not-real"
NOW_MS = 1_786_752_000_000.0

BODY = json.dumps({"ty": "NEW_MESSAGE", "mId": "0" * 20 + "0001"}).encode()


def signed_headers(body: bytes) -> dict[str, str]:
    ts = str(int(NOW_MS))
    return {
        PUMBLE_REQUEST_TIMESTAMP_HEADER: ts,
        PUMBLE_REQUEST_SIGNATURE_HEADER: sign_pumble_request(
            signing_secret=SECRET, timestamp=ts, raw_body=body
        ),
    }


def make_app(**kwargs) -> PumbleApp:
    return PumbleApp(signing_secret=SECRET, now_ms=lambda: NOW_MS, **kwargs)


@pytest.mark.asyncio
async def test_decorator_registration_and_dispatch() -> None:
    app = make_app()
    seen = []

    @app.event("NEW_MESSAGE")
    async def on_message(event, context):
        seen.append(event.body.m_id)

    result = await app.handle_webhook(BODY, signed_headers(BODY))
    assert result.status == 204
    assert seen == ["0" * 20 + "0001"]


@pytest.mark.asyncio
async def test_direct_registration_chains() -> None:
    app = make_app()
    seen = []
    app.event("NEW_MESSAGE", lambda event, context: seen.append(1)).event(
        "NEW_MESSAGE", lambda event, context: seen.append(2)
    )
    result = await app.handle_webhook(BODY, signed_headers(BODY))
    assert result.status == 204
    assert seen == [1, 2]


@pytest.mark.asyncio
async def test_invalid_signature_never_reaches_router() -> None:
    app = make_app()
    seen = []
    app.event("NEW_MESSAGE", lambda event, context: seen.append(1))
    result = await app.handle_webhook(BODY, {})
    assert result.status == 401
    assert seen == []


@pytest.mark.asyncio
async def test_handler_failure_maps_to_500_and_on_error() -> None:
    errors = []
    app = make_app(on_error=errors.append)

    @app.event("NEW_MESSAGE")
    async def failing(event, context):
        raise RuntimeError("boom")

    result = await app.handle_webhook(BODY, signed_headers(BODY))
    assert result.status == 500
    assert isinstance(errors[0], PumbleEventHandlerError)


@pytest.mark.asyncio
async def test_asgi_adapter_end_to_end() -> None:
    app = make_app()
    seen = []
    app.event("NEW_MESSAGE", lambda event, context: seen.append(1))
    transport = httpx.ASGITransport(app=app.asgi_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://app.example.invalid"
    ) as client:
        response = await client.post("/", content=BODY, headers=signed_headers(BODY))
    assert response.status_code == 204
    assert seen == [1]
