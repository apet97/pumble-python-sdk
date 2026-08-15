"""Deterministic redaction for diagnostics, previews, and debug output.

Two families, ported from the TypeScript reference:

- ``redact_sensitive_text`` (from ``extensions/write-plan.ts``): strips
  credential material out of free text while preserving surrounding
  structure for debugging.
- ``redact_debug_value`` / ``redact_debug_headers`` (from
  ``extensions/debug-redaction.ts``): recursively redact structured
  debug data — secret-named keys, message-body keys, emails, and
  24-character hex Pumble IDs.

Redaction is deterministic: the same input always produces the same
output. Never log a value that has not passed through one of these.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "<redacted>"

_SECRET_KEY_PATTERN = re.compile(
    r"api[-_ ]?key|authorization|token|secret|password|cookie|signature",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_HEX_ID_PATTERN = re.compile(r"\b[0-9a-f]{24}\b", re.IGNORECASE)
_BODY_TEXT_KEYS = frozenset({"text", "tx", "message", "description"})

_PMB_TOKEN_PATTERN = re.compile(r"\bpmb_[A-Za-z0-9_-]+\b")
_BEARER_BASIC_PATTERN = re.compile(
    r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE
)
_ASSIGNMENT_PATTERN = re.compile(
    r"\b(api[-_ ]?key|access[-_ ]?token|refresh[-_ ]?token|token|secret|password)"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
    re.IGNORECASE,
)


def redact_sensitive_text(text: str) -> str:
    """Strip credential material from free text; keep ordinary prose intact."""
    text = _PMB_TOKEN_PATTERN.sub("[redacted]", text)
    text = _BEARER_BASIC_PATTERN.sub(lambda m: f"{m.group(1)} [redacted]", text)
    return _ASSIGNMENT_PATTERN.sub(lambda m: f"{m.group(1)}=[redacted]", text)


def _redact_debug_string(value: str) -> str:
    value = _EMAIL_PATTERN.sub(REDACTED, value)
    return _HEX_ID_PATTERN.sub(REDACTED, value)


def redact_debug_value(
    value: Any,
    key: str = "",
    *,
    sensitive_keys: frozenset[str] = frozenset(),
) -> Any:
    """Recursively redact structured debug data.

    Values under secret-named keys, message-body keys, or configured
    ``sensitive_keys`` are replaced whole; other strings lose embedded
    emails and 24-hex IDs.
    """
    if isinstance(value, str):
        if (
            _SECRET_KEY_PATTERN.search(key)
            or key in _BODY_TEXT_KEYS
            or key in sensitive_keys
        ):
            return REDACTED
        return _redact_debug_string(value)

    if isinstance(value, (list, tuple)):
        return [
            redact_debug_value(item, key, sensitive_keys=sensitive_keys)
            for item in value
        ]

    if isinstance(value, Mapping):
        return {
            child_key: redact_debug_value(
                child_value, str(child_key), sensitive_keys=sensitive_keys
            )
            for child_key, child_value in value.items()
        }

    return value


def redact_debug_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Lower-case header names; redact secret-named headers whole."""
    out: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        out[lower] = (
            REDACTED
            if _SECRET_KEY_PATTERN.search(lower)
            else _redact_debug_string(value)
        )
    return out
