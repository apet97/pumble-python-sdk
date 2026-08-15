"""Fixture sanitizer and canonical body hash.

Ported from ``extensions/testing/fixtures.ts``. The placeholder
contract matches the TypeScript record/replay tooling:

- 24-hex IDs → zero-padded sequential placeholders (already-placeholder
  IDs pass through);
- emails → ``user-N@example.invalid``;
- names → ``User N`` for user-shaped parents, else
  ``example-name-<sha8>``;
- avatar paths → a fixed redacted URL;
- message-text fields (``text``, ``tx``, ``description``, ``title``,
  ``phone``, ``code``) → ``[redacted]``.

``create_fixture_body_hash`` sorts object keys recursively before
hashing so structurally identical JSON bodies produce the same digest.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_REAL_ID = re.compile(r"\b(?![0a-d]{20}\d{4}\b)[0-9a-f]{24}\b", re.IGNORECASE)
_PLACEHOLDER_ID = re.compile(r"^(?:0{20}|a{20}|b{20}|c{20}|d{20})\d{4}$")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_EXAMPLE_NAME = re.compile(r"^example-name-[0-9a-f]{8}$", re.IGNORECASE)
_TEXT_FIELDS = frozenset({"text", "tx", "description", "title", "phone", "code"})


class _State:
    def __init__(self) -> None:
        self.id_map: dict[str, str] = {}
        self.email_map: dict[str, str] = {}
        self.user_name_map: dict[str, str] = {}
        self.name_map: dict[str, str] = {}


def _sanitize_id(value: str, state: _State) -> str:
    if _PLACEHOLDER_ID.fullmatch(value):
        return value
    if value not in state.id_map:
        state.id_map[value] = str(len(state.id_map) + 1).zfill(24)
    return state.id_map[value]


def _sanitize_email(value: str, state: _State) -> str:
    if value.endswith("@example.invalid"):
        return value
    if value not in state.email_map:
        state.email_map[value] = f"user-{len(state.email_map) + 1}@example.invalid"
    return state.email_map[value]


def _sanitize_name(value: str, parent: Any, state: _State) -> str:
    if _EXAMPLE_NAME.fullmatch(value):
        return value
    parent_record = parent if isinstance(parent, dict) else None
    if parent_record is not None and (
        "email" in parent_record
        or "role" in parent_record
        or "timeZoneId" in parent_record
    ):
        email = parent_record.get("email")
        user_key = (
            _sanitize_email(email, state)
            if isinstance(email, str)
            else parent_record.get("id", value)
        )
        key = str(user_key)
        if key not in state.user_name_map:
            state.user_name_map[key] = f"User {len(state.user_name_map) + 1}"
        return state.user_name_map[key]
    if value.startswith("sdk-livetest"):
        return "sdk-livetest-redacted"
    if value not in state.name_map:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        state.name_map[value] = f"example-name-{digest}"
    return state.name_map[value]


def _sanitize_string(value: str, key: str | None, parent: Any, state: _State) -> str:
    if key == "email":
        return _sanitize_email(value, state)
    if key in ("fullPath", "scaledPath"):
        return "https://example.invalid/redacted-avatar.png"
    if key == "name":
        return _sanitize_name(value, parent, state)
    if key is not None and key in _TEXT_FIELDS:
        return "" if value == "" else "[redacted]"
    value = _EMAIL.sub(lambda m: _sanitize_email(m.group(0), state), value)
    return _REAL_ID.sub(lambda m: _sanitize_id(m.group(0), state), value)


def _sanitize_body_text(text: str, state: _State) -> str:
    if text == "":
        return text
    try:
        parsed = json.loads(text)
    except ValueError:
        return _sanitize_string(text, None, None, state)
    return json.dumps(_sanitize(parsed, None, None, state))


def _sanitize(value: Any, key: str | None, parent: Any, state: _State) -> Any:
    if isinstance(value, str):
        if key == "body":
            return _sanitize_body_text(value, state)
        return _sanitize_string(value, key, parent, state)
    if isinstance(value, list):
        return [_sanitize(child, None, None, state) for child in value]
    if isinstance(value, dict):
        return {
            child_key: _sanitize(child_value, child_key, value, state)
            for child_key, child_value in value.items()
        }
    return value


def sanitize_pumble_fixture_value(value: Any) -> Any:
    """Redact live values with the shared placeholder contract.

    Pure per input value: each call gets fresh placeholder maps while
    preserving repeated IDs/emails/names inside that value.
    """
    return _sanitize(value, None, None, _State())


def _canonical(value: Any) -> Any:
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    return value


def create_fixture_body_hash(body: Any) -> str:
    """Stable SHA-256 hash over the canonicalized (key-sorted) body."""
    serialised = (
        "" if body is None else json.dumps(_canonical(body), separators=(",", ":"))
    )
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()
