"""ASGI adapter for the framework-neutral webhook receiver.

Ported from ``extensions/app/http-receiver.ts``. The raw body is read
once, incrementally, with the size limit enforced during the read; the
bytes reach signature verification untouched.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from pumble_keys.pumble_app.webhooks import (
    DEFAULT_MAX_BODY_BYTES,
    WebhookResult,
)

WebhookHandler = Callable[[bytes, Mapping[str, Any]], Awaitable[WebhookResult]]


async def _send_response(send: Any, result: WebhookResult) -> None:
    headers = [
        (b"content-type", b"text/plain; charset=utf-8"),
        *(
            (name.encode("latin-1"), value.encode("latin-1"))
            for name, value in result.headers.items()
        ),
    ]
    await send(
        {
            "type": "http.response.start",
            "status": result.status,
            "headers": headers,
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": result.body.encode("utf-8"),
        }
    )


def create_asgi_webhook_app(
    handler: WebhookHandler,
    *,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> Any:
    """Wrap the receiver as a minimal ASGI application (POST only)."""

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":  # pragma: no cover — lifespan etc.
            raise RuntimeError("create_asgi_webhook_app only handles http")
        if scope.get("method", "").upper() != "POST":
            await _send_response(send, WebhookResult(405, "Method not allowed"))
            return

        chunks: list[bytes] = []
        total = 0
        too_large = False
        while True:
            message = await receive()
            if message["type"] != "http.request":  # pragma: no cover
                continue
            body = message.get("body", b"")
            total += len(body)
            if total > max_body_bytes:
                too_large = True
            elif body:
                chunks.append(body)
            if not message.get("more_body", False):
                break
        if too_large:
            await _send_response(
                send, WebhookResult(413, "Pumble webhook body too large")
            )
            return

        headers = {
            name.decode("latin-1").lower(): value.decode("latin-1")
            for name, value in scope.get("headers", [])
        }
        result = await handler(b"".join(chunks), headers)
        await _send_response(send, result)

    return app


def starlette_route(
    path: str,
    handler: WebhookHandler,
) -> Any:
    """A Starlette ``Route`` (POST) over the same receiver.

    Imports Starlette lazily; it is available transitively via
    ``mcp[cli]`` but stays optional for pure-SDK users.
    """
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Route

    async def endpoint(request: Request) -> Response:
        raw_body = await request.body()
        result = await handler(raw_body, dict(request.headers))
        return Response(
            result.body,
            status_code=result.status,
            headers=result.headers,
            media_type="text/plain",
        )

    return Route(path, endpoint, methods=["POST"])
