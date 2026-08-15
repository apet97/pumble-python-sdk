"""Scheduled-message façade: create, list, get, edit, cancel.

Ported from ``extensions/scheduled.ts`` with the §10.4 direct-read
verification added to create/edit (``fetchScheduledMessage`` exists, so
success is proven by ID). ``send_at`` must be an integer epoch
millisecond strictly greater than the injected clock. Cancel is never
retried and claims nothing beyond the successful API response.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pumble_keys.extensions.display import display_channel
from pumble_keys.extensions.results import (
    FacadeFailure,
    create_facade_invalid_request,
)
from pumble_keys.extensions.writes import (
    WriteReceipt,
    WriteVerification,
    _attempt,
    _verify,
)


def _default_now_ms() -> int:
    return int(time.time() * 1000)


def _invalid_send_at(send_at: Any, now_ms: int, operation: str) -> FacadeFailure | None:
    if isinstance(send_at, bool) or not isinstance(send_at, int):
        return create_facade_invalid_request(
            f"{operation} requires send_at as an epoch-millisecond integer.",
            "Pass a future epoch-millisecond timestamp.",
        )
    if send_at <= now_ms:
        return create_facade_invalid_request(
            f"{operation} requires send_at to be in the future.",
            "Pass a send_at value greater than the current epoch milliseconds.",
        )
    return None


class ScheduledFacade:
    """``client.scheduled`` — safe scheduled workflows."""

    def __init__(
        self,
        *,
        raw: Any,
        guard: Any,
        resolve_facade_channel: Any,
        now_ms: Callable[[], int] = _default_now_ms,
    ) -> None:
        self._raw = raw
        self._guard = guard
        self._resolve_channel = resolve_facade_channel
        self._now_ms = now_ms

    async def _channel_target(
        self,
        operation: str,
        channel: str | None,
        channel_id: str | None,
        validate_target: bool | None,
    ) -> tuple[str, Any] | FacadeFailure:
        target = channel_id if channel_id is not None else channel
        if target is None or not target.strip():
            return create_facade_invalid_request(
                f"{operation} requires channel or channel_id.",
                "Pass channel, channel_id, or preflight the target before writing.",
            )
        if channel_id is not None and validate_target is not True:
            return (channel_id, None)
        resolved = await self._resolve_channel(target)
        if not resolved.ok:
            return resolved
        return (resolved.channel.id, resolved.channel)

    async def create(
        self,
        *,
        channel: str | None = None,
        channel_id: str | None = None,
        validate_target: bool | None = None,
        text: str,
        send_at: int,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        failure = _invalid_send_at(send_at, self._now_ms(), "scheduled.create")
        if failure is not None:
            return failure
        target = await self._channel_target(
            "scheduled.create", channel, channel_id, validate_target
        )
        if isinstance(target, FacadeFailure):
            return target
        resolved_id, resolved_channel = target

        scheduled = await _attempt(
            self._raw.scheduled_messages.create_scheduled_message_async(
                channel_id=resolved_id, text=text, send_at=send_at, **rest
            ),
            "Pumble API rejected scheduled.create.",
        )
        if isinstance(scheduled, FacadeFailure):
            return scheduled

        verification = await _verify(
            lambda: self._raw.scheduled_messages.fetch_scheduled_message_async(
                scheduled_message_id=scheduled.id
            ),
            f"scheduled message {scheduled.id}",
        )
        where = (
            display_channel(resolved_channel)
            if resolved_channel
            else f"channel {resolved_id}"
        )
        return WriteReceipt(
            summary=f"Scheduled message {scheduled.id} in {where}.",
            ids={
                "channel_id": resolved_id,
                "scheduled_message_id": scheduled.id,
            },
            channel=resolved_channel,
            reference=scheduled,
            verification=verification,
        )

    async def list(
        self,
        *,
        channel: str | None = None,
        channel_id: str | None = None,
        validate_target: bool | None = None,
        **rest: Any,
    ) -> Any:
        """One page of scheduled messages, normalized to the result body."""
        if channel is None and channel_id is None:
            response = await self._guard(
                "fetchScheduledMessages",
                self._raw.scheduled_messages.fetch_scheduled_messages_async(**rest),
            )
            return getattr(response, "result", response)
        target = await self._channel_target(
            "scheduled.list", channel, channel_id, validate_target
        )
        if isinstance(target, FacadeFailure):
            return target
        resolved_id, _resolved_channel = target
        response = await self._guard(
            "fetchScheduledMessages",
            self._raw.scheduled_messages.fetch_scheduled_messages_async(
                channel_id=resolved_id, **rest
            ),
        )
        return getattr(response, "result", response)

    async def get(self, **options: Any) -> Any:
        return await self._guard(
            "fetchScheduledMessage",
            self._raw.scheduled_messages.fetch_scheduled_message_async(**options),
        )

    async def edit(
        self,
        *,
        scheduled_message_id: str,
        channel: str | None = None,
        channel_id: str | None = None,
        validate_target: bool | None = None,
        text: str,
        send_at: int,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        failure = _invalid_send_at(send_at, self._now_ms(), "scheduled.edit")
        if failure is not None:
            return failure
        if not scheduled_message_id.strip():
            return create_facade_invalid_request(
                "scheduled.edit requires scheduled_message_id.",
                "Pass the id of the scheduled message to edit.",
            )
        target = await self._channel_target(
            "scheduled.edit", channel, channel_id, validate_target
        )
        if isinstance(target, FacadeFailure):
            return target
        resolved_id, resolved_channel = target

        scheduled = await _attempt(
            self._raw.scheduled_messages.edit_scheduled_message_async(
                scheduled_message_id=scheduled_message_id,
                channel_id=resolved_id,
                text=text,
                send_at=send_at,
                **rest,
            ),
            "Pumble API rejected scheduled.edit.",
        )
        if isinstance(scheduled, FacadeFailure):
            return scheduled

        verification = await _verify(
            lambda: self._raw.scheduled_messages.fetch_scheduled_message_async(
                scheduled_message_id=scheduled.id
            ),
            f"scheduled message {scheduled.id}",
        )
        return WriteReceipt(
            summary=f"Updated scheduled message {scheduled.id}.",
            ids={
                "channel_id": resolved_id,
                "scheduled_message_id": scheduled.id,
            },
            channel=resolved_channel,
            reference=scheduled,
            verification=verification,
        )

    async def cancel(
        self, *, scheduled_message_id: str, **rest: Any
    ) -> WriteReceipt | FacadeFailure:
        """One delete attempt; no retry, no content-verification claim."""
        if not scheduled_message_id.strip():
            return create_facade_invalid_request(
                "scheduled.cancel requires scheduled_message_id.",
                "Pass the id of the scheduled message to cancel.",
            )
        result = await _attempt(
            self._raw.scheduled_messages.delete_scheduled_message_async(
                scheduled_message_id=scheduled_message_id, **rest
            ),
            "Pumble API rejected scheduled.cancel.",
        )
        if isinstance(result, FacadeFailure):
            return result
        return WriteReceipt(
            summary=f"Canceled scheduled message {scheduled_message_id}.",
            ids={"scheduled_message_id": scheduled_message_id},
            verification=WriteVerification(
                state="not_verifiable",
                detail=(
                    "The API accepted the cancel. No content verification "
                    "is claimed beyond the successful response."
                ),
            ),
        )
