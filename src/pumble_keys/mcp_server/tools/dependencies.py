"""Resolver dependencies for the MRTR interactive tools.

``Resolve`` hides two things from the model-visible schema: the
server-resolved channel and the user's confirmation outcome. The
elicitation question is deterministic — built only from the resolved
target and the text (label, redacted excerpt, hash prefix, risk); no
random IDs, no timestamps — so retry rounds render identically and the
framework asks each question exactly once.
"""

from __future__ import annotations

from typing import Any

import pydantic
from mcp.server.mcpserver import Context

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.extensions.write_plan import (
    excerpt_text,
    hash_text,
    infer_risk_level,
)
from pumble_keys.mcp_server.tools.read import state_of, to_failure


class ConfirmationAnswer(pydantic.BaseModel):
    """The single deterministic question: send it or not."""

    send: bool = pydantic.Field(
        description="true sends the message exactly once; false aborts."
    )


async def resolve_channel_dependency(channel: str, ctx: Context) -> Any:
    """Server-owned channel resolution; failures stay values."""
    state = state_of(ctx)
    found = await state.client.channels.find(channel)
    if isinstance(found, FacadeFailure):
        return to_failure(found)
    return found


def confirmation_question(
    *,
    action: str,
    target_label: str,
    text: str,
    extra: str = "",
) -> str:
    """Deterministic MRTR question text (no IDs, no clocks)."""
    excerpt = excerpt_text(text)
    digest = hash_text(text)[:12]
    risk = infer_risk_level(action)
    detail = f" {extra}" if extra else ""
    return (
        f"{action} to {target_label}?{detail} "
        f'Text ({len(text)} characters, sha256 {digest}): "{excerpt}". '
        f"Risk: {risk}. Reply send=true to send exactly once; decline or "
        "cancel sends nothing."
    )
