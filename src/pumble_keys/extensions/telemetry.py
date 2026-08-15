"""Sanitized telemetry: optional OTel spans and a redacted JSONL audit sink.

Ported from ``extensions/telemetry.ts``. Three independent blocks:

1. ``create_otel_span_recorder`` — uses ``opentelemetry-api`` when the
   consumer installed it; otherwise returns the same no-op recorder as
   ``NoopRecorder``. Telemetry adds no required runtime dependency.
2. ``JsonlAuditWriter`` — appends one redacted JSON line per event.
   Write failures warn once on stderr and never raise into the SDK
   call path. Create audit files with owner-only permissions (0600);
   the writer sets that mode when it creates the file.
3. ``traced`` — wraps one awaitable in a span + audit event.

Attribute policy (§10.7): only the allowlisted keys survive —
operation ID, HTTP method, status class, retry count, duration, result
category, and bounded counts. Bodies, message text, emails, API keys,
tokens, and full Pumble IDs are forbidden; values are additionally
passed through the debug redactor as a second line of defense.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any, Protocol

from pumble_keys.extensions.redaction import redact_debug_value

SPAN_ATTRIBUTE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "operation_id",
        "http_method",
        "status_class",
        "status_code",
        "retry_count",
        "duration_ms",
        "result_category",
        "count",
        "page_count",
        "error_class",
    }
)


class RecorderSpan(Protocol):
    def end(self) -> None: ...

    def set_status(self, *, ok: bool, error_class: str | None = None) -> None: ...

    def set_attributes(self, attrs: dict[str, Any]) -> None: ...


class SpanRecorder(Protocol):
    def start_span(
        self, name: str, attrs: dict[str, Any] | None = None
    ) -> RecorderSpan: ...


class _NoopSpan:
    def end(self) -> None:
        return None

    def set_status(self, *, ok: bool, error_class: str | None = None) -> None:
        return None

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        return None


class NoopRecorder:
    """No-op ``SpanRecorder``; also the fallback when OTel is missing."""

    def start_span(self, name: str, attrs: dict[str, Any] | None = None) -> _NoopSpan:
        return _NoopSpan()


def filter_span_attributes(attrs: dict[str, Any]) -> dict[str, Any]:
    """Drop non-allowlisted keys; redact surviving string values."""
    return {
        key: redact_debug_value(value) if isinstance(value, str) else value
        for key, value in attrs.items()
        if key in SPAN_ATTRIBUTE_ALLOWLIST
    }


class _OTelSpan:
    def __init__(self, span: Any, status_code_cls: Any) -> None:
        self._span = span
        self._status = status_code_cls

    def end(self) -> None:
        self._span.end()

    def set_status(self, *, ok: bool, error_class: str | None = None) -> None:
        from opentelemetry.trace import Status

        if ok:
            self._span.set_status(Status(self._status.OK))
        else:
            self._span.set_status(Status(self._status.ERROR, error_class or "error"))

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        for key, value in filter_span_attributes(attrs).items():
            self._span.set_attribute(key, value)


class _OTelRecorder:
    def __init__(self, tracer: Any, status_code_cls: Any) -> None:
        self._tracer = tracer
        self._status = status_code_cls

    def start_span(self, name: str, attrs: dict[str, Any] | None = None) -> _OTelSpan:
        span = self._tracer.start_span(
            name, attributes=filter_span_attributes(attrs or {})
        )
        return _OTelSpan(span, self._status)


def create_otel_span_recorder(
    tracer_name: str = "pumble-keys-sdk",
    tracer_version: str | None = None,
) -> SpanRecorder:
    """OTel-backed recorder, or a no-op when the API is not installed."""
    try:
        from opentelemetry import trace
        from opentelemetry.trace import StatusCode
    except ImportError:
        return NoopRecorder()
    tracer = trace.get_tracer(tracer_name, tracer_version)
    return _OTelRecorder(tracer, StatusCode)


class JsonlAuditWriter:
    """Append-only redacted JSONL audit sink for write attempts/results.

    The file is created with mode 0600 (owner read/write only); keep it
    on a private volume. Every event passes through the debug redactor
    before serialization.
    """

    def __init__(
        self,
        path: str,
        *,
        sensitive_keys: frozenset[str] = frozenset(),
    ) -> None:
        self._path = path
        self._sensitive_keys = sensitive_keys
        self._warned = False

    def write(self, event: dict[str, Any]) -> None:
        """Append one event. Never raises into the caller."""
        redacted = redact_debug_value(event, sensitive_keys=self._sensitive_keys)
        try:
            line = json.dumps(redacted, default=str) + "\n"
            fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)
        except OSError as error:
            if not self._warned:
                self._warned = True
                print(
                    f"[pumble-keys-sdk] audit-log write failed ({self._path}): {error}",
                    file=sys.stderr,
                )


async def traced(
    name: str,
    awaitable: Any,
    *,
    recorder: SpanRecorder | None = None,
    writer: JsonlAuditWriter | None = None,
    attributes: dict[str, Any] | None = None,
    now: Any = time.monotonic,
    wall_now: Any = None,
) -> Any:
    """Run one awaitable inside a span; emit one redacted audit event.

    With no recorder and no writer this is a plain await — zero cost,
    zero dependencies. Cancellation propagates and is not recorded as a
    failure of the operation.
    """
    if recorder is None and writer is None:
        return await awaitable

    active_recorder = recorder or NoopRecorder()
    span = active_recorder.start_span(name, attributes or {})
    start = now()
    ok = True
    error_class: str | None = None
    try:
        return await awaitable
    except asyncio.CancelledError:
        span.end()
        raise
    except BaseException as error:
        ok = False
        error_class = type(error).__name__
        raise
    finally:
        if ok or error_class is not None:
            duration_ms = max(0.0, (now() - start) * 1000)
            span.set_status(ok=ok, error_class=error_class)
            span.set_attributes({**(attributes or {}), "duration_ms": duration_ms})
            span.end()
            if writer is not None:
                timestamp = wall_now() if wall_now is not None else time.time()
                event: dict[str, Any] = {
                    "ts": timestamp,
                    "op": name,
                    "ok": ok,
                    "duration_ms": duration_ms,
                    **filter_span_attributes(attributes or {}),
                }
                if error_class is not None:
                    event["error_class"] = error_class
                writer.write(event)
