"""Mount the Pumble webhook receiver beside ``/mcp``.

``/webhooks/pumble`` is protected by Pumble's HMAC signature (the P20
receiver: ``<timestamp>:<raw-body>``, ±300 s, 1 MiB), NOT by the MCP
bearer authorization — Pumble cannot present an OAuth token. A verified
event publishes URI-only refetch cues (see ``subscriptions``); an
unverified request publishes nothing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from pumble_keys.mcp_server.subscriptions import EventPublisher, publish_cues
from pumble_keys.pumble_app.asgi import starlette_route
from pumble_keys.pumble_app.events import PumbleWebhookEvent
from pumble_keys.pumble_app.webhooks import (
    WebhookResult,
    create_webhook_handler,
)

WEBHOOK_PATH = "/webhooks/pumble"

WebhookHandler = Callable[[bytes, Mapping[str, Any]], Awaitable[WebhookResult]]


def create_webhook_bridge(
    *,
    signing_secret: str,
    publisher: EventPublisher,
    on_error: Callable[[BaseException], None] | None = None,
    now_ms: Callable[[], float] | None = None,
) -> WebhookHandler:
    """A signature-verified receiver that publishes refetch cues."""

    async def forward(event: PumbleWebhookEvent) -> None:
        await publish_cues(publisher, event)

    return create_webhook_handler(
        signing_secret=signing_secret,
        on_event=forward,
        on_error=on_error,
        now_ms=now_ms,
    )


def mount_pumble_webhooks(
    app: Any, handler: WebhookHandler, *, path: str = WEBHOOK_PATH
) -> Any:
    """Add the webhook route to the server's Streamable HTTP app."""
    app.router.routes.append(starlette_route(path, handler))
    return app
