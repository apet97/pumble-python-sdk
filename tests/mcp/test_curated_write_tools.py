"""P28: curated write tools — preview/confirm binding through a real session."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server
from tests.mcp.harness import mcp_session, structured

CHANNEL_ID = "0" * 20 + "0001"
OTHER_CHANNEL_ID = "0" * 20 + "0002"
MESSAGE_ID = "0" * 20 + "0003"
KEY = "test-key-not-real"
SECRET = "confirmation-secret-not-real"

WRITE_TOOLS = [
    "send_message_preview",
    "send_message_confirmed",
    "reply_to_thread_preview",
    "reply_to_thread_confirmed",
]


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
                        id=OTHER_CHANNEL_ID,
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


def make_server(*, replay_size=1024, **overrides):
    from pumble_keys.extensions.client import create_pumble_client

    raw = make_raw(**overrides)
    config = McpConfig(
        api_key=KEY,
        confirmation_secret=SECRET,
        confirmation_replay_size=replay_size,
    )
    server = create_server(
        config, client_factory=lambda _c: create_pumble_client(raw=raw)
    )
    return server, raw._recorders


@pytest.mark.asyncio
async def test_manifest_and_annotations() -> None:
    server, _ = make_server()
    tools = {tool.name: tool for tool in await server.list_tools()}
    for name in WRITE_TOOLS:
        assert name in tools
    for name in ("send_message_preview", "reply_to_thread_preview"):
        assert tools[name].annotations.read_only_hint is True
    for name in ("send_message_confirmed", "reply_to_thread_confirmed"):
        annotations = tools[name].annotations
        assert annotations.read_only_hint is False
        assert annotations.idempotent_hint is False
        assert annotations.destructive_hint is False
        assert annotations.open_world_hint is True


async def do_preview(session, channel="engineering", text="hello world"):
    result = await session.call_tool(
        "send_message_preview", {"channel": channel, "text": text}
    )
    return structured(result)


@pytest.mark.asyncio
async def test_preview_shape_redaction_and_no_write() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        payload = await do_preview(session, text="api-key: sekret123 hello")
    assert payload["ok"] is True
    plan = payload["preview"]
    assert plan["target_id"] == CHANNEL_ID
    assert plan["risk_level"] == "medium"
    assert "sekret123" not in plan["text_excerpt"]
    assert plan["expires_at_ms"] > plan["issued_at_ms"]
    assert payload["token"].startswith("pumble-write-plan-v1.")
    assert recorders["send_message"].calls == []  # preview never writes
    assert "Nothing was sent" in payload["summary"]


@pytest.mark.asyncio
async def test_confirmed_happy_path_one_write_direct_read() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        payload = await do_preview(session)
        confirmed = await session.call_tool(
            "send_message_confirmed",
            {
                "channel": "engineering",
                "text": "hello world",
                "preview": payload["preview"],
                "token": payload["token"],
            },
        )
    result = structured(confirmed)
    assert result["ok"] is True
    assert result["ids"]["message_id"] == MESSAGE_ID
    assert result["verification_state"] == "verified"
    assert len(recorders["send_message"].calls) == 1  # exactly one attempt
    assert len(recorders["fetch_message"].calls) == 1  # direct-read proof


@pytest.mark.asyncio
async def test_tampered_text_target_preview_and_token_rejected() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        payload = await do_preview(session)
        base = {
            "channel": "engineering",
            "text": "hello world",
            "preview": payload["preview"],
            "token": payload["token"],
        }

        text_changed = structured(
            await session.call_tool(
                "send_message_confirmed", {**base, "text": "changed text"}
            )
        )
        assert text_changed["reason"] == "confirmation_request_mismatch"

        target_changed = structured(
            await session.call_tool(
                "send_message_confirmed", {**base, "channel": "random"}
            )
        )
        assert target_changed["reason"] == "confirmation_target_mismatch"

        tampered_preview = {
            **payload["preview"],
            "risk_level": "low",
        }
        preview_tampered = structured(
            await session.call_tool(
                "send_message_confirmed",
                {**base, "preview": tampered_preview},
            )
        )
        assert preview_tampered["reason"] == "confirmation_invalid_token"

        token_tampered = structured(
            await session.call_tool(
                "send_message_confirmed",
                {**base, "token": payload["token"][:-2] + "zz"},
            )
        )
        assert token_tampered["reason"] == "confirmation_invalid_token"

    assert recorders["send_message"].calls == []  # nothing ever ran


@pytest.mark.asyncio
async def test_expired_preview_rejected() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        payload = await do_preview(session)
        expired_preview = dict(payload["preview"])
        # An edited expiry breaks the signature; a genuinely old preview
        # is simulated below by validating directly.
        from pumble_keys.extensions.write_plan import (
            WritePreview,
            create_confirmation_token,
            validate_confirmation,
        )

        plan = WritePreview.model_validate(payload["preview"])
        stale = plan.model_copy(update={"expires_at_ms": plan.issued_at_ms - 1})
        stale_token = create_confirmation_token(stale, SECRET.encode())
        reason = validate_confirmation(
            preview=stale,
            token=stale_token,
            secret=SECRET.encode(),
            now_ms=plan.issued_at_ms,
            workspace_id=stale.workspace_id,
            request={"any": "thing"},
            text="hello world",
        )
        assert reason == "expired"
        assert expired_preview["expires_at_ms"] > 0
    assert recorders["send_message"].calls == []


@pytest.mark.asyncio
async def test_duplicate_token_rejected_by_replay_guard() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        payload = await do_preview(session)
        args = {
            "channel": "engineering",
            "text": "hello world",
            "preview": payload["preview"],
            "token": payload["token"],
        }
        first = structured(await session.call_tool("send_message_confirmed", args))
        assert first["ok"] is True
        second = structured(await session.call_tool("send_message_confirmed", args))
        assert second["reason"] == "confirmation_replayed"
    assert len(recorders["send_message"].calls) == 1  # never twice


@pytest.mark.asyncio
async def test_wrong_secret_instance_rejects() -> None:
    # Two servers with different secrets: a token from one fails on the
    # other (workspace fingerprints match; the signature does not).
    server_a, _ = make_server()
    from pumble_keys.extensions.client import create_pumble_client

    raw_b = make_raw()
    server_b = create_server(
        McpConfig(api_key=KEY, confirmation_secret="different-secret"),
        client_factory=lambda _c: create_pumble_client(raw=raw_b),
    )
    async with mcp_session(server_a) as session_a:
        payload = await do_preview(session_a)
    async with mcp_session(server_b) as session_b:
        rejected = structured(
            await session_b.call_tool(
                "send_message_confirmed",
                {
                    "channel": "engineering",
                    "text": "hello world",
                    "preview": payload["preview"],
                    "token": payload["token"],
                },
            )
        )
    assert rejected["reason"] == "confirmation_invalid_token"
    assert raw_b._recorders["send_message"].calls == []


@pytest.mark.asyncio
async def test_shared_secret_verifies_across_instances() -> None:
    # Stateless HTTP contract: any instance with the shared secret can
    # verify a preview issued by another instance.
    server_a, _ = make_server()
    server_b, recorders_b = make_server()
    async with mcp_session(server_a) as session_a:
        payload = await do_preview(session_a)
    async with mcp_session(server_b) as session_b:
        confirmed = structured(
            await session_b.call_tool(
                "send_message_confirmed",
                {
                    "channel": "engineering",
                    "text": "hello world",
                    "preview": payload["preview"],
                    "token": payload["token"],
                },
            )
        )
    assert confirmed["ok"] is True
    assert len(recorders_b["send_message"].calls) == 1


@pytest.mark.asyncio
async def test_reply_preview_and_confirm_roundtrip() -> None:
    server, recorders = make_server()
    async with mcp_session(server) as session:
        payload = structured(
            await session.call_tool(
                "reply_to_thread_preview",
                {
                    "channel": "engineering",
                    "message_id": MESSAGE_ID,
                    "text": "re",
                },
            )
        )
        assert payload["ok"] is True
        confirmed = structured(
            await session.call_tool(
                "reply_to_thread_confirmed",
                {
                    "channel": "engineering",
                    "message_id": MESSAGE_ID,
                    "text": "re",
                    "preview": payload["preview"],
                    "token": payload["token"],
                },
            )
        )
    assert confirmed["ok"] is True
    assert confirmed["ids"]["root_message_id"] == MESSAGE_ID
    assert len(recorders["send_reply"].calls) == 1

    # Changing the root id after preview invalidates the request binding.
    async with mcp_session(server) as session:
        payload = structured(
            await session.call_tool(
                "reply_to_thread_preview",
                {
                    "channel": "engineering",
                    "message_id": MESSAGE_ID,
                    "text": "re",
                },
            )
        )
        mismatch = structured(
            await session.call_tool(
                "reply_to_thread_confirmed",
                {
                    "channel": "engineering",
                    "message_id": "0" * 20 + "0009",
                    "text": "re",
                    "preview": payload["preview"],
                    "token": payload["token"],
                },
            )
        )
    assert mismatch["reason"] == "confirmation_request_mismatch"
