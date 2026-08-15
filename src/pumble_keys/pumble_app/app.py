"""``PumbleApp`` — convenience wiring of webhook verification + routing.

Ported from ``extensions/app/pumble-app.ts``. This is the Pumble
*integration* helper (webhooks in, typed events out), not the
interactive Pumble Workspace MCP App.

Usage:

    app = PumbleApp(signing_secret="...")

    @app.event("NEW_MESSAGE")
    async def on_message(event, context):
        ...

    # framework-neutral:
    result = await app.handle_webhook(raw_body, headers)
    # or mount the ASGI adapters:
    asgi_app = app.asgi_app()
    route = app.starlette_route("/webhooks/pumble")
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pumble_keys.pumble_app.asgi import create_asgi_webhook_app, starlette_route
from pumble_keys.pumble_app.events import PumbleWebhookEvent
from pumble_keys.pumble_app.router import EventHandler, PumbleEventRouter
from pumble_keys.pumble_app.webhooks import (
    WebhookResult,
    create_webhook_handler,
)


class PumbleApp:
    def __init__(
        self,
        *,
        signing_secret: str,
        on_error: Callable[[BaseException], None] | None = None,
        timestamp_tolerance_seconds: float = 300,
        max_body_bytes: int = 1024 * 1024,
        now_ms: Callable[[], float] | None = None,
    ) -> None:
        self.router = PumbleEventRouter()

        async def route_event(event: PumbleWebhookEvent) -> None:
            await self.router.dispatch(event, {})

        self._max_body_bytes = max_body_bytes
        self._webhook_handler = create_webhook_handler(
            signing_secret=signing_secret,
            on_event=route_event,
            on_error=on_error,
            timestamp_tolerance_seconds=timestamp_tolerance_seconds,
            max_body_bytes=max_body_bytes,
            now_ms=now_ms,
        )

    def event(self, event_type: str, handler: EventHandler | None = None) -> Any:
        """Register a handler; usable directly or as a decorator."""
        if handler is not None:
            self.router.on(event_type, handler)
            return self

        def register(decorated: EventHandler) -> EventHandler:
            self.router.on(event_type, decorated)
            return decorated

        return register

    async def handle_webhook(
        self, raw_body: bytes, headers: Mapping[str, Any]
    ) -> WebhookResult:
        """Framework-neutral entry point."""
        return await self._webhook_handler(raw_body, headers)

    def asgi_app(self) -> Any:
        return create_asgi_webhook_app(
            self._webhook_handler, max_body_bytes=self._max_body_bytes
        )

    def starlette_route(self, path: str) -> Any:
        return starlette_route(path, self._webhook_handler)
