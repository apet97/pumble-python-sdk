"""Shared failure classification for façade operations.

Ported from ``extensions/facade-operation.ts``: turn a raised error into
an ``api_error``/``transport_error`` façade failure without losing the
cause internally, and guard against already-failed resolver results.
"""

from __future__ import annotations

from typing import Any, Literal

from pumble_keys.extensions.results import (
    FacadeFailure,
    create_facade_operation_failure,
)

OPERATION_FAILURE_NEXT_ACTION = (
    "Inspect the raw error or retry after correcting the request."
)


def operation_failure_reason(
    error: Any,
) -> Literal["api_error", "transport_error"]:
    """HTTP-shaped errors are API failures; everything else is transport."""
    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int) and not isinstance(status_code, bool):
        return "api_error"
    return "transport_error"


def operation_failure(summary: str, error: Any) -> FacadeFailure:
    """Build the standard operation-failure value for a raised error."""
    return create_facade_operation_failure(
        operation_failure_reason(error),
        summary,
        OPERATION_FAILURE_NEXT_ACTION,
        error,
    )


def is_facade_operation_failure(value: Any) -> bool:
    """True when a resolver/preflight step already returned a failure."""
    if isinstance(value, FacadeFailure):
        return True
    return isinstance(value, dict) and value.get("ok") is False
