"""P33: MRTR interactive send/reply tools on the curated-interactive profile."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp.client.client import Client
from mcp_types import ElicitResult

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.profiles import Profile
from pumble_keys.mcp_server.server import create_server
from pumble_keys.mcp_server.tools.dependencies import confirmation_question

CHANNEL_ID = "0" * 20 + "0001"
MESSAGE_ID = "0" * 20 + "0003"
KEY = "test-key-not-real"

INTERACTIVE_TOOLS = ["send_message_interactive", "reply_to_thread_interactive"]


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


def make_raw(**overrides):
    r = {
        "list_channels": Recorder(
            [
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id=CHANNEL_ID,
                        name="engineering",
                        channel_type="PUBLIC",
                    )
                ),
                SimpleNamespace(
                    channel=SimpleNamespace(
                        id="0" * 20 + "0002",
                        name="random",
                        channel_type="PUBLIC",
                    )
                ),
            ]
        ),
        "send_message": Recorder(SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)),
        "send_reply": Recorder(SimpleNamespace(id="reply-1", channel_id=CHANNEL_ID)),
        "fetch_message": Recorder(SimpleNamespace(id=MESSAGE_ID)),
    }
    r.update(overrides)
    return SimpleNamespace(
        channels=SimpleNamespace(list_channels_async=r["list_channels"]),
        users=SimpleNamespace(list_users_async=Recorder([])),
        messages=SimpleNamespace(
            send_message_async=r["send_message"],
            send_reply_async=r["send_reply"],
            fetch_message_async=r["fetch_message"],
        ),
        _recorders=r,
    )


def make_server(profile: Profile = Profile.CURATED_INTERACTIVE, **overrides):
    raw = make_raw(**overrides)
    server = create_server(
        McpConfig(api_key=KEY, profile=profile),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )
    return server, raw._recorders


def answering(action: str, *, send: bool = True, questions: list[str] | None = None):
    async def callback(_context, params) -> ElicitResult:
        if questions is not None:
            questions.append(params.message)
        content = {"send": send} if action == "accept" else None
        return ElicitResult(action=action, content=content)

    return callback


def structured(result):
    payload = result.structured_content
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload


@pytest.mark.asyncio
async def test_manifest_schema_and_annotations() -> None:
    server, _ = make_server()
    tools = {tool.name: tool for tool in await server.list_tools()}
    for name in INTERACTIVE_TOOLS:
        annotations = tools[name].annotations
        assert annotations.read_only_hint is False
        assert annotations.idempotent_hint is False
        assert annotations.destructive_hint is False
    # Resolve-injected parameters and the context never reach the model.
    send_schema = tools["send_message_interactive"].input_schema
    reply_schema = tools["reply_to_thread_interactive"].input_schema
    assert sorted(send_schema["properties"]) == ["channel", "text"]
    assert sorted(send_schema["required"]) == ["channel", "text"]
    assert sorted(reply_schema["properties"]) == ["channel", "message_id", "text"]


@pytest.mark.asyncio
async def test_curated_profile_does_not_expose_interactive_tools() -> None:
    server, _ = make_server(profile=Profile.CURATED)
    names = {tool.name for tool in await server.list_tools()}
    assert not names.intersection(INTERACTIVE_TOOLS)


@pytest.mark.asyncio
async def test_accept_sends_exactly_once_with_direct_read_receipt() -> None:
    server, recorders = make_server()
    async with Client(
        server, mode="auto", elicitation_callback=answering("accept")
    ) as client:
        result = await client.call_tool(
            "send_message_interactive",
            {"channel": "engineering", "text": "hello world"},
        )
    payload = structured(result)
    assert payload["ids"]["message_id"] == MESSAGE_ID
    assert payload["verification_state"] == "verified"
    assert len(recorders["send_message"].calls) == 1
    # Verification reads the message back by ID — no search involved.
    assert len(recorders["fetch_message"].calls) == 1


@pytest.mark.asyncio
async def test_question_is_deterministic_and_matches_the_contract() -> None:
    server, _ = make_server()
    questions: list[str] = []
    async with Client(
        server,
        mode="auto",
        elicitation_callback=answering("accept", questions=questions),
    ) as client:
        for _ in range(2):
            await client.call_tool(
                "send_message_interactive",
                {"channel": "engineering", "text": "hello world"},
            )
    assert len(questions) == 2
    assert questions[0] == questions[1]
    assert questions[0] == confirmation_question(
        action="Send message",
        target_label="#engineering",
        text="hello world",
    )


@pytest.mark.asyncio
async def test_question_tracks_the_resolved_target() -> None:
    server, _ = make_server()
    questions: list[str] = []
    async with Client(
        server,
        mode="auto",
        elicitation_callback=answering("accept", questions=questions),
    ) as client:
        for channel in ("engineering", "random"):
            await client.call_tool(
                "send_message_interactive",
                {"channel": channel, "text": "hello world"},
            )
    assert "#engineering" in questions[0]
    assert "#random" in questions[1]
    assert questions[0] != questions[1]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "send", "reason"),
    [
        ("decline", True, "confirmation_declined"),
        ("cancel", True, "confirmation_cancelled"),
        ("accept", False, "confirmation_accepted"),
    ],
)
async def test_not_confirmed_writes_nothing(action, send, reason) -> None:
    server, recorders = make_server()
    async with Client(
        server,
        mode="auto",
        elicitation_callback=answering(action, send=send),
    ) as client:
        result = await client.call_tool(
            "send_message_interactive",
            {"channel": "engineering", "text": "hello world"},
        )
    payload = structured(result)
    assert payload["ok"] is False
    assert payload["reason"] == reason
    assert recorders["send_message"].calls == []


@pytest.mark.asyncio
async def test_resolution_failure_skips_the_question_and_the_write() -> None:
    server, recorders = make_server()
    questions: list[str] = []
    async with Client(
        server,
        mode="auto",
        elicitation_callback=answering("accept", questions=questions),
    ) as client:
        result = await client.call_tool(
            "send_message_interactive",
            {"channel": "no-such-channel", "text": "hello world"},
        )
    payload = structured(result)
    assert payload["ok"] is False
    assert questions == []
    assert recorders["send_message"].calls == []


@pytest.mark.asyncio
async def test_api_failure_after_accept_is_a_structured_value() -> None:
    server, recorders = make_server(send_message=Recorder(error=RuntimeError("boom")))
    async with Client(
        server, mode="auto", elicitation_callback=answering("accept")
    ) as client:
        result = await client.call_tool(
            "send_message_interactive",
            {"channel": "engineering", "text": "hello world"},
        )
    payload = structured(result)
    assert payload["ok"] is False
    assert len(recorders["send_message"].calls) == 1


@pytest.mark.asyncio
async def test_reply_accept_replies_exactly_once() -> None:
    server, recorders = make_server()
    questions: list[str] = []
    async with Client(
        server,
        mode="auto",
        elicitation_callback=answering("accept", questions=questions),
    ) as client:
        result = await client.call_tool(
            "reply_to_thread_interactive",
            {
                "channel": "engineering",
                "message_id": MESSAGE_ID,
                "text": "in thread",
            },
        )
    payload = structured(result)
    assert payload["ids"]["message_id"] == "reply-1"
    assert payload["ids"]["root_message_id"] == MESSAGE_ID
    assert len(recorders["send_reply"].calls) == 1
    assert f"(thread root {MESSAGE_ID})" in questions[0]
