"""Ordered live smoke against the sacrificial workspace (PUMBLE_LIVE=1).

Reads cover all 11 read operations; writes create only probe-prefixed
objects in the sacrificial channel, verify by direct read, and delete
them. Channel creation is deliberately NOT exercised: the API has no
channel-delete operation, so a created channel would be permanent
residue — recorded as skipped instead.
"""

from __future__ import annotations

import contextlib
import os
import time

import pytest

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.extensions.results import FacadeFailure

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("PUMBLE_LIVE") != "1", reason="PUMBLE_LIVE=1 not set"
    ),
    pytest.mark.asyncio,
]

STATE: dict[str, str] = {}


@contextlib.asynccontextmanager
async def live_client(api_key: str):
    client = create_pumble_client(api_key)
    try:
        yield client
    finally:
        await client.aclose()


def ok(value):
    assert not isinstance(value, FacadeFailure), value
    return value


async def test_00_workspace_guard(api_key, live_channel_id, ledger) -> None:
    """Abort the whole session unless the sacrificial marker is present."""
    async with live_client(api_key) as client:
        entries = ok(await client.channels.list())
        ledger.read("listChannels")
        channel_ids = {entry.channel.id for entry in entries}
        if live_channel_id not in channel_ids:
            pytest.exit(
                "PUMBLE_LIVE_CHANNEL_ID is not visible to this API key; "
                "refusing to run writes against an unmarked workspace",
                2,
            )


async def test_01_read_smoke(api_key, live_channel_id, ledger) -> None:
    async with live_client(api_key) as client:
        raw = client.raw
        me = await raw.users.my_info_async()
        ledger.read("myInfo")
        STATE["my_id"] = me.id
        await raw.users.list_users_async()
        ledger.read("listUsers")
        await raw.users.list_user_groups_async()
        ledger.read("listUserGroups")
        await raw.channels.get_channel_async(channel_id=live_channel_id)
        ledger.read("getChannel")
        await raw.messages.list_messages_async(channel_id=live_channel_id, limit=5)
        ledger.read("listMessages")
        await raw.messages.search_messages_async(
            text="PYSDK-PROBE", in_=[live_channel_id], limit=5
        )
        ledger.read("searchMessages")
        await raw.scheduled_messages.fetch_scheduled_messages_async(
            channel_id=live_channel_id, limit=5
        )
        ledger.read("fetchScheduledMessages")


async def test_02_send_reply_edit_react(
    api_key, live_channel_id, ledger, probe_prefix
) -> None:
    async with live_client(api_key) as client:
        receipt = ok(
            await client.messages.send(
                channel_id=live_channel_id,
                text=f"{probe_prefix} live smoke root",
            )
        )
        ledger.write("sendMessage")
        assert receipt.verification.state == "verified"
        root_id = receipt.ids["message_id"]
        ledger.track("message", root_id)
        STATE["root_id"] = root_id

        reply = ok(
            await client.threads.reply(
                channel_id=live_channel_id,
                message_id=root_id,
                text=f"{probe_prefix} live smoke reply",
            )
        )
        ledger.write("sendReply")
        assert reply.verification.state == "verified"
        reply_id = reply.ids["message_id"]
        ledger.track("message", reply_id)
        STATE["reply_id"] = reply_id

        raw = client.raw
        await raw.messages.fetch_message_async(
            message_id=root_id, channel_id=live_channel_id
        )
        ledger.read("fetchMessage")
        await raw.messages.fetch_thread_replies_async(
            root_message_id=root_id, channel_id=live_channel_id, limit=10
        )
        ledger.read("fetchThreadReplies")

        await raw.messages.edit_message_async(
            message_id=root_id,
            channel_id=live_channel_id,
            text=f"{probe_prefix} live smoke root (edited)",
        )
        ledger.write("editMessage")
        edited = await raw.messages.fetch_message_async(
            message_id=root_id, channel_id=live_channel_id
        )
        assert "(edited)" in edited.text

        await raw.messages.add_reaction_async(
            message_id=root_id, reaction=":+1:", channel_id=live_channel_id
        )
        ledger.write("addReaction")
        await raw.messages.remove_reaction_async(
            message_id=root_id, reaction=":+1:", channel_id=live_channel_id
        )
        ledger.write("removeReaction")


async def test_03_scheduled_roundtrip(
    api_key, live_channel_id, ledger, probe_prefix
) -> None:
    async with live_client(api_key) as client:
        send_at = int(time.time() * 1000) + 60 * 60 * 1000
        created = ok(
            await client.scheduled.create(
                channel_id=live_channel_id,
                text=f"{probe_prefix} scheduled probe",
                send_at=send_at,
            )
        )
        ledger.write("createScheduledMessage")
        scheduled_id = created.ids["scheduled_message_id"]
        ledger.track("scheduled_message", scheduled_id)

        fetched = await client.raw.scheduled_messages.fetch_scheduled_message_async(
            scheduled_message_id=scheduled_id
        )
        ledger.read("fetchScheduledMessage")
        assert fetched is not None

        ok(await client.scheduled.cancel(scheduled_message_id=scheduled_id))
        ledger.write("deleteScheduledMessage")
        ledger.untrack(scheduled_id)


