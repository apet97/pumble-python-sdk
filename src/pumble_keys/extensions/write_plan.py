"""Write plans: canonical previews and signed confirmation tokens.

Ported from ``extensions/write-plan.ts`` with the plan-mandated
hardening: previews additionally bind an issued/expiry time, the
workspace fingerprint, and a canonical request hash, so a stateless
remote instance can verify a confirmation with nothing but the shared
secret. A token authorizes ONE attempt; it does not make the Pumble
API idempotent.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from collections import OrderedDict
from typing import Any, Literal

import pydantic

from pumble_keys.extensions.redaction import redact_sensitive_text

WriteRiskLevel = Literal["low", "medium", "high"]

TOKEN_PREFIX = "pumble-write-plan-v1"
TEXT_EXCERPT_MAX_LENGTH = 160
DEFAULT_TTL_MS = 5 * 60 * 1000

_HIGH_RISK = re.compile(
    r"delete|remove|revoke|archive|deactivate|cancel", re.IGNORECASE
)
_MEDIUM_RISK = re.compile(
    r"send|post|reply|create|update|edit|invite|set|clear", re.IGNORECASE
)


class WritePreview(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    action_type: str
    target_kind: str
    target_id: str | None = None
    target_name: str | None = None
    text_excerpt: str
    text_sha256: str
    risk_level: WriteRiskLevel
    workspace_id: str
    issued_at_ms: int
    expires_at_ms: int
    request_sha256: str


def canonical_json(value: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, drop ``None``."""
    if value is None or not isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    entries = sorted((key, item) for key, item in value.items() if item is not None)
    return (
        "{"
        + ",".join(
            f"{json.dumps(key, ensure_ascii=False)}:{canonical_json(item)}"
            for key, item in entries
        )
        + "}"
    )


def hash_text(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def hash_request(request: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(request).encode("utf-8")).hexdigest()


def excerpt_text(text: str | None) -> str:
    if not isinstance(text, str):
        return ""
    redacted = redact_sensitive_text(re.sub(r"\s+", " ", text).strip())
    if len(redacted) <= TEXT_EXCERPT_MAX_LENGTH:
        return redacted
    return redacted[: TEXT_EXCERPT_MAX_LENGTH - 3].rstrip() + "..."


def infer_risk_level(action_type: str) -> WriteRiskLevel:
    if _HIGH_RISK.search(action_type):
        return "high"
    if _MEDIUM_RISK.search(action_type):
        return "medium"
    return "low"


def create_write_preview(
    *,
    action_type: str,
    target_kind: str,
    target_id: str | None = None,
    target_name: str | None = None,
    text: str | None = None,
    risk_level: WriteRiskLevel | None = None,
    workspace_id: str,
    request: dict[str, Any],
    now_ms: int,
    ttl_ms: int = DEFAULT_TTL_MS,
) -> WritePreview:
    if not action_type.strip():
        raise ValueError("create_write_preview: action type is required")
    if not target_kind.strip():
        raise ValueError("create_write_preview: target kind is required")
    if not (target_id or target_name):
        raise ValueError("create_write_preview: target id or target name is required")
    return WritePreview(
        action_type=action_type.strip(),
        target_kind=target_kind.strip(),
        target_id=target_id,
        target_name=target_name,
        text_excerpt=excerpt_text(text),
        text_sha256=hash_text(text),
        risk_level=risk_level or infer_risk_level(action_type),
        workspace_id=workspace_id,
        issued_at_ms=now_ms,
        expires_at_ms=now_ms + ttl_ms,
        request_sha256=hash_request(request),
    )


def _require_secret(secret: bytes | str) -> bytes:
    raw = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
    if not raw:
        raise ValueError("confirmation secret must be non-empty")
    return raw


def create_confirmation_token(preview: WritePreview, secret: bytes | str) -> str:
    digest = hmac.new(
        _require_secret(secret),
        canonical_json(preview.model_dump()).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"{TOKEN_PREFIX}.{encoded}"


def verify_confirmation_token(
    preview: WritePreview, token: str, secret: bytes | str
) -> bool:
    if not isinstance(token, str) or not token.startswith(f"{TOKEN_PREFIX}."):
        return False
    expected = create_confirmation_token(preview, secret)
    return hmac.compare_digest(token.encode(), expected.encode())


def validate_confirmation(
    *,
    preview: WritePreview,
    token: str,
    secret: bytes | str,
    now_ms: int,
    workspace_id: str,
    request: dict[str, Any],
    text: str | None,
) -> str | None:
    """Full confirmed-write check. Returns a failure reason or ``None``.

    Order: signature, expiry, workspace binding, request equality,
    text-hash binding. Every check fails closed.
    """
    if not verify_confirmation_token(preview, token, secret):
        return "invalid_token"
    if now_ms > preview.expires_at_ms:
        return "expired"
    if workspace_id != preview.workspace_id:
        return "workspace_mismatch"
    if hash_request(request) != preview.request_sha256:
        return "request_mismatch"
    if hash_text(text) != preview.text_sha256:
        return "text_mismatch"
    return None


class ReplayGuard:
    """Bounded in-memory used-token store.

    One process only: a write-enabled multi-worker deployment needs a
    shared replay store or a single worker — do not pretend otherwise.
    """

    def __init__(self, max_entries: int = 1024) -> None:
        if max_entries < 1:
            raise ValueError("ReplayGuard: max_entries must be >= 1")
        self._max_entries = max_entries
        self._seen: OrderedDict[str, None] = OrderedDict()

    def consume(self, token: str) -> bool:
        """False when the token was already consumed."""
        if token in self._seen:
            return False
        self._seen[token] = None
        while len(self._seen) > self._max_entries:
            self._seen.popitem(last=False)
        return True
