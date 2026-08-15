"""P20 integration: the ASGI adapter end-to-end over httpx."""

from __future__ import annotations

import json

import httpx
import pytest

from pumble_keys.pumble_app.asgi import create_asgi_webhook_app, starlette_route
from pumble_keys.pumble_app.webhooks import (
    PUMBLE_REQUEST_SIGNATURE_HEADER,
    PUMBLE_REQUEST_TIMESTAMP_HEADER,
    create_webhook_handler,
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


def make_app(**kwargs):
    events = []

    async def on_event(event):
        events.append(event)

    handler = create_webhook_handler(
        signing_secret=SECRET,
        on_event=on_event,
        now_ms=lambda: NOW_MS,
        **kwargs,
    )
    return create_asgi_webhook_app(
        handler, max_body_bytes=kwargs.get("max_body_bytes", 1024 * 1024)
    ), events


def client_for(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://webhook.example.invalid",
    )


@pytest.mark.asyncio
async def test_valid_post_returns_204_and_dispatches() -> None:
    app, events = make_app()
    async with client_for(app) as client:
        response = await client.post(
            "/webhooks/pumble", content=BODY, headers=signed_headers(BODY)
        )
    assert response.status_code == 204
    assert len(events) == 1


@pytest.mark.asyncio
async def test_unsigned_post_is_401() -> None:
    app, events = make_app()
    async with client_for(app) as client:
        response = await client.post("/webhooks/pumble", content=BODY)
    assert response.status_code == 401
    assert events == []


@pytest.mark.asyncio
async def test_oversized_body_is_413_during_read() -> None:
    app, _events = make_app(max_body_bytes=16)
    async with client_for(app) as client:
        response = await client.post("/webhooks/pumble", content=b"x" * 64)
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_get_is_405() -> None:
    app, _events = make_app()
    async with client_for(app) as client:
        response = await client.get("/webhooks/pumble")
    assert response.status_code == 405


@pytest.mark.asyncio
async def test_starlette_route_adapter() -> None:
    pytest.importorskip("starlette")
    from starlette.applications import Starlette

    events = []

    async def on_event(event):
        events.append(event)

    handler = create_webhook_handler(
        signing_secret=SECRET, on_event=on_event, now_ms=lambda: NOW_MS
    )
    app = Starlette(routes=[starlette_route("/webhooks/pumble", handler)])
    async with client_for(app) as client:
        ok = await client.post(
            "/webhooks/pumble", content=BODY, headers=signed_headers(BODY)
        )
        bad = await client.post("/webhooks/pumble", content=BODY)
    assert ok.status_code == 204
    assert bad.status_code == 401
    assert len(events) == 1
