"""P21: event router — deterministic order, error propagation, counts."""

from __future__ import annotations

import pytest

from pumble_keys.pumble_app.events import normalize_webhook_event
from pumble_keys.pumble_app.router import (
    PumbleEventHandlerError,
    PumbleEventRouter,
)

EVENTS = {
    event_type: normalize_webhook_event({"ty": event_type})
    for event_type in (
        "NEW_MESSAGE",
        "UPDATED_MESSAGE",
        "REACTION_ADDED",
        "CHANNEL_CREATED",
        "APP_UNINSTALLED",
        "APP_UNAUTHORIZED",
        "WORKSPACE_USER_JOINED",
    )
}


@pytest.mark.asyncio
async def test_zero_handlers_dispatches_zero() -> None:
    router = PumbleEventRouter()
    result = await router.dispatch(EVENTS["NEW_MESSAGE"], {})
    assert result.handled == 0


@pytest.mark.asyncio
async def test_single_sync_handler() -> None:
    router = PumbleEventRouter()
    seen = []
    router.on("NEW_MESSAGE", lambda event, context: seen.append(event.type))
    result = await router.dispatch(EVENTS["NEW_MESSAGE"], {})
    assert result.handled == 1
    assert seen == ["NEW_MESSAGE"]


@pytest.mark.asyncio
async def test_multiple_handlers_run_in_registration_order() -> None:
    router = PumbleEventRouter()
    order = []

    async def first(event, context):
        order.append("first")

    async def second(event, context):
        order.append("second")

    router.on("NEW_MESSAGE", first).on("NEW_MESSAGE", second)
    result = await router.dispatch(EVENTS["NEW_MESSAGE"], {})
    assert result.handled == 2
    assert order == ["first", "second"]


@pytest.mark.asyncio
async def test_failing_handler_stops_dispatch_and_wraps_cause() -> None:
    router = PumbleEventRouter()
    order = []

    async def first(event, context):
        order.append("first")
        raise ValueError("handler boom")

    async def second(event, context):
        order.append("second")

    router.on("NEW_MESSAGE", first).on("NEW_MESSAGE", second)
    with pytest.raises(
        PumbleEventHandlerError,
        match="Pumble event handler failed for NEW_MESSAGE: handler boom",
    ) as excinfo:
        await router.dispatch(EVENTS["NEW_MESSAGE"], {})
    assert isinstance(excinfo.value.__cause__, ValueError)
    assert order == ["first"]  # second never ran (TS behavior)


@pytest.mark.asyncio
async def test_context_is_shared_between_handlers() -> None:
    router = PumbleEventRouter()

    async def writer(event, context):
        context["seen"] = event.type

    async def reader(event, context):
        context["echo"] = context["seen"]

    router.on("REACTION_ADDED", writer).on("REACTION_ADDED", reader)
    context: dict = {}
    await router.dispatch(EVENTS["REACTION_ADDED"], context)
    assert context == {"seen": "REACTION_ADDED", "echo": "REACTION_ADDED"}


@pytest.mark.asyncio
async def test_all_seven_event_types_route_independently() -> None:
    router = PumbleEventRouter()
    seen: dict[str, int] = {}
    for event_type in EVENTS:
        router.on(
            event_type,
            lambda event, context: seen.__setitem__(
                event.type, seen.get(event.type, 0) + 1
            ),
        )
    for event in EVENTS.values():
        result = await router.dispatch(event, {})
        assert result.handled == 1
    assert seen == {event_type: 1 for event_type in EVENTS}


@pytest.mark.asyncio
async def test_handlers_only_fire_for_their_type() -> None:
    router = PumbleEventRouter()
    seen = []
    router.on("NEW_MESSAGE", lambda event, context: seen.append("nm"))
    await router.dispatch(EVENTS["REACTION_ADDED"], {})
    assert seen == []