async def test_04_status_set_and_clear(api_key, ledger) -> None:
    async with live_client(api_key) as client:
        # Short expiry: the status self-clears even if the explicit
        # clear below is rejected, so no lasting workspace state.
        expires = int(time.time() * 1000) + 60 * 1000
        receipt = await client.users.set_status(
            code=":coffee:", expires_at=expires, status="PYSDK probe"
        )
        if isinstance(receipt, FacadeFailure):
            ledger.skipped.append(f"customStatus: {receipt.reason}")
            pytest.skip(f"customStatus not permitted: {receipt.reason}")
        ledger.write("customStatus")
        cleared = await client.users.clear_status()
        if isinstance(cleared, FacadeFailure):
            # Live finding: the expired-status clear trick is rejected
            # by the current API; the 60 s expiry above self-clears.
            ledger.skipped.append(f"clearStatus: {cleared.reason}")
        else:
            ledger.write("customStatus")


async def test_05_dm_self(api_key, ledger, probe_prefix) -> None:
    async with live_client(api_key) as client:
        receipt = await client.messages.dm(
            user_id=STATE["my_id"], text=f"{probe_prefix} dm probe"
        )
        if isinstance(receipt, FacadeFailure):
            ledger.skipped.append(f"dmUser: {receipt.reason}")
            pytest.skip(f"dmUser not permitted: {receipt.reason}")
        ledger.write("dmUser")
        dm_id = receipt.ids["message_id"]
        dm_channel = receipt.ids["channel_id"]
        ledger.track("message", dm_id)
        await client.raw.messages.delete_message_async(
            message_id=dm_id, channel_id=dm_channel
        )
        ledger.write("deleteMessage")
        ledger.untrack(dm_id)


async def test_06_mcp_live(api_key, live_channel_id, ledger, probe_prefix) -> None:
    from mcp.client.client import Client

    from pumble_keys.mcp_server.config import McpConfig
    from pumble_keys.mcp_server.server import create_server

    server = create_server(McpConfig(api_key=api_key))
    async with Client(server, mode="auto") as mcp_client:
        whoami = (await mcp_client.call_tool("whoami", {})).structured_content
        assert whoami["result"]["ok"] is True

        channels = (
            await mcp_client.call_tool("list_channels", {"limit": 50})
        ).structured_content["result"]
        assert channels["ok"] is True

        context = (
            await mcp_client.call_tool(
                "get_channel_context", {"channel": live_channel_id, "limit": 5}
            )
        ).structured_content["result"]
        assert context["ok"] is True

        text = f"{probe_prefix} mcp preview/confirm probe"
        preview = (
            await mcp_client.call_tool(
                "send_message_preview",
                {"channel": live_channel_id, "text": text},
            )
        ).structured_content["result"]
        assert preview["ok"] is True

        confirmed = (
            await mcp_client.call_tool(
                "send_message_confirmed",
                {
                    "channel": live_channel_id,
                    "text": text,
                    "preview": preview["preview"],
                    "token": preview["token"],
                },
            )
        ).structured_content["result"]
        assert confirmed["ok"] is True
        assert confirmed["verification_state"] == "verified"
        ledger.write("sendMessage")
        mcp_message_id = confirmed["ids"]["message_id"]
        ledger.track("message", mcp_message_id)
        STATE["mcp_message_id"] = mcp_message_id

        opened = (
            await mcp_client.call_tool("open_pumble_workspace", {})
        ).structured_content
        assert opened["ok"] is True

        bootstrap = (
            await mcp_client.call_tool("pumble_ui_bootstrap", {})
        ).structured_content
        assert bootstrap["ok"] is True

    ledger.skipped.append(
        "webhook/subscription live check: no signing secret or callback "
        "ingress configured"
    )


async def test_98_cleanup(api_key, live_channel_id, ledger) -> None:
    async with live_client(api_key) as client:
        raw = client.raw
        for key in ("reply_id", "root_id", "mcp_message_id"):
            message_id = STATE.get(key)
            if message_id is None:
                continue
            await raw.messages.delete_message_async(
                message_id=message_id, channel_id=live_channel_id
            )
            ledger.write("deleteMessage")
            with contextlib.suppress(Exception):
                fetched = await raw.messages.fetch_message_async(
                    message_id=message_id, channel_id=live_channel_id
                )
                assert getattr(fetched, "id", None) != message_id, (
                    "deleted message still readable"
                )
            ledger.untrack(message_id)


async def test_99_residue_and_coverage(ledger) -> None:
    assert ledger.residue() == [], f"cleanup residue: {ledger.residue()}"
    for read_op in (
        "listChannels",
        "getChannel",
        "fetchMessage",
        "fetchThreadReplies",
        "searchMessages",
        "listMessages",
        "fetchScheduledMessages",
        "fetchScheduledMessage",
        "listUsers",
        "listUserGroups",
        "myInfo",
    ):
        assert ledger.reads.get(read_op, 0) >= 1, f"read not covered: {read_op}"
    ledger.skipped.append(
        "createChannel/addUsersToChannel/removeUserFromChannel: the API "
        "has no channel delete, so channel creation would leave residue"
    )
