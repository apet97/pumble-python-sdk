"""Optional MRTR interactive send/reply tools (curated-interactive only).

The 2026 protocol carries deterministic user questions inside the tool
call. ``Resolve`` keeps the resolved channel and the server-owned
confirmation out of the model-visible schema; the framework elicits the
single deterministic question and injects the outcome. Accepted → one
non-retried façade write with a direct-read receipt; declined or
cancelled → nothing runs. Both paths share the same façade write
service as the preview/confirm tools — one safety implementation.

Older clients: the SDK negotiates the transport (standalone elicitation
requests on <= 2025-11-25); a client without the elicitation capability
gets the SDK's clear missing-capability error and no write occurs.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.elicitation import AcceptedElicitation, ElicitationResult
from mcp.server.mcpserver import Context, Elicit, Resolve
from mcp_types import ToolAnnotations

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.models import CuratedFailure
from pumble_keys.mcp_server.tools.dependencies import (
    ConfirmationAnswer,
    confirmation_question,
    resolve_channel_dependency,
)
from pumble_keys.mcp_server.tools.read import state_of, to_failure
from pumble_keys.mcp_server.tools.write import ConfirmedResult

INTERACTIVE_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)

# The `ElicitationResult[...]` consumer annotation opts into the full
# accept/decline/cancel union so declines stay structured values. The
# resolver injects None instead when channel resolution failed; the tool
# returns the resolution failure before reading `outcome`.
ConfirmationOutcome = ElicitationResult[ConfirmationAnswer]


async def _confirm_send(
    text: str,
    resolved: Annotated[Any, Resolve(resolve_channel_dependency)],
) -> Any:
    if not getattr(resolved, "ok", False):
        return None  # resolution failed; the tool reports the failure
    return Elicit(
        confirmation_question(
            action="Send message",
            target_label=f"#{resolved.channel.name}",
            text=text,
        ),
        ConfirmationAnswer,
    )


async def _confirm_reply(
    text: str,
    message_id: str,
    resolved: Annotated[Any, Resolve(resolve_channel_dependency)],
) -> Any:
    if not getattr(resolved, "ok", False):
        return None
    return Elicit(
        confirmation_question(
            action="Reply",
            target_label=f"#{resolved.channel.name}",
            text=text,
            extra=f"(thread root {message_id})",
        ),
        ConfirmationAnswer,
    )


def _outcome_failure(outcome: Any) -> CuratedFailure:
    kind = type(outcome).__name__.replace("Elicitation", "").lower()
    return CuratedFailure(
        reason=f"confirmation_{kind}",
        summary=f"The user {kind} the interactive confirmation; nothing was sent.",
        next_actions=["Ask again only if the user changes their mind."],
    )


def register(server: MCPServer, _config: McpConfig) -> None:
    @server.tool(
        name="send_message_interactive",
        description=(
            "Send a channel message after an in-call interactive "
            "confirmation (MRTR). Nothing is sent unless the user accepts."
        ),
        annotations=INTERACTIVE_ANNOTATIONS,
    )
    async def send_message_interactive(
        channel: str,  # pylint: disable=unused-argument
        text: str,
        ctx: Context,
        resolved: Annotated[Any, Resolve(resolve_channel_dependency)],
        outcome: Annotated[ConfirmationOutcome, Resolve(_confirm_send)],
    ) -> ConfirmedResult | CuratedFailure:
        if isinstance(resolved, CuratedFailure):
            return resolved
        if not (isinstance(outcome, AcceptedElicitation) and outcome.data.send):
            return _outcome_failure(outcome)

        state = state_of(ctx)
        receipt = await state.client.messages.send(
            channel_id=resolved.channel.id, text=text
        )
        if isinstance(receipt, FacadeFailure):
            return to_failure(receipt)
        return ConfirmedResult(
            summary=receipt.summary,
            ids=dict(receipt.ids),
            verification_state=receipt.verification.state,
            verification_detail=receipt.verification.detail,
        )

    @server.tool(
        name="reply_to_thread_interactive",
        description=(
            "Reply in a thread after an in-call interactive confirmation "
            "(MRTR). Nothing is sent unless the user accepts."
        ),
        annotations=INTERACTIVE_ANNOTATIONS,
    )
    async def reply_to_thread_interactive(
        channel: str,  # pylint: disable=unused-argument
        message_id: str,
        text: str,
        ctx: Context,
        resolved: Annotated[Any, Resolve(resolve_channel_dependency)],
        outcome: Annotated[ConfirmationOutcome, Resolve(_confirm_reply)],
    ) -> ConfirmedResult | CuratedFailure:
        if isinstance(resolved, CuratedFailure):
            return resolved
        if not (isinstance(outcome, AcceptedElicitation) and outcome.data.send):
            return _outcome_failure(outcome)

        state = state_of(ctx)
        receipt = await state.client.threads.reply(
            channel_id=resolved.channel.id, message_id=message_id, text=text
        )
        if isinstance(receipt, FacadeFailure):
            return to_failure(receipt)
        return ConfirmedResult(
            summary=receipt.summary,
            ids=dict(receipt.ids),
            verification_state=receipt.verification.state,
            verification_detail=receipt.verification.detail,
        )
