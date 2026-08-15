"""Typed event router with deterministic registration-order dispatch.

Ported from ``extensions/app/event-router.ts``. Handlers registered for
an event type run in registration order; the first failing handler
stops the dispatch and raises ``PumbleEventHandlerError`` carrying the
cause (the TypeScript behavior — no continue-on-error).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pumble_keys.pumble_app.events import PumbleWebhookEvent

EventContext = dict[str, Any]
EventHandler = Callable[[PumbleWebhookEvent, EventContext], Awaitable[None] | None]


@dataclass(frozen=True)
class DispatchResult:
    handled: int


class PumbleEventHandlerError(Exception):
    """One registered handler failed; dispatch stopped there."""

    def __init__(self, event_type: str, cause: BaseException) -> None:
        suffix = f": {cause}" if str(cause) else ""
        super().__init__(f"Pumble event handler failed for {event_type}{suffix}")
        self.event_type = event_type
        self.__cause__ = cause


class PumbleEventRouter:
    """Register with ``on(type, handler)``; dispatch in order."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event_type: str, handler: EventHandler) -> PumbleEventRouter:
        self._handlers.setdefault(event_type, []).append(handler)
        return self

    def handler_count(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, []))

    async def dispatch(
        self,
        event: PumbleWebhookEvent,
        context: EventContext | None = None,
    ) -> DispatchResult:
        registered = list(self._handlers.get(event.type, []))
        active_context: EventContext = context if context is not None else {}
        handled = 0
        for handler in registered:
            try:
                outcome = handler(event, active_context)
                if outcome is not None and isinstance(outcome, Awaitable):
                    await outcome
            except asyncio.CancelledError:
                raise
            except BaseException as cause:
                raise PumbleEventHandlerError(event.type, cause) from cause
            handled += 1
        return DispatchResult(handled=handled)
