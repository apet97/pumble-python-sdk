"""Curated preview/confirmed write tools.

Exactly four default write tools: ``send_message_preview``,
``send_message_confirmed``, ``reply_to_thread_preview``,
``reply_to_thread_confirmed``. A preview resolves the target, redacts a
160-character excerpt, hashes the full text, and returns a signed,
expiring, workspace-bound plan. The confirmed tool verifies signature,
expiry, workspace, request equality, and text hash, optionally consumes
the bounded replay store, then performs ONE non-retried write through
the façade (which adds the direct-read receipt). The token authorizes
one attempt; it does not make the Pumble API idempotent.
"""

from __future__ import annotations

import time
from typing import Any, Literal

import pydantic
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.extensions.write_plan import (
    WritePreview,
    create_confirmation_token,
    create_write_preview,
    validate_confirmation,
)
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.models import CuratedFailure
from pumble_keys.mcp_server.tools.read import state_of, to_failure

PREVIEW_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)
CONFIRMED_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)


class PreviewResult(pydantic.BaseModel):
    ok: Literal[True] = True
    summary: str
    preview: WritePreview
    token: str
    next_actions: list[str]


class ConfirmedResult(pydantic.BaseModel):
    ok: Literal[True] = True
    summary: str
    ids: dict[str, Any]
    verification_state: str
    verification_detail: str | None = None


def _now_ms() -> int:
    return int(time.time() * 1000)


def _send_request(channel_id: str, text: str) -> dict[str, Any]:
    return {"action": "send_message", "channel_id": channel_id, "text": text}


def _reply_request(channel_id: str, root_message_id: str, text: str) -> dict[str, Any]:
    return {
        "action": "reply_to_thread",
        "channel_id": channel_id,
        "root_message_id": root_message_id,
        "text": text,
    }


async def _resolve_channel(state: Any, channel: str):
    found = await state.client.channels.find(channel)
    if isinstance(found, FacadeFailure):
        return to_failure(found)
    return found


def _confirm_failure(reason: str) -> CuratedFailure:
    detail = {
        "invalid_token": "The confirmation token does not match the preview.",
        "expired": "The confirmation expired; request a new preview.",
        "workspace_mismatch": (
            "The confirmation was issued for a different workspace."
        ),
        "request_mismatch": (
            "The request changed after the preview; request a new preview."
        ),
        "text_mismatch": ("The text changed after the preview; request a new preview."),
        "replayed": "This confirmation token was already used once.",
        "target_mismatch": (
            "The resolved target changed after the preview; request a new preview."
        ),
    }[reason]
    return CuratedFailure(
        reason=f"confirmation_{reason}",
        summary=f"Confirmed write rejected: {detail}",
        next_actions=["Call the preview tool again and confirm the new plan."],
    )


def _verify_and_consume(
    state: Any,
    *,
    preview: WritePreview,
    token: str,
    request: dict[str, Any],
    text: str,
) -> CuratedFailure | None:
    reason = validate_confirmation(
        preview=preview,
        token=token,
        secret=state.confirmation_signer.secret,
        now_ms=_now_ms(),
        workspace_id=state.workspace_fingerprint,
        request=request,
        text=text,
    )
    if reason is not None:
        return _confirm_failure(reason)
    guard = getattr(state, "replay_guard", None)
    if guard is not None and not guard.consume(token):
        return _confirm_failure("replayed")
    return None


