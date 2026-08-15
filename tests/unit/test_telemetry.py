"""P18: telemetry — allowlisted attributes, canary leak scan, no-op mode."""

from __future__ import annotations

import json
import stat
import sys

import pytest

from pumble_keys.extensions.telemetry import (
    SPAN_ATTRIBUTE_ALLOWLIST,
    JsonlAuditWriter,
    NoopRecorder,
    create_otel_span_recorder,
    filter_span_attributes,
    traced,
)

CANARY_KEY = "pmb_super_secret_canary"
CANARY_EMAIL = "real.person@example.com"
CANARY_ID = "abcdefabcdefabcdefabcdef"
CANARY_TEXT = "private message body canary"


class FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict = {}
        self.status: dict = {}
        self.ended = False

    def end(self) -> None:
        self.ended = True

    def set_status(self, *, ok: bool, error_class: str | None = None) -> None:
        self.status = {"ok": ok, "error_class": error_class}

    def set_attributes(self, attrs: dict) -> None:
        self.attributes.update(filter_span_attributes(attrs))


class FakeRecorder:
    def __init__(self) -> None:
        self.spans: list[tuple[str, FakeSpan]] = []

    def start_span(self, name: str, attrs: dict | None = None) -> FakeSpan:
        span = FakeSpan()
        span.attributes.update(filter_span_attributes(attrs or {}))
        self.spans.append((name, span))
        return span


def test_filter_drops_forbidden_attributes() -> None:
    filtered = filter_span_attributes(
        {
            "operation_id": "sendMessage",
            "http_method": "POST",
            "status_class": "2xx",
            "retry_count": 0,
            "duration_ms": 12.5,
            "result_category": "ok",
            "count": 3,
            "api_key": CANARY_KEY,
            "text": CANARY_TEXT,
            "email": CANARY_EMAIL,
            "message_id_full": CANARY_ID,
            "body": {"text": CANARY_TEXT},
        }
    )
    assert set(filtered) <= SPAN_ATTRIBUTE_ALLOWLIST
    dumped = json.dumps(filtered)
    for canary in (CANARY_KEY, CANARY_EMAIL, CANARY_ID, CANARY_TEXT):
        assert canary not in dumped


@pytest.mark.asyncio
async def test_traced_success_records_span_and_audit(tmp_path) -> None:
    recorder = FakeRecorder()
    writer = JsonlAuditWriter(str(tmp_path / "audit.jsonl"))

    async def op():
        return "value"

    result = await traced(
        "pumble.api.sendMessage",
        op(),
        recorder=recorder,
        writer=writer,
        attributes={"operation_id": "sendMessage", "api_key": CANARY_KEY},
    )
    assert result == "value"
    name, span = recorder.spans[0]
    assert name == "pumble.api.sendMessage"
    assert span.ended and span.status["ok"] is True
    assert "api_key" not in span.attributes

    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    event = json.loads(lines[0])
    assert event["op"] == "pumble.api.sendMessage"
    assert event["ok"] is True
    assert CANARY_KEY not in lines[0]


@pytest.mark.asyncio
async def test_traced_failure_records_error_class_not_message(tmp_path) -> None:
    recorder = FakeRecorder()
    writer = JsonlAuditWriter(str(tmp_path / "audit.jsonl"))

    async def op():
        raise RuntimeError(f"secret {CANARY_KEY} inside")

    with pytest.raises(RuntimeError):
        await traced("pumble.api.sendMessage", op(), recorder=recorder, writer=writer)
    _name, span = recorder.spans[0]
    assert span.status == {"ok": False, "error_class": "RuntimeError"}
    line = (tmp_path / "audit.jsonl").read_text()
    assert json.loads(line)["error_class"] == "RuntimeError"
    assert CANARY_KEY not in line


@pytest.mark.asyncio
async def test_traced_noop_mode_is_plain_await() -> None:
    async def op():
        return 42

    assert await traced("x", op()) == 42


def test_audit_writer_redacts_and_uses_owner_only_mode(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    writer = JsonlAuditWriter(str(path))
    writer.write(
        {
            "op": "write",
            "api_key": CANARY_KEY,
            "text": CANARY_TEXT,
            "note": f"sent by {CANARY_EMAIL} in {CANARY_ID}",
        }
    )
    content = path.read_text()
    for canary in (CANARY_KEY, CANARY_EMAIL, CANARY_ID, CANARY_TEXT):
        assert canary not in content
    assert json.loads(content)["op"] == "write"
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_audit_writer_failure_warns_once_never_raises(tmp_path, capsys) -> None:
    writer = JsonlAuditWriter(str(tmp_path / "missing-dir" / "audit.jsonl"))
    writer.write({"op": "a"})
    writer.write({"op": "b"})
    err = capsys.readouterr().err
    assert err.count("audit-log write failed") == 1


def test_otel_recorder_degrades_to_noop_without_dependency(monkeypatch) -> None:
    # Simulate an environment without opentelemetry: poisoning the module
    # entries makes `import opentelemetry` raise ImportError.
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", None)
    recorder = create_otel_span_recorder()
    assert isinstance(recorder, NoopRecorder)
    span = recorder.start_span("x")
    span.set_status(ok=True)
    span.end()


def test_otel_recorder_uses_api_when_installed() -> None:
    pytest.importorskip("opentelemetry")
    recorder = create_otel_span_recorder()
    span = recorder.start_span(
        "pumble.api.myInfo",
        {"operation_id": "myInfo", "api_key": CANARY_KEY},
    )
    span.set_attributes({"duration_ms": 1.0, "text": CANARY_TEXT})
    span.set_status(ok=True)
    span.end()


def test_no_required_telemetry_dependency_declared() -> None:
    import tomllib
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent.parent
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text())
    declared = " ".join(pyproject["project"]["dependencies"])
    assert "opentelemetry" not in declared, (
        "opentelemetry must stay optional in this project's own dependency "
        "list (transitive presence via mcp[cli] is fine)"
    )
