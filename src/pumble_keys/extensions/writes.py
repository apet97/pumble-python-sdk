"""Safe message/channel write façades.

Ported from ``extensions/facade-writes.ts`` with the plan-mandated
addition of direct-read verification (§10.4):

1. validate local shape;
2. resolve the human target unless an explicit ID with
   ``validate_target=False`` is supplied;
3. call the write exactly once — never through a retry helper;
4. directly fetch the returned object by ID;
5. return the write reference AND the verification outcome.

A lost write response is not retried. A successful write followed by a
failed verification returns an ``ok=True`` receipt whose verification
state is ``verification_failed`` — it does not call the write again and
does not claim a rollback. Search is never used as proof.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

import pydantic

from pumble_keys.extensions.display import display_channel, display_user
from pumble_keys.extensions.operations import (
    OPERATION_FAILURE_NEXT_ACTION,
    operation_failure_reason,
)
from pumble_keys.extensions.results import (
    FacadeFailure,
    create_facade_invalid_request,
    create_facade_operation_failure,
)


class WriteVerification(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, arbitrary_types_allowed=True)

    state: Literal["verified", "verification_failed", "not_verifiable"]
    detail: str | None = None
    # The direct-read object; excluded diagnostic payload for receipts.
    object: Any = pydantic.Field(default=None, exclude=True, repr=False)


class WriteReceipt(pydantic.BaseModel):
    """``ok=True`` write receipt: what was accepted and what a direct
    read proved. Nothing more."""

    model_config = pydantic.ConfigDict(frozen=True, arbitrary_types_allowed=True)

    ok: Literal[True] = True
    summary: str
    ids: dict[str, Any]
    channel: Any = None
    user: Any = None
    reference: Any = None
    verification: WriteVerification


async def _attempt(coro: Any, summary: str) -> Any:
    """Run one write attempt; a raised error becomes a failure value."""
    try:
        return await coro
    except asyncio.CancelledError:
        raise
    except Exception as error:  # noqa: BLE001 — categorized into a value
        return create_facade_operation_failure(
            operation_failure_reason(error),
            summary,
            OPERATION_FAILURE_NEXT_ACTION,
            error,
        )


async def _verify(coro_factory: Any, what: str) -> WriteVerification:
    """Direct read-by-ID proof. Never retries; never re-runs the write."""
    try:
        fetched = await coro_factory()
    except asyncio.CancelledError:
        raise
    except Exception as error:  # noqa: BLE001 — verification is best-effort
        return WriteVerification(
            state="verification_failed",
            detail=(
                f"The write returned success but the direct read of {what} "
                f"failed ({type(error).__name__}). The write was NOT retried "
                "and no rollback happened."
            ),
        )
    return WriteVerification(
        state="verified",
        detail=f"Direct read of {what} succeeded.",
        object=fetched,
    )


def _is_failure(value: Any) -> bool:
    return isinstance(value, FacadeFailure)


class FacadeWrites:
    """Write façades bound to a raw client and the façade resolvers."""

    def __init__(
        self,
        *,
        raw: Any,
        resolve_facade_channel: Any,
        resolve_facade_user: Any,
    ) -> None:
        self._raw = raw
        self._resolve_channel = resolve_facade_channel
        self._resolve_user = resolve_facade_user

    async def send_message(
        self,
        *,
        channel: str | None = None,
        channel_id: str | None = None,
        validate_target: bool | None = None,
        text: str,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        target = channel_id if channel_id is not None else channel
        if target is None or not target.strip():
            return create_facade_invalid_request(
                "messages.send requires channel or channel_id.",
                "Pass channel, channel_id, or preflight the target before writing.",
            )

        resolved = None
        if channel_id is None or validate_target is True:
            found = await self._resolve_channel(target)
            if not found.ok:
                return found
            resolved = found.channel
            channel_id = resolved.id

        message = await _attempt(
            self._raw.messages.send_message_async(
                request={"channel_id": channel_id, "text": text, **rest}
            ),
            "Pumble API rejected messages.send.",
        )
        if _is_failure(message):
            return message

        verification = await _verify(
            lambda: self._raw.messages.fetch_message_async(
                message_id=message.id, channel_id=message.channel_id
            ),
            f"message {message.id}",
        )
        where = display_channel(resolved) if resolved else f"channel {channel_id}"
        return WriteReceipt(
            summary=f"Sent message {message.id} to {where}.",
            ids={"channel_id": message.channel_id, "message_id": message.id},
            channel=resolved,
            reference=message,
            verification=verification,
        )

    async def dm_user(
        self,
        *,
        user: str | None = None,
        user_id: str | None = None,
        validate_target: bool | None = None,
        text: str,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        target = user_id if user_id is not None else user
        if target is None or not target.strip():
            return create_facade_invalid_request(
                "messages.dm requires user or user_id.",
                "Pass user, user_id, or preflight the target before writing.",
            )

        resolved = None
        if user_id is None or validate_target is True:
            found = await self._resolve_user(target)
            if not found.ok:
                return found
            resolved = found.user
            user_id = resolved.id

        message = await _attempt(
            self._raw.messages.dm_user_async(
                request={"user_id": user_id, "text": text, **rest}
            ),
            "Pumble API rejected messages.dm.",
        )
        if _is_failure(message):
            return message

        verification = await _verify(
            lambda: self._raw.messages.fetch_message_async(
                message_id=message.id, channel_id=message.channel_id
            ),
            f"message {message.id}",
        )
        who = display_user(resolved) if resolved else f"user {user_id}"
        return WriteReceipt(
            summary=f"Sent DM {message.id} to {who}.",
            ids={
                "user_id": user_id,
                "message_id": message.id,
                "channel_id": message.channel_id,
            },
            user=resolved,
            reference=message,
            verification=verification,
        )

    async def dm_group(
        self,
        *,
        user_ids: list[str],
        text: str,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        if not user_ids or any(not u.strip() for u in user_ids):
            return create_facade_invalid_request(
                "messages.dm_group requires a non-empty user_ids list.",
                "Pass the explicit user ids for the group conversation.",
            )

        message = await _attempt(
            self._raw.messages.dm_group_async(
                request={"user_ids": user_ids, "text": text, **rest}
            ),
            "Pumble API rejected messages.dm_group.",
        )
        if _is_failure(message):
            return message

        verification = await _verify(
            lambda: self._raw.messages.fetch_message_async(
                message_id=message.id, channel_id=message.channel_id
            ),
            f"message {message.id}",
        )
        return WriteReceipt(
            summary=(f"Sent group DM {message.id} to {len(user_ids)} users."),
            ids={
                "user_ids": list(user_ids),
                "message_id": message.id,
                "channel_id": message.channel_id,
            },
            reference=message,
            verification=verification,
        )

    async def reply_to_thread(
        self,
        *,
        channel: str | None = None,
        channel_id: str | None = None,
        message_id: str,
        validate_target: bool | None = None,
        text: str,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        target = channel_id if channel_id is not None else channel
        if target is None or not target.strip():
            return create_facade_invalid_request(
                "threads.reply requires channel or channel_id.",
                "Pass channel, channel_id, or preflight the target before writing.",
            )
        if not message_id.strip():
            return create_facade_invalid_request(
                "threads.reply requires the root message_id.",
                "Pass the id of the thread root message.",
            )

        resolved = None
        if channel_id is None or validate_target is True:
            found = await self._resolve_channel(target)
            if not found.ok:
                return found
            resolved = found.channel
            channel_id = resolved.id

        reply = await _attempt(
            self._raw.messages.send_reply_async(
                request={
                    "channel_id": channel_id,
                    "message_id": message_id,
                    "text": text,
                    **rest,
                }
            ),
            "Pumble API rejected threads.reply.",
        )
        if _is_failure(reply):
            return reply

        verification = await _verify(
            lambda: self._raw.messages.fetch_message_async(
                message_id=reply.id, channel_id=reply.channel_id
            ),
            f"reply {reply.id}",
        )
        where = display_channel(resolved) if resolved else f"channel {channel_id}"
        return WriteReceipt(
            summary=f"Replied with {reply.id} in {where}.",
            ids={
                "channel_id": reply.channel_id,
                "message_id": reply.id,
                "root_message_id": message_id,
            },
            channel=resolved,
            reference=reply,
            verification=verification,
        )

    async def create_channel(
        self,
        *,
        name: str,
        type: str,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        if not name.strip():
            return create_facade_invalid_request(
                "channels.create requires a channel name.",
                "Pass a non-blank channel name.",
            )

        ref = await _attempt(
            self._raw.channels.create_channel_async(name=name, type_=type, **rest),
            "Pumble API rejected channels.create.",
        )
        if _is_failure(ref):
            return ref

        verification = await _verify(
            lambda: self._raw.channels.get_channel_async(channel_id=ref.id),
            f"channel {ref.id}",
        )
        return WriteReceipt(
            summary=f"Created channel #{ref.name} ({ref.id}).",
            ids={"channel_id": ref.id},
            reference=ref,
            verification=verification,
        )

    async def search_recent(
        self, *, query: str, limit: int | None = None
    ) -> dict[str, Any] | FacadeFailure:
        """Bounded most-recent search (read; lives here for TS parity)."""
        effective_limit = limit if limit is not None else 10
        page = await _attempt(
            self._raw.messages.search_messages_async(
                text=query, limit=effective_limit, strategy="MOST_RECENT"
            ),
            "Pumble API rejected search.recent.",
        )
        if _is_failure(page):
            return page
        data = list(page.result.content[:effective_limit])
        plural = "" if len(data) == 1 else "s"
        channel_ids: list[str] = []
        for hit in data:
            if hit.channel_id not in channel_ids:
                channel_ids.append(hit.channel_id)
        return {
            "ok": True,
            "summary": (f'Found {len(data)} recent message{plural} for "{query}".'),
            "ids": {
                "message_ids": [hit.id for hit in data],
                "channel_ids": channel_ids,
            },
            "data": data,
        }
