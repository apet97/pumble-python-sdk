"""Pumble webhook ingress: raw-body HMAC verification and dispatch.

Ported from ``extensions/webhooks.ts``. Verification happens over the
raw bytes exactly as received — never parse-and-reserialize before
checking the signature. Response contract:

- 401 — signature or timestamp failure;
- 400 — malformed JSON, malformed event body, or unsupported payload;
- 413 — body over the size limit (default 1 MiB);
- 204 — verified, normalized, and dispatched;
- 500 — a handler raised (reported through ``on_error``).

The signature is HMAC-SHA256 of ``<timestamp>:<raw-body>`` with the
signing secret, hex-encoded, compared timing-safe. Timestamps are
accepted in seconds or milliseconds with a default ±300-second window.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import math
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pumble_keys.pumble_app.events import (
    PumbleWebhookEvent,
    normalize_webhook_event,
)

PUMBLE_REQUEST_TIMESTAMP_HEADER = "x-pumble-request-timestamp"
PUMBLE_REQUEST_SIGNATURE_HEADER = "x-pumble-request-signature"

DEFAULT_TIMESTAMP_TOLERANCE_SECONDS = 300
DEFAULT_MAX_BODY_BYTES = 1024 * 1024

_HEX = re.compile(r"^[0-9a-f]+$", re.IGNORECASE)

EventHandler = Callable[[PumbleWebhookEvent], Awaitable[None] | None]


@dataclass(frozen=True)
class WebhookResult:
    status: int
    body: str
    headers: dict[str, str] = field(default_factory=dict)


def _header_value(headers: Mapping[str, Any], name: str) -> str | None:
    lowered = {str(key).lower(): value for key, value in headers.items()}
    value = lowered.get(name)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return value if isinstance(value, str) else None


def _parse_timestamp_ms(timestamp: str) -> float | None:
    try:
        numeric = float(timestamp)
    except ValueError:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric * 1000 if numeric < 1_000_000_000_000 else numeric


def _timing_safe_hex_equal(actual_hex: str, expected_hex: str) -> bool:
    actual = actual_hex.strip()
    if not _HEX.fullmatch(actual):
        return False
    if len(actual) != len(expected_hex):
        return False
    return hmac.compare_digest(bytes.fromhex(actual), bytes.fromhex(expected_hex))


def verify_pumble_signature(
    *,
    headers: Mapping[str, Any],
    raw_body: bytes,
    signing_secret: str,
    tolerance_ms: float,
    now_ms: Callable[[], float],
) -> tuple[bool, str]:
    timestamp = _header_value(headers, PUMBLE_REQUEST_TIMESTAMP_HEADER)
    signature = _header_value(headers, PUMBLE_REQUEST_SIGNATURE_HEADER)
    if timestamp is None or signature is None:
        return (
            False,
            "Invalid Pumble signature: missing timestamp or signature",
        )

    timestamp_ms = _parse_timestamp_ms(timestamp)
    if timestamp_ms is None:
        return False, "Invalid Pumble signature: bad timestamp"
    if abs(now_ms() - timestamp_ms) > tolerance_ms:
        return False, "Invalid Pumble signature: stale timestamp"

    expected = hmac.new(
        signing_secret.encode("utf-8"),
        timestamp.encode("utf-8") + b":" + raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not _timing_safe_hex_equal(signature, expected):
        return False, "Invalid Pumble signature"
    return True, ""


def sign_pumble_request(*, signing_secret: str, timestamp: str, raw_body: bytes) -> str:
    """Produce the hex signature for a raw body (tests and tooling)."""
    return hmac.new(
        signing_secret.encode("utf-8"),
        timestamp.encode("utf-8") + b":" + raw_body,
        hashlib.sha256,
    ).hexdigest()


def create_webhook_handler(
    *,
    signing_secret: str,
    handlers: Mapping[str, EventHandler] | None = None,
    on_event: EventHandler | None = None,
    on_error: Callable[[BaseException], None] | None = None,
    timestamp_tolerance_seconds: float = DEFAULT_TIMESTAMP_TOLERANCE_SECONDS,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    now_ms: Callable[[], float] | None = None,
) -> Callable[[bytes, Mapping[str, Any]], Awaitable[WebhookResult]]:
    """Framework-neutral receiver: ``(raw_body, headers) -> WebhookResult``.

    ``handlers`` maps event types to callables; ``on_event`` (e.g. the
    P21 router's dispatch) receives every normalized event. Both may be
    given.
    """
    if not isinstance(signing_secret, str) or not signing_secret.strip():
        raise ValueError(
            "create_webhook_handler: signing_secret must be a non-empty string"
        )
    if max_body_bytes <= 0:
        raise ValueError(
            f"create_webhook_handler: max_body_bytes must be > 0, got {max_body_bytes}"
        )
    tolerance_ms = timestamp_tolerance_seconds * 1000
    clock = now_ms if now_ms is not None else (lambda: time.time() * 1000)
    event_handlers = dict(handlers or {})

    async def handle(raw_body: bytes, headers: Mapping[str, Any]) -> WebhookResult:
        if len(raw_body) > max_body_bytes:
            return WebhookResult(413, "Pumble webhook body too large")

        ok, message = verify_pumble_signature(
            headers=headers,
            raw_body=raw_body,
            signing_secret=signing_secret,
            tolerance_ms=tolerance_ms,
            now_ms=clock,
        )
        if not ok:
            return WebhookResult(401, message)

        try:
            parsed = json.loads(raw_body)
        except ValueError:
            return WebhookResult(400, "Malformed JSON body")

        try:
            event = normalize_webhook_event(parsed)
        except ValueError:
            return WebhookResult(400, "Malformed Pumble event body")
        if event is None:
            return WebhookResult(400, "Unsupported Pumble webhook payload")

        try:
            handler = event_handlers.get(event.type)
            if handler is not None:
                outcome = handler(event)
                if outcome is not None and isinstance(outcome, Awaitable):
                    await outcome
            if on_event is not None:
                outcome = on_event(event)
                if outcome is not None and isinstance(outcome, Awaitable):
                    await outcome
        except asyncio.CancelledError:
            raise
        except BaseException as error:  # noqa: BLE001 — 500 + on_error
            if on_error is not None:
                try:
                    on_error(error)
                except Exception:  # noqa: BLE001, S110
                    pass  # keep the response tied to the handler failure
            return WebhookResult(500, "Webhook handler failed")
        return WebhookResult(204, "")

    return handle
