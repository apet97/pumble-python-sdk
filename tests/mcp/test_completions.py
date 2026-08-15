"""P30: completions — bounded, deterministic, empty-cache safe."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp_types import (
    PromptReference,
    ResourceTemplateReference,
)

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server
from tests.mcp.harness import mcp_session

KEY = "test-key-not-real"


class Recorder:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    async def __call__(self, **kwargs):
        if self.error is not None:
            raise self.error
        return self.value


def make_raw(channel_count=30):
    return SimpleNamespace(
        channels=SimpleNamespace(
            list_channels_async=Recorder(
                [
                    SimpleNamespace(
                        channel=SimpleNamespace(
                            id=f"{i:024d}",
                            name=f"chan-{i:02d}",
                            channel_type="PUBLIC",
                        )
                    )
                    for i in range(channel_count)
                ]
            )
        ),
        users=SimpleNamespace(
            list_users_async=Recorder(
                [
                    SimpleNamespace(
                        id="0" * 24,
                        name="User One",
                        email="user-1@example.invalid",
                    )
                ]
            )
        ),
    )


def make_server(**overrides):
    from pumble_keys.extensions.client import create_pumble_client

    raw = make_raw(**overrides)
    return create_server(
        McpConfig(api_key=KEY),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )


async def complete(session, ref, name: str, value: str):
    result = await session.complete(ref, argument={"name": name, "value": value})
    return result.completion


@pytest.mark.asyncio
async def test_event_name_completion_sorted_and_filtered() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        all_events = await complete(
            session,
            ResourceTemplateReference(
                type="ref/resource", uri="pumble://events/{name}"
            ),
            "name",
            "",
        )
        assert all_events.values[0] == "APP_UNAUTHORIZED"  # sorted
        assert len(all_events.values) == 7

        filtered = await complete(
            session,
            ResourceTemplateReference(
                type="ref/resource", uri="pumble://events/{name}"
            ),
            "name",
            "MESSAGE",
        )
        assert set(filtered.values) == {"NEW_MESSAGE", "UPDATED_MESSAGE"}


@pytest.mark.asyncio
async def test_knowledge_path_completion() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        completion = await complete(
            session,
            ResourceTemplateReference(
                type="ref/resource", uri="pumble://knowledge/{+path}"
            ),
            "path",
            "guides",
        )
    assert "guides/safe-writes.md" in completion.values
    assert all(value.endswith((".md", ".txt")) for value in completion.values)


@pytest.mark.asyncio
async def test_channel_completion_bounded_and_ordered() -> None:
    server = make_server(channel_count=30)
    async with mcp_session(server) as session:
        completion = await complete(
            session,
            PromptReference(type="ref/prompt", name="summarize_thread"),
            "channel",
            "chan",
        )
    assert len(completion.values) == 20  # bounded
    assert completion.values[0] == "chan-00"  # API list order
    assert completion.has_more is True
    assert completion.total == 30


@pytest.mark.asyncio
async def test_user_completion_names_and_emails_no_message_text() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        completion = await complete(
            session,
            PromptReference(type="ref/prompt", name="summarize_thread"),
            "user",
            "user",
        )
    assert "User One" in completion.values
    assert "user-1@example.invalid" in completion.values
    assert KEY not in " ".join(completion.values)


@pytest.mark.asyncio
async def test_unknown_argument_returns_empty() -> None:
    server = make_server()
    async with mcp_session(server) as session:
        completion = await complete(
            session,
            PromptReference(type="ref/prompt", name="summarize_thread"),
            "mystery",
            "x",
        )
    assert completion.values == []


@pytest.mark.asyncio
async def test_listing_failure_yields_empty_not_error() -> None:
    from pumble_keys.extensions.client import create_pumble_client

    raw = make_raw()
    raw.channels.list_channels_async = Recorder(error=ConnectionError("down"))
    server = create_server(
        McpConfig(api_key=KEY),
        client_factory=lambda _c: create_pumble_client(raw=raw),
    )
    async with mcp_session(server) as session:
        completion = await complete(
            session,
            PromptReference(type="ref/prompt", name="summarize_thread"),
            "channel",
            "chan",
        )
    assert completion.values == []
