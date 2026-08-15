"""Categorize raw SDK/transport errors for retry and reporting decisions.

Ported from ``extensions/categorize-error.ts``. The six categories and
the classification order are contract:

1. 403 with a structured body → ``validation`` (Pumble uses 403 for
   framework-layer validation rejections).
2. 401/403 → ``permission``.
3. 404 → ``not-found``.
4. 429 → ``rate-limit`` (retryable).
5. 408/425/5xx → ``transient`` (retryable).
6. 400/422 with a structured body → ``validation``.
7. Connection-level transport failures → ``transient`` (retryable).
8. Anything else → ``unknown``.

The raw error is kept only as excluded diagnostic state.
"""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx
import pydantic

ErrorCategory = Literal[
    "permission",
    "not-found",
    "rate-limit",
    "validation",
    "transient",
    "unknown",
]


class CategorizedError(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    category: ErrorCategory
    retryable: bool
    status_code: int | None
    message: str
    localized_message: str | None = None
    code: int | None = None
    raw: Any = pydantic.Field(default=None, exclude=True, repr=False)


class _Details(pydantic.BaseModel):
    message: str
    localized_message: str | None = None
    code: int | None = None
    has_validation_field: bool = False


def categorize_error(error: Any) -> CategorizedError:
    status_code = _status_code_of(error)
    details = _details_of(error)

    def result(category: ErrorCategory, retryable: bool, status: int | None):
        return CategorizedError(
            category=category,
            retryable=retryable,
            status_code=status,
            message=details.message,
            localized_message=details.localized_message,
            code=details.code,
            raw=error,
        )

    if status_code == 403 and _is_structured_like(details):
        return result("validation", False, status_code)
    if status_code in (401, 403):
        return result("permission", False, status_code)
    if status_code == 404:
        return result("not-found", False, status_code)
    if status_code == 429:
        return result("rate-limit", True, status_code)
    if status_code in (408, 425) or (status_code is not None and status_code >= 500):
        return result("transient", True, status_code)
    if status_code in (400, 422) and _is_structured_like(details):
        return result("validation", False, status_code)
    if _is_transient_transport(error):
        return result("transient", True, None)
    return result("unknown", False, status_code)


def _status_code_of(error: Any) -> int | None:
    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, bool):
        return None
    return status_code if isinstance(status_code, int) else None


def _details_of(error: Any) -> _Details:
    data = getattr(error, "data", None)
    if data is not None:
        message = getattr(data, "message", None)
        localized = getattr(data, "localized_message", None)
        code = getattr(data, "code", None)
        if isinstance(localized, str) and isinstance(message, str):
            return _Details(
                message=message,
                localized_message=localized,
                code=code if isinstance(code, int) else None,
            )
        legacy = getattr(data, "error", None)
        if isinstance(legacy, str):
            fallback = getattr(error, "message", "")
            return _Details(message=legacy or fallback)

    parsed = _parse_pumble_body(error)
    if parsed is not None:
        localized = parsed.get("localizedMessage")
        code = parsed.get("code")
        message = parsed.get("message")
        if not isinstance(message, str):
            message = parsed.get("error")
        if not isinstance(message, str):
            message = str(error) if isinstance(error, Exception) else "Unknown error"
        return _Details(
            message=message,
            localized_message=localized if isinstance(localized, str) else None,
            code=(
                code if isinstance(code, int) and not isinstance(code, bool) else None
            ),
            has_validation_field=_has_validation_style_field(parsed),
        )

    if isinstance(error, Exception):
        return _Details(message=str(error) or type(error).__name__)
    return _Details(message="Unknown error")


def _is_structured_like(details: _Details) -> bool:
    return (
        details.localized_message is not None
        or details.code is not None
        or details.has_validation_field
    )


def _parse_pumble_body(error: Any) -> dict[str, Any] | None:
    body = getattr(error, "body", None)
    if not isinstance(body, str) or not body.strip():
        return None
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _has_validation_style_field(record: dict[str, Any]) -> bool:
    if not isinstance(record.get("message"), str):
        return False
    return (
        isinstance(record.get("field"), str)
        or isinstance(record.get("fields"), list)
        or isinstance(record.get("errors"), list)
        or isinstance(record.get("violations"), list)
    )


def _is_transient_transport(error: Any) -> bool:
    """Connection-level failures map to the TS transient network codes."""
    return isinstance(error, (httpx.TransportError, ConnectionError, TimeoutError))
