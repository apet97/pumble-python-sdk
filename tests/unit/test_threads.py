"""P13: compact thread context and safer thread reply."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from pumble_keys.extensions.threads import (
    ThreadContextMessage,
    get_thread_context,
    reply_to_thread,
)

CHANNEL_ID = "0" * 20 + "0001"
ROOT_ID = "0" * 20 + "0002"


def message(message_id: str, author: str, *, reply_count: int | None = None):
    info = None if reply_count is None else SimpleNamespace(reply_count=reply_count)
    return SimpleNamespace(
        id=message_id,
        channel_id=CHANNEL_ID,
        author=author,
        text=f"text-{message_id}",
        timestamp=datetime(2026, 8, 15, tzinfo=UTC),
        timestamp_milli=1_786_752_000_000,
        thread_root_info=info,
    )


class Fetchers:
    def __init__(self, root, replies, *, delay: float = 0.0) -> None:
        self.root = root
        self.replies = replies
        self.delay = delay
        self.calls: list[tuple[str, dict]] = []
        self.events: list[str] = []

    async def fetch_message(self, request: dict):
        self.calls.append(("fetch_message", request))
        self.events.append("root-start")
        if self.delay:
            await asyncio.sleep(self.delay)
        self.events.append("root-end")
        return self.root

    async def fetch_thread_replies(self, request: dict):
        self.calls.append(("fetch_thread_replies", request))
        self.events.append("replies-start")
        if self.delay:
            await asyncio.sleep(self.delay)
        self.events.append("replies-end")
        return SimpleNamespace(result=self.replies)


@pytest.mark.asyncio
async def test_compact_context_and_requests() -> None:
    root = message(ROOT_ID, "author-root", reply_count=7)
    replies = [message("r1", "author-a"), message("r2", "author-b")]
    fetchers = Fetchers(root, replies)

    context = await get_thread_context(
        fetch_message=fetchers.fetch_message,
        fetch_thread_replies=fetchers.fetch_thread_replies,
        channel_id=CHANNEL_ID,
        message_id=ROOT_ID,
    )
    assert context.root == ThreadContextMessage(
        id=ROOT_ID,
        channel_id=CHANNEL_ID,
        author="author-root",
        text=f"text-{ROOT_ID}",
        timestamp="2026-08-15T00:00:00Z",
        timestamp_milli=1_786_752_000_000,
    )
    assert [reply.id for reply in context.replies] == ["r1", "r2"]
    assert context.reply_count == 7  # server count wins
    assert dict(fetchers.calls)["fetch_thread_replies"] == {
        "channel_id": CHANNEL_ID,
        "root_message_id": ROOT_ID,
    }


@pytest.mark.asyncio
async def test_root_and_replies_fetch_concurrently() -> None:
    fetchers = Fetchers(message(ROOT_ID, "a"), [], delay=0.01)
    await get_thread_context(
        fetch_message=fetchers.fetch_message,
        fetch_thread_replies=fetchers.fetch_thread_replies,
        channel_id=CHANNEL_ID,
        message_id=ROOT_ID,
    )
    # Both fetches started before either finished.
    assert fetchers.events[:2] == ["root-start", "replies-start"]


@pytest.mark.asyncio
async def test_reply_limit_slices_and_is_sent() -> None:
    replies = [message(f"r{i}", f"author-{i}") for i in range(5)]
    fetchers = Fetchers(message(ROOT_ID, "a"), replies)
    context = await get_thread_context(
        fetch_message=fetchers.fetch_message,
        fetch_thread_replies=fetchers.fetch_thread_replies,
        channel_id=CHANNEL_ID,
        message_id=ROOT_ID,
        reply_limit=2,
    )
    assert len(context.replies) == 2
    assert dict(fetchers.calls)["fetch_thread_replies"]["limit"] == 2


@pytest.mark.asyncio
async def test_reply_count_falls_back_to_reply_length() -> None:
    replies = [message("r1", "a")]
    fetchers = Fetchers(message(ROOT_ID, "a"), replies)
    context = await get_thread_context(
        fetch_message=fetchers.fetch_message,
        fetch_thread_replies=fetchers.fetch_thread_replies,
        channel_id=CHANNEL_ID,
        message_id=ROOT_ID,
    )
    assert context.reply_count == 1


@pytest.mark.asyncio
async def test_participants_first_seen_order_dedupe_blank_skipped() -> None:
    root = message(ROOT_ID, "author-a")
    replies = [
        message("r1", "author-b"),
        message("r2", "author-a"),  # duplicate
        message("r3", "  "),  # blank skipped
        message("r4", "author-c"),
    ]
    fetchers = Fetchers(root, replies)
    context = await get_thread_context(
        fetch_message=fetchers.fetch_message,
        fetch_thread_replies=fetchers.fetch_thread_replies,
        channel_id=CHANNEL_ID,
        message_id=ROOT_ID,
    )
    assert context.participants == ("author-a", "author-b", "author-c")


@pytest.mark.asyncio
async def test_blank_inputs_rejected_before_any_fetch() -> None:
    fetchers = Fetchers(message(ROOT_ID, "a"), [])
    for kwargs in (
        {"channel_id": " ", "message_id": ROOT_ID},
        {"channel_id": CHANNEL_ID, "message_id": ""},
    ):
        with pytest.raises(ValueError, match="is required"):
            await get_thread_context(
                fetch_message=fetchers.fetch_message,
                fetch_thread_replies=fetchers.fetch_thread_replies,
                **kwargs,
            )
    assert fetchers.calls == []


@pytest.mark.asyncio
async def test_invalid_reply_limit_rejected() -> None:
    fetchers = Fetchers(message(ROOT_ID, "a"), [])
    for bad in (0, -1, float("nan"), True):
        with pytest.raises(ValueError, match="reply_limit"):
            await get_thread_context(
                fetch_message=fetchers.fetch_message,
                fetch_thread_replies=fetchers.fetch_thread_replies,
                channel_id=CHANNEL_ID,
                message_id=ROOT_ID,
                reply_limit=bad,
            )
    assert fetchers.calls == []


@pytest.mark.asyncio
async def test_api_failure_propagates() -> None:
    async def failing(_request: dict):
        raise ConnectionError("boom")

    async def replies_ok(_request: dict):
        return SimpleNamespace(result=[])

    with pytest.raises(ConnectionError):
        await get_thread_context(
            fetch_message=failing,
            fetch_thread_replies=replies_ok,
            channel_id=CHANNEL_ID,
            message_id=ROOT_ID,
        )


@pytest.mark.asyncio
async def test_reply_to_thread_sends_once_with_extras() -> None:
    sent: list[dict] = []

    async def send_reply(request: dict):
        sent.append(request)
        return SimpleNamespace(id="new-reply")

    result = await reply_to_thread(
        send_reply=send_reply,
        channel_id=CHANNEL_ID,
        message_id=ROOT_ID,
        text="hello",
        reply_to_channel=True,
    )
    assert result.id == "new-reply"
    assert sent == [
        {
            "channel_id": CHANNEL_ID,
            "message_id": ROOT_ID,
            "text": "hello",
            "reply_to_channel": True,
        }
    ]


@pytest.mark.asyncio
async def test_reply_to_thread_rejects_blank_fields() -> None:
    sent: list[dict] = []

    async def send_reply(request: dict):
        sent.append(request)

    for kwargs in (
        {"channel_id": "", "message_id": ROOT_ID, "text": "x"},
        {"channel_id": CHANNEL_ID, "message_id": " ", "text": "x"},
        {"channel_id": CHANNEL_ID, "message_id": ROOT_ID, "text": "   "},
    ):
        with pytest.raises(ValueError, match="is required"):
            await reply_to_thread(send_reply=send_reply, **kwargs)
    assert sent == []
