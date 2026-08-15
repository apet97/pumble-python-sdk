"""Structured façade results: success receipts and normal-failure values.

Ported from ``extensions/facade-failure.ts``. Normal operational
outcomes — not found, ambiguity, invalid request, API rejection,
transport failure — are returned as values, never raised. Exceptions
are opt-in through ``assert_facade_ok``.

The raw exception behind an ``api_error``/``transport_error`` failure is
kept only as excluded diagnostic state (``cause``); it never serializes
and never appears in logs by default.
"""

from __future__ import annotations

from typing import Any, Literal

import pydantic

from pumble_keys.extensions.display import (
    format_channel_candidate_label,
    format_user_candidate_label,
)

FacadeFailureReason = Literal[
    "not_found",
    "ambiguous",
    "invalid_request",
    "api_error",
    "transport_error",
]

_REASONS: frozenset[str] = frozenset(
    ("not_found", "ambiguous", "invalid_request", "api_error", "transport_error")
)


class FacadeFailure(pydantic.BaseModel):
    """A normal façade failure value (``ok`` is always ``False``)."""

    model_config = pydantic.ConfigDict(frozen=True)

    ok: Literal[False] = False
    reason: FacadeFailureReason
    summary: str
    choices: tuple[Any, ...] = ()
    next_actions: tuple[str, ...] = ()
    cause: Any = pydantic.Field(default=None, exclude=True, repr=False)


def is_facade_failure(value: Any) -> bool:
    """Runtime guard matching the TypeScript shape check."""
    if isinstance(value, FacadeFailure):
        return True
    if not isinstance(value, dict):
        return False
    return (
        value.get("ok") is False
        and value.get("reason") in _REASONS
        and isinstance(value.get("summary"), str)
        and isinstance(value.get("choices"), (list, tuple))
        and isinstance(value.get("next_actions"), (list, tuple))
    )


def create_facade_failure(
    target_kind: Literal["Channel", "User"],
    input_value: str,
    *,
    reason: FacadeFailureReason,
    candidates: list[Any],
) -> FacadeFailure:
    """Resolver failure with labeled bounded choices, matching the TS text."""
    target = target_kind.lower()
    state = "ambiguous" if reason == "ambiguous" else "not found"
    if reason == "ambiguous":
        next_action = (
            f"Use a more exact {target_kind} value or pass one returned {target} id."
        )
    else:
        next_action = f"Check the {target} name, email, or id and try again."
    return FacadeFailure(
        reason=reason,
        summary=f'{target_kind} "{input_value}" is {state}.',
        choices=tuple(
            _candidate_with_label(target_kind, choice) for choice in candidates
        ),
        next_actions=(next_action,),
    )


def create_facade_invalid_request(summary: str, next_action: str) -> FacadeFailure:
    return FacadeFailure(
        reason="invalid_request",
        summary=summary,
        next_actions=(next_action,),
    )


def create_facade_operation_failure(
    reason: Literal["api_error", "transport_error"],
    summary: str,
    next_action: str,
    error: Any,
) -> FacadeFailure:
    return FacadeFailure(
        reason=reason,
        summary=summary,
        next_actions=(next_action,),
        cause=error,
    )


def assert_facade_ok(value: Any) -> Any:
    """Explicit exception adapter: return successes, raise on failures."""
    ok = value.get("ok") if isinstance(value, dict) else getattr(value, "ok", None)
    if ok is True:
        return value

    if isinstance(value, dict):
        summary = value.get("summary")
        next_actions = value.get("next_actions")
    else:
        summary = getattr(value, "summary", None)
        next_actions = getattr(value, "next_actions", None)

    suffix = ""
    if next_actions:
        suffix = f" Next actions: {' '.join(next_actions)}"
    raise FacadeError(f"{summary or 'Facade operation failed.'}{suffix}", value)


class FacadeError(Exception):
    """Raised by ``assert_facade_ok`` for callers that prefer exceptions."""

    def __init__(self, message: str, failure: Any):
        super().__init__(message)
        self.failure = failure


def _candidate_with_label(target_kind: Literal["Channel", "User"], choice: Any) -> Any:
    if not isinstance(choice, dict) or "label" in choice:
        return choice
    if target_kind == "Channel" and {"id", "name", "channel_type"} <= choice.keys():
        return {
            **choice,
            "label": format_channel_candidate_label(
                id=choice["id"],
                name=choice["name"],
                channel_type=choice["channel_type"],
            ),
        }
    if target_kind == "User" and {"id", "email", "name"} <= choice.keys():
        return {
            **choice,
            "label": format_user_candidate_label(
                id=choice["id"], email=choice["email"], name=choice["name"]
            ),
        }
    return choice
