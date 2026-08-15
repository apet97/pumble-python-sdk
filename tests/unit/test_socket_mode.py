"""P23: Socket Mode — frames, pong, ping lifecycle, injected transport."""

from __future__ import annotations

import asyncio
import json

import pytest

from pumble_keys.pumble_app.router import PumbleEventRouter
from pumble_keys.pumble_app.socket_mode import (
    PumbleSocketModeReceiver,
    PumbleSocketModeUnsupportedError,
    parse_frame,
)

MID = "0" * 20 + "0001"
WID = "0" * 20 + "0002"


def frame(payload: dict, correlation_id: str | None = "corr-1") -> str:
    data: dict = {"payload": payload}
    if correlation_id is not None:
        data["correlation_id"] = correlation_id
    return json.dumps(data)


def event_payload(**overrides) -> dict:
    payload = {
        "messageType": "PUMBLE_EVENT",
        "eventType": "NEW_MESSAGE",
        "workspaceId": WID,
        "body": {"ty": "NEW_MESSAGE", "mId": MID},
    }
    payload.update(overrides)
    return payload


class FakeSocket:
    def __init__(self) -> None:
        self.listeners: dict[str, list] = {}
        self.sent: list = []
        self.closed = False
        self.removed = False

    def on(self, event: str, listener) -> None:
        self.listeners.setdefault(event, []).append(listener)

    def send(self, data) -> None:
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True

    def remove_all_listeners(self) -> None:
        self.removed = True

    async def emit(self, event: str, data=None) -> None:
        for listener in self.listeners.get(event, []):
            outcome = listener(data) if data is not None else listener()
            if asyncio.iscoroutine(outcome):
                await outcome


class FakeTimers:
    def __init__(self) -> None:
        self.intervals: list = []
        self.cancelled = 0

    def set_interval(self, callback, interval_s):
        self.intervals.append((callback, interval_s))
        timers = self

        class Handle:
            def cancel(self) -> None:
                timers.cancelled += 1

        return Handle()


def make_receiver(**kwargs):
    router = PumbleEventRouter()
    seen: list = []
    router.on("NEW_MESSAGE", lambda event, context: seen.append(event))
    socket = FakeSocket()
    timers = FakeTimers()
    receiver = PumbleSocketModeReceiver(
        get_websocket_url=lambda: "wss://socket.example.invalid",
        router=router,
        create_socket=kwargs.pop("create_socket", lambda url: socket),
        set_interval=timers.set_interval,
        **kwargs,
    )
    return receiver, socket, timers, seen


@pytest.mark.asyncio
async def test_connect_without_transport_raises_dedicated_error() -> None:
    receiver = PumbleSocketModeReceiver(
        get_websocket_url=lambda: "wss://x.example.invalid",
        router=PumbleEventRouter(),
    )
    with pytest.raises(PumbleSocketModeUnsupportedError, match="not bundled"):
        await receiver.connect()


@pytest.mark.asyncio
async def test_string_and_bytes_frames_dispatch() -> None:
    receiver, _socket, _timers, seen = make_receiver()
    result = await receiver.dispatch(frame(event_payload()))
    assert result.kind == "event"
    assert result.handled == 1
    assert result.correlation_id == "corr-1"

    result2 = await receiver.dispatch(frame(event_payload()).encode("utf-8"))
    assert result2.kind == "event"
    assert len(seen) == 2
    assert seen[0].body.m_id == MID
    assert seen[0].workspace_id == WID


@pytest.mark.asyncio
async def test_pong_is_ignored() -> None:
    receiver, _socket, _timers, seen = make_receiver()
    result = await receiver.dispatch("pong")
    assert result.kind == "pong"
    assert result.handled == 0
    assert seen == []


@pytest.mark.asyncio
async def test_malformed_json_and_missing_payload() -> None:
    receiver, _socket, _timers, _seen = make_receiver()
    with pytest.raises(ValueError, match="frame JSON"):
        await receiver.dispatch("{not json")
    with pytest.raises(ValueError, match="missing payload"):
        await receiver.dispatch(json.dumps({"nope": 1}))
    with pytest.raises(ValueError, match="missing payload"):
        await receiver.dispatch(json.dumps({"payload": "not-a-dict"}))


@pytest.mark.asyncio
async def test_unsupported_message_and_event_types() -> None:
    receiver, _socket, _timers, _seen = make_receiver()
    with pytest.raises(PumbleSocketModeUnsupportedError, match="messageType"):
        await receiver.dispatch(frame(event_payload(messageType="SOMETHING_ELSE")))
    with pytest.raises(PumbleSocketModeUnsupportedError, match="unknown eventType"):
        await receiver.dispatch(frame(event_payload(eventType="MYSTERY")))


@pytest.mark.asyncio
async def test_missing_correlation_id_is_none() -> None:
    receiver, _socket, _timers, _seen = make_receiver()
    result = await receiver.dispatch(frame(event_payload(), correlation_id=None))
    assert result.correlation_id is None


@pytest.mark.asyncio
async def test_app_event_message_type_accepted() -> None:
    receiver, _socket, _timers, seen = make_receiver()
    await receiver.dispatch(frame(event_payload(messageType="APP_EVENT")))
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_ping_lifecycle_and_cleanup() -> None:
    receiver, socket, timers, seen = make_receiver()
    await receiver.connect()
    await receiver.connect()  # idempotent

    await socket.emit("open")
    assert len(timers.intervals) == 1
    callback, interval_s = timers.intervals[0]
    assert interval_s == 25.0
    callback()
    assert socket.sent == ["ping"]

    await socket.emit("message", frame(event_payload()))
    assert len(seen) == 1

    await receiver.disconnect()
    assert socket.closed is True
    assert socket.removed is True
    assert timers.cancelled == 1

    # After disconnect, connect works again with a fresh socket.
    await receiver.disconnect()  # no-op


@pytest.mark.asyncio
async def test_close_event_cleans_up_without_closing_again() -> None:
    receiver, socket, timers, _seen = make_receiver()
    await receiver.connect()
    await socket.emit("open")
    await socket.emit("close")
    assert timers.cancelled == 1
    assert socket.removed is True
    assert socket.closed is False


@pytest.mark.asyncio
async def test_message_error_routes_to_on_error() -> None:
    errors: list = []
    receiver, socket, _timers, _seen = make_receiver(on_error=errors.append)
    await receiver.connect()
    await socket.emit("message", "{broken")
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)


@pytest.mark.asyncio
async def test_context_factory_receives_event_and_frame() -> None:
    contexts: list = []

    async def factory(event, socket_frame):
        contexts.append((event.type, socket_frame.correlation_id))
        return {"from": "factory"}

    router = PumbleEventRouter()
    seen_context: list = []
    router.on("NEW_MESSAGE", lambda event, context: seen_context.append(context))
    receiver = PumbleSocketModeReceiver(
        get_websocket_url=lambda: "wss://x.example.invalid",
        router=router,
        context=factory,
    )
    await receiver.dispatch(frame(event_payload()))
    assert contexts == [("NEW_MESSAGE", "corr-1")]
    assert seen_context == [{"from": "factory"}]


def test_parse_frame_shapes() -> None:
    parsed = parse_frame(frame({"messageType": "PUMBLE_EVENT"}))
    assert parsed.correlation_id == "corr-1"
    assert parsed.payload == {"messageType": "PUMBLE_EVENT"}
