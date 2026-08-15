"""P31: raw profiles — exact 11/26, gates, annotations, audit, dry-run."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.profiles import Profile
from pumble_keys.mcp_server.server import create_server
from pumble_keys.mcp_server.tools.raw_manifest import (
    RAW_READ_OPERATIONS,
    RAW_WRITE_OPERATIONS,
)
from pumble_keys.mcp_server.tools.raw_write import RawWriteGateError
from tests.mcp.harness import mcp_session, structured

KEY = "test-key-not-real"
CHANNEL_ID = "0" * 20 + "0001"
MESSAGE_ID = "0" * 20 + "0002"
REPO = Path(__file__).resolve().parent.parent.parent

DESTRUCTIVE = {
    "raw_remove_user_from_channel",
    "raw_delete_message",
    "raw_remove_reaction",
    "raw_delete_scheduled_message",
}


class Recorder:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.value


def make_raw():
    recorders: dict[str, Recorder] = {}

    def namespace(methods: dict[str, Recorder]):
        recorders.update(methods)
        return SimpleNamespace(**methods)

    raw = SimpleNamespace(
        channels=namespace(
            {
                "list_channels_async": Recorder([]),
                "get_channel_async": Recorder(
                    SimpleNamespace(channel=SimpleNamespace(id=CHANNEL_ID))
                ),
                "create_channel_async": Recorder(
                    SimpleNamespace(id=CHANNEL_ID, name="fresh")
                ),
                "add_users_to_channel_async": Recorder({}),
                "remove_user_from_channel_async": Recorder({}),
            }
        ),
        messages=namespace(
            {
                "send_message_async": Recorder(
                    SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)
                ),
                "send_reply_async": Recorder(
                    SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)
                ),
                "dm_user_async": Recorder(
                    SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)
                ),
                "dm_group_async": Recorder(
                    SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)
                ),
                "fetch_message_async": Recorder(SimpleNamespace(id=MESSAGE_ID)),
                "fetch_thread_replies_async": Recorder(SimpleNamespace(result=[])),
                "search_messages_async": Recorder(
                    SimpleNamespace(result=SimpleNamespace(content=[], has_more=False))
                ),
                "delete_message_async": Recorder({}),
                "list_messages_async": Recorder(
                    SimpleNamespace(result=SimpleNamespace(messages=[]))
                ),
                "add_reaction_async": Recorder({}),
                "remove_reaction_async": Recorder({}),
                "edit_message_async": Recorder({}),
            }
        ),
        scheduled_messages=namespace(
            {
                "create_scheduled_message_async": Recorder(SimpleNamespace(id="s1")),
                "fetch_scheduled_messages_async": Recorder(
                    SimpleNamespace(result=SimpleNamespace(scheduled_messages=[]))
                ),
                "fetch_scheduled_message_async": Recorder(SimpleNamespace(id="s1")),
                "edit_scheduled_message_async": Recorder(SimpleNamespace(id="s1")),
                "delete_scheduled_message_async": Recorder(None),
            }
        ),
        users=namespace(
            {
                "list_users_async": Recorder([]),
                "list_user_groups_async": Recorder([]),
                "my_info_async": Recorder(SimpleNamespace(id="u1")),
                "custom_status_async": Recorder({}),
            }
        ),
    )
    return raw, recorders


def make_server(profile: Profile, tmp_path=None, *, dry_run=False):
    from pumble_keys.extensions.client import create_pumble_client

    raw, recorders = make_raw()
    kwargs = {}
    if profile is Profile.READWRITE:
        kwargs = {
            "allow_raw_writes": True,
            "audit_log_path": str(tmp_path / "audit.jsonl"),
            "dry_run": dry_run,
        }
    server = create_server(
        McpConfig(api_key=KEY, profile=profile, **kwargs),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )
    return server, recorders


def test_manifest_matches_operations_ledger() -> None:
    ledger = json.loads((REPO / "contracts" / "operations.json").read_text())
    reads = [op for op in ledger if op["class"] == "read"]
    writes = [op for op in ledger if op["class"] == "write"]
    assert [op.operation_id for op in RAW_READ_OPERATIONS] == [
        op["operationId"] for op in reads
    ]
    assert [op.operation_id for op in RAW_WRITE_OPERATIONS] == [
        op["operationId"] for op in writes
    ]
    by_id = {op["operationId"]: op for op in ledger}
    for op in (*RAW_READ_OPERATIONS, *RAW_WRITE_OPERATIONS):
        assert op.http == by_id[op.operation_id]["method"]
        assert op.path == by_id[op.operation_id]["path"]


@pytest.mark.asyncio
async def test_readonly_registers_exactly_11(tmp_path) -> None:
    server, _ = make_server(Profile.READONLY)
    tools = await server.list_tools()
    assert [tool.name for tool in tools][:11] == [
        op.tool_name for op in RAW_READ_OPERATIONS
    ]
    raw_tools = [t for t in tools if t.name.startswith("raw_")]
    assert len(raw_tools) == 11
    for tool in raw_tools:
        assert tool.annotations.read_only_hint is True


@pytest.mark.asyncio
async def test_readwrite_registers_exactly_26_with_annotations(
    tmp_path,
) -> None:
    server, _ = make_server(Profile.READWRITE, tmp_path)
    tools = {t.name: t for t in await server.list_tools() if t.name.startswith("raw_")}
    assert len(tools) == 26
    for op in RAW_WRITE_OPERATIONS:
        annotations = tools[op.tool_name].annotations
        assert annotations.idempotent_hint is False  # every write
        assert annotations.destructive_hint is (op.tool_name in DESTRUCTIVE)


def test_gates_block_unguarded_readwrite(tmp_path) -> None:
    # Gate 1: config validation.
    with pytest.raises(ValueError, match="allow_raw_writes"):
        McpConfig(api_key=KEY, profile=Profile.READWRITE)
    # Gate 2: registrar re-check (bypassing config via a curated config).
    from pumble_keys.mcp_server.tools import raw_write

    class FakeServer:
        def tool(self, **kwargs):
            return lambda fn: fn

    with pytest.raises(RawWriteGateError, match="allow_raw_writes"):
        raw_write.register(FakeServer(), McpConfig(api_key=KEY))


@pytest.mark.asyncio
async def test_every_read_adapter_calls_its_operation(tmp_path) -> None:
    server, recorders = make_server(Profile.READONLY)
    arguments = {
        "raw_get_channel": {"channel_id": CHANNEL_ID},
        "raw_fetch_message": {"message_id": MESSAGE_ID},
        "raw_fetch_thread_replies": {"root_message_id": MESSAGE_ID},
        "raw_search_messages": {"text": "x"},
        "raw_list_messages": {"channel_id": CHANNEL_ID},
        "raw_fetch_scheduled_messages": {},
        "raw_fetch_scheduled_message": {"scheduled_message_id": "s1"},
    }
    async with mcp_session(server) as session:
        for op in RAW_READ_OPERATIONS:
            result = structured(
                await session.call_tool(op.tool_name, arguments.get(op.tool_name, {}))
            )
            assert result["ok"] is True, op.tool_name
            assert len(recorders[op.method].calls) == 1, op.tool_name


@pytest.mark.asyncio
async def test_every_write_adapter_calls_once_and_audits(tmp_path) -> None:
    server, recorders = make_server(Profile.READWRITE, tmp_path)
    arguments = {
        "raw_create_channel": {"name": "fresh", "type_": "PUBLIC"},
        "raw_add_users_to_channel": {
            "channel_id": CHANNEL_ID,
            "user_ids": ["u1"],
        },
        "raw_remove_user_from_channel": {
            "channel_id": CHANNEL_ID,
            "user_id": "u1",
        },
        "raw_send_message": {"text": "t", "channel_id": CHANNEL_ID},
        "raw_send_reply": {
            "text": "t",
            "message_id": MESSAGE_ID,
            "channel_id": CHANNEL_ID,
        },
        "raw_dm_user": {"user_id": "u1", "text": "t"},
        "raw_dm_group": {"user_ids": ["u1"], "text": "t"},
        "raw_delete_message": {"message_id": MESSAGE_ID},
        "raw_add_reaction": {"message_id": MESSAGE_ID, "reaction": ":+1:"},
        "raw_remove_reaction": {"message_id": MESSAGE_ID, "reaction": ":+1:"},
        "raw_edit_message": {
            "message_id": MESSAGE_ID,
            "channel_id": CHANNEL_ID,
            "text": "t",
        },
        "raw_create_scheduled_message": {
            "channel_id": CHANNEL_ID,
            "text": "t",
            "send_at": 99,
        },
        "raw_edit_scheduled_message": {
            "scheduled_message_id": "s1",
            "channel_id": CHANNEL_ID,
            "text": "t",
            "send_at": 99,
        },
        "raw_delete_scheduled_message": {"scheduled_message_id": "s1"},
        "raw_custom_status": {"code": ":zap:", "expires_at": 0},
    }
    async with mcp_session(server) as session:
        for op in RAW_WRITE_OPERATIONS:
            result = structured(
                await session.call_tool(op.tool_name, arguments[op.tool_name])
            )
            assert result["ok"] is True, op.tool_name
            assert len(recorders[op.method].calls) == 1, op.tool_name

    audit_lines = (tmp_path / "audit.jsonl").read_text().strip().splitlines()
    events = [json.loads(line) for line in audit_lines]
    # attempt + success per write.
    assert len(events) == 30
    assert {event["outcome"] for event in events} == {"attempt", "success"}
    assert all(event["kind"] == "raw_write" for event in events)


@pytest.mark.asyncio
async def test_request_wrapped_writes_build_request_dict(tmp_path) -> None:
    server, recorders = make_server(Profile.READWRITE, tmp_path)
    async with mcp_session(server) as session:
        await session.call_tool(
            "raw_send_message",
            {"text": "hello", "channel_id": CHANNEL_ID},
        )
    assert recorders["send_message_async"].calls == [
        {"request": {"text": "hello", "channel_id": CHANNEL_ID}}
    ]


@pytest.mark.asyncio
async def test_write_failure_single_attempt_audited(tmp_path) -> None:
    from pumble_keys.extensions.client import create_pumble_client

    raw, recorders = make_raw()
    raw.messages.send_message_async = Recorder(error=ConnectionError("down"))
    recorders["send_message_async"] = raw.messages.send_message_async
    server = create_server(
        McpConfig(
            api_key=KEY,
            profile=Profile.READWRITE,
            allow_raw_writes=True,
            audit_log_path=str(tmp_path / "audit.jsonl"),
        ),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )
    async with mcp_session(server) as session:
        result = structured(
            await session.call_tool(
                "raw_send_message", {"text": "t", "channel_id": CHANNEL_ID}
            )
        )
    assert result["ok"] is False
    assert len(recorders["send_message_async"].calls) == 1  # never retried
    events = [
        json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()
    ]
    assert [event["outcome"] for event in events] == ["attempt", "failure"]


@pytest.mark.asyncio
async def test_dry_run_never_calls_writes(tmp_path) -> None:
    server, recorders = make_server(Profile.READWRITE, tmp_path, dry_run=True)
    tools = {t.name: t for t in await server.list_tools() if t.name.startswith("raw_")}
    assert "DRY-RUN SIMULATION" in tools["raw_delete_message"].description
    assert tools["raw_delete_message"].annotations.read_only_hint is True

    async with mcp_session(server) as session:
        result = structured(
            await session.call_tool("raw_delete_message", {"message_id": MESSAGE_ID})
        )
    assert result["dry_run"] is True
    assert result["planned"]["http_method"] == "DELETE"
    assert result["planned"]["destructive"] is True
    # Zero write endpoints were touched.
    for op in RAW_WRITE_OPERATIONS:
        assert recorders[op.method].calls == [], op.tool_name


@pytest.mark.asyncio
async def test_curated_profile_has_no_raw_tools(tmp_path) -> None:
    server, _ = make_server(Profile.CURATED)
    tools = [t.name for t in await server.list_tools()]
    assert not any(name.startswith("raw_") for name in tools)