def register(server: MCPServer, _config: McpConfig) -> None:
    @server.tool(
        name="send_message_preview",
        description=(
            "Preview a channel message: resolved target, redacted excerpt, "
            "text hash, risk, expiry, and a signed confirmation token. "
            "Performs no write."
        ),
        annotations=PREVIEW_ANNOTATIONS,
    )
    async def send_message_preview(
        channel: str, text: str, ctx: Context
    ) -> PreviewResult | CuratedFailure:
        state = state_of(ctx)
        found = await _resolve_channel(state, channel)
        if isinstance(found, CuratedFailure):
            return found
        channel_id = found.channel.id
        preview = create_write_preview(
            action_type="send_message",
            target_kind="channel",
            target_id=channel_id,
            target_name=found.channel.name,
            text=text,
            workspace_id=state.workspace_fingerprint,
            request=_send_request(channel_id, text),
            now_ms=_now_ms(),
        )
        token = create_confirmation_token(preview, state.confirmation_signer.secret)
        return PreviewResult(
            summary=(
                f"Ready to send to #{found.channel.name}: "
                f"“{preview.text_excerpt}” (risk "
                f"{preview.risk_level}). Nothing was sent."
            ),
            preview=preview,
            token=token,
            next_actions=[
                (
                    "Call send_message_confirmed with the unchanged channel "
                    "and text plus this preview and token before it expires."
                )
            ],
        )

    @server.tool(
        name="send_message_confirmed",
        description=(
            "Send a previously previewed channel message. One attempt, "
            "never retried; success is proven by a direct read."
        ),
        annotations=CONFIRMED_ANNOTATIONS,
    )
    async def send_message_confirmed(
        channel: str,
        text: str,
        preview: WritePreview,
        token: str,
        ctx: Context,
    ) -> ConfirmedResult | CuratedFailure:
        state = state_of(ctx)
        found = await _resolve_channel(state, channel)
        if isinstance(found, CuratedFailure):
            return found
        channel_id = found.channel.id
        if channel_id != preview.target_id:
            return _confirm_failure("target_mismatch")
        failure = _verify_and_consume(
            state,
            preview=preview,
            token=token,
            request=_send_request(channel_id, text),
            text=text,
        )
        if failure is not None:
            return failure

        receipt = await state.client.messages.send(channel_id=channel_id, text=text)
        if isinstance(receipt, FacadeFailure):
            return to_failure(receipt)
        return ConfirmedResult(
            summary=receipt.summary,
            ids=dict(receipt.ids),
            verification_state=receipt.verification.state,
            verification_detail=receipt.verification.detail,
        )

    @server.tool(
        name="reply_to_thread_preview",
        description=(
            "Preview a thread reply with the same binding contract as "
            "send_message_preview. Performs no write."
        ),
        annotations=PREVIEW_ANNOTATIONS,
    )
    async def reply_to_thread_preview(
        channel: str, message_id: str, text: str, ctx: Context
    ) -> PreviewResult | CuratedFailure:
        state = state_of(ctx)
        found = await _resolve_channel(state, channel)
        if isinstance(found, CuratedFailure):
            return found
        channel_id = found.channel.id
        if not message_id.strip():
            return CuratedFailure(
                reason="invalid_request",
                summary="reply_to_thread_preview requires message_id.",
                next_actions=["Pass the id of the thread root message."],
            )
        preview = create_write_preview(
            action_type="reply_to_thread",
            target_kind="thread",
            target_id=channel_id,
            target_name=found.channel.name,
            text=text,
            workspace_id=state.workspace_fingerprint,
            request=_reply_request(channel_id, message_id, text),
            now_ms=_now_ms(),
        )
        token = create_confirmation_token(preview, state.confirmation_signer.secret)
        return PreviewResult(
            summary=(
                f"Ready to reply in #{found.channel.name} (thread "
                f"{message_id}): “{preview.text_excerpt}” (risk "
                f"{preview.risk_level}). Nothing was sent."
            ),
            preview=preview,
            token=token,
            next_actions=[
                (
                    "Call reply_to_thread_confirmed with the unchanged "
                    "request plus this preview and token before it expires."
                )
            ],
        )

    @server.tool(
        name="reply_to_thread_confirmed",
        description=(
            "Send a previously previewed thread reply. One attempt, never "
            "retried; success is proven by a direct read."
        ),
        annotations=CONFIRMED_ANNOTATIONS,
    )
    async def reply_to_thread_confirmed(
        channel: str,
        message_id: str,
        text: str,
        preview: WritePreview,
        token: str,
        ctx: Context,
    ) -> ConfirmedResult | CuratedFailure:
        state = state_of(ctx)
        found = await _resolve_channel(state, channel)
        if isinstance(found, CuratedFailure):
            return found
        channel_id = found.channel.id
        if channel_id != preview.target_id:
            return _confirm_failure("target_mismatch")
        failure = _verify_and_consume(
            state,
            preview=preview,
            token=token,
            request=_reply_request(channel_id, message_id, text),
            text=text,
        )
        if failure is not None:
            return failure

        receipt = await state.client.threads.reply(
            channel_id=channel_id, message_id=message_id, text=text
        )
        if isinstance(receipt, FacadeFailure):
            return to_failure(receipt)
        return ConfirmedResult(
            summary=receipt.summary,
            ids=dict(receipt.ids),
            verification_state=receipt.verification.state,
            verification_detail=receipt.verification.detail,
        )
