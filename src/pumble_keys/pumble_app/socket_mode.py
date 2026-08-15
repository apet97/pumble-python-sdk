"""Experimental — Pumble Socket Mode without a bundled WebSocket transport.

Ported from ``extensions/app/socket-mode.ts``. Callers inject
``create_socket`` and own reconnect/heartbeat policy; this package does
not choose one for you. See ``docs/EXPERIMENTAL.md`` before using. A
concrete ``websockets`` adapter example lives there behind the
``[socket]`` optional dependency.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pumble_keys.pumble_app.events import (
    KNOWN_EVENT_TYPES,
    PumbleWebhookEvent,
    normalize_webhook_event,
)
from pumble_keys.pumble_app.router import PumbleEventRouter

PUMBLE_SOCKET_MODE_PROTOCOL_EVIDENCE = {
    "source": (
        "https://github.com/CAKE-com/pumble-node-sdk/blob/master/pumble-sdk/"
        "src/core/adapters/socket/AddonWebsocketListener.ts"
    ),
    "verified_on": "2026-05-22",
    "verified_behavior": (
        "Official source fetches a websocket URL, opens a WebSocket, sends "
        "ping, ignores pong, receives JSON frames shaped "
        "{ payload, correlation_id }, and dispatches PUMBLE_EVENT/APP_EVENT "
        "payloads by parsing payload.body."
    ),
}

DEFAULT_PING_INTERVAL_S = 25.0


class PumbleSocketModeUnsupportedError(Exception):
    """Unsupported transport, message type, or event type."""


@dataclass(frozen=True)
class PumbleSocketModeFrame:
    payload: dict[str, Any]
    correlation_id: str | None = None


@dataclass(frozen=True)
class PumbleSocketModeDispatchResult:
    kind: str  # "event" | "pong"
    handled: int
    correlation_id: str | None = None


def _raw_message_text(raw_message: Any) -> str:
    if isinstance(raw_message, str):
        return raw_message
    if isinstance(raw_message, (bytes, bytearray, memoryview)):
        return bytes(raw_message).decode("utf-8")
    return str(raw_message)


def parse_frame(text: str) -> PumbleSocketModeFrame:
    try:
        parsed = json.loads(text)
    except ValueError as cause:
        raise ValueError("Malformed Pumble Socket Mode frame JSON") from cause
    if not isinstance(parsed, dict) or not isinstance(parsed.get("payload"), dict):
        # ValueError, not TypeError: a wire-format defect, not a Python typing bug.
        raise ValueError(  # noqa: TRY004
            "Malformed Pumble Socket Mode frame: missing payload"
        )
    correlation_id = parsed.get("correlation_id")
    return PumbleSocketModeFrame(
        payload=parsed["payload"],
        correlation_id=(correlation_id if isinstance(correlation_id, str) else None),
    )


def event_from_payload(payload: dict[str, Any]) -> PumbleWebhookEvent:
    message_type = payload.get("messageType")
    if message_type not in ("PUMBLE_EVENT", "APP_EVENT"):
        raise PumbleSocketModeUnsupportedError(
            f"Unsupported Pumble Socket Mode messageType: {message_type}"
        )

    event_type = payload.get("eventType")
    if not isinstance(event_type, str) or event_type not in KNOWN_EVENT_TYPES:
        raise PumbleSocketModeUnsupportedError(
            "Unsupported Pumble Socket Mode event payload: unknown eventType"
        )

    # The payload matches the P19 envelope form; one shared event model.
    event = normalize_webhook_event(payload)
    if event is None:
        raise ValueError(
            "Malformed Pumble Socket Mode event payload: body must be an object"
        )
    return event


class PumbleSocketModeReceiver:
    """Injected-transport Socket Mode receiver.

    ``create_socket(url)`` must return an object with ``on(event,
    listener)``, ``send(data)``, ``close()``, and optionally
    ``remove_all_listeners()``. No reconnect policy is applied here.
    """

    def __init__(
        self,
        *,
        get_websocket_url: Callable[[], str | Awaitable[str]],
        router: PumbleEventRouter,
        context: Any = None,
        create_socket: Callable[[str], Any] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
        ping_interval_s: float = DEFAULT_PING_INTERVAL_S,
        set_interval: Callable[[Callable[[], None], float], Any] | None = None,
    ) -> None:
        self._get_websocket_url = get_websocket_url
        self._router = router
        self._context = context
        self._create_socket = create_socket
        self._on_error = on_error
        self._ping_interval_s = ping_interval_s
        self._set_interval = set_interval or self._default_set_interval
        self._socket: Any = None
        self._ping_handle: Any = None

    @staticmethod
    def _default_set_interval(callback: Callable[[], None], interval_s: float) -> Any:
        async def loop() -> None:
            while True:
                await asyncio.sleep(interval_s)
                callback()

        return asyncio.ensure_future(loop())

    async def connect(self) -> None:
        if self._socket is not None:
            return
        if self._create_socket is None:
            raise PumbleSocketModeUnsupportedError(
                "Pumble Socket Mode WebSocket transport is not bundled; "
                "inject create_socket after choosing a verified WebSocket "
                "implementation."
            )

        url = self._get_websocket_url()
        if isinstance(url, Awaitable):
            url = await url
        socket = self._create_socket(url)
        self._socket = socket

        def on_open(_data: Any = None) -> None:
            if self._ping_interval_s <= 0:
                return
            self._clear_ping()
            self._ping_handle = self._set_interval(
                lambda: socket.send("ping"), self._ping_interval_s
            )

        async def on_message(data: Any = None) -> None:
            try:
                await self.dispatch(data)
            except asyncio.CancelledError:
                raise
            except BaseException as error:
                if self._on_error is not None:
                    self._on_error(error)
                    return
                raise

        def on_close(_data: Any = None) -> None:
            self._cleanup(socket)

        def on_error(error: Any = None) -> None:
            self._cleanup(socket)
            if self._on_error is not None and isinstance(error, BaseException):
                self._on_error(error)

        socket.on("open", on_open)
        socket.on("message", on_message)
        socket.on("close", on_close)
        socket.on("error", on_error)

    async def disconnect(self) -> None:
        socket = self._socket
        if socket is None:
            return
        self._cleanup(socket)
        socket.close()

    async def dispatch(self, raw_message: Any) -> PumbleSocketModeDispatchResult:
        text = _raw_message_text(raw_message)
        if text == "pong":
            return PumbleSocketModeDispatchResult(kind="pong", handled=0)

        frame = parse_frame(text)
        event = event_from_payload(frame.payload)
        context = self._context
        if callable(context):
            context = context(event, frame)
            if isinstance(context, Awaitable):
                context = await context
        active_context = context if isinstance(context, dict) else {}
        result = await self._router.dispatch(event, active_context)
        return PumbleSocketModeDispatchResult(
            kind="event",
            handled=result.handled,
            correlation_id=frame.correlation_id,
        )

    def _clear_ping(self) -> None:
        if self._ping_handle is not None:
            cancel = getattr(self._ping_handle, "cancel", None)
            if cancel is not None:
                cancel()
            self._ping_handle = None

    def _cleanup(self, socket: Any) -> None:
        if self._socket is not socket:
            return
        self._clear_ping()
        self._socket = None
        remove = getattr(socket, "remove_all_listeners", None)
        if remove is not None:
            remove()
