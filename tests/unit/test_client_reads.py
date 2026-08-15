"""P14: curated client façade — namespaces, read mapping, safety wiring."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from pumble_keys.extensions.client import (
    PumbleClient,
    create_pumble_client,
)
from pumble_keys.extensions.results import FacadeFailure

CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0002"


class Recorder:
    """Fake generated namespace method: records kwargs, returns a value."""

    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.value


def fake_channel(name="engineering"):
    return SimpleNamespace(id=CHANNEL_ID, name=name, channel_type="PUBLIC")


def fake_user(name="Example", email="user-1@example.invalid"):
    return SimpleNamespace(id=USER_ID, name=name, email=email)


def make_raw(**overrides):
    defaults = {
        "my_info": Recorder(fake_user()),
        "list_users": Recorder([fake_user()]),
        "list_user_groups": Recorder([]),
        "list_channels": Recorder([SimpleNamespace(channel=fake_channel())]),
        "get_channel": Recorder(SimpleNamespace(channel=fake_channel())),
        "fetch_message": Recorder(SimpleNamespace(id="m1")),
        "fetch_thread_replies": Recorder(SimpleNamespace(result=[])),
        "search_messages": Recorder(
            SimpleNamespace(result=SimpleNamespace(content=[], has_more=False))
        ),
        "list_messages": Recorder(SimpleNamespace(result=SimpleNamespace(messages=[]))),
        "fetch_scheduled_messages": Recorder(
            SimpleNamespace(result=SimpleNamespace(scheduled_messages=[]))
        ),
        "fetch_scheduled_message": Recorder(SimpleNamespace(id="s1")),
    }
    defaults.update(overrides)
    r = defaults
    return SimpleNamespace(
        users=SimpleNamespace(
            my_info_async=r["my_info"],
            list_users_async=r["list_users"],
            list_user_groups_async=r["list_user_groups"],
        ),
        channels=SimpleNamespace(
            list_channels_async=r["list_channels"],
            get_channel_async=r["get_channel"],
        ),
        messages=SimpleNamespace(
            fetch_message_async=r["fetch_message"],
            fetch_thread_replies_async=r["fetch_thread_replies"],
            search_messages_async=r["search_messages"],
            list_messages_async=r["list_messages"],
        ),
        scheduled_messages=SimpleNamespace(
            fetch_scheduled_messages_async=r["fetch_scheduled_messages"],
            fetch_scheduled_message_async=r["fetch_scheduled_message"],
        ),
        _recorders=r,
    )


def make_client(**overrides) -> PumbleClient:
    return create_pumble_client(raw=make_raw(**overrides))


def test_namespace_manifest_snapshot() -> None:
    client = make_client()
    manifest = {
        name: sorted(
            member
            for member in dir(getattr(client, name))
            if not member.startswith("_")
        )
        for name in (
            "identity",
            "channels",
            "users",
            "messages",
            "search",
            "threads",
            "scheduled",
            "cache",
        )
    }
    assert manifest == {
        "identity": ["me"],
        "channels": ["find", "find_by_name", "get", "list", "resolve"],
        "users": ["find", "find_by_email", "list", "list_groups", "resolve"],
        "messages": ["all", "get", "list"],
        "search": ["all", "page"],
        "threads": ["get_context", "list_replies"],
        "scheduled": ["get", "list"],
        "cache": ["clear", "info", "metrics", "refresh"],
    }
    assert hasattr(client, "raw")
    assert callable(client.preflight)


def test_facade_is_async_only() -> None:
    client = make_client()
    for namespace in ("identity", "channels", "users", "messages"):
        obj = getattr(client, namespace)
        for name in dir(obj):
            if name.startswith("_") or name == "all":
                continue
            assert inspect.iscoroutinefunction(getattr(obj, name)), (
                f"{namespace}.{name}"
            )


@pytest.mark.asyncio
async def test_each_read_uses_expected_generated_callable() -> None:
    raw = make_raw()
    client = create_pumble_client(raw=raw)
    r = raw._recorders

    await client.identity.me(timeout_ms=99)
    assert r["my_info"].calls == [{"timeout_ms": 99}]

    await client.channels.list(server_url="http://localhost:1")
    assert r["list_channels"].calls == [{"server_url": "http://localhost:1"}]

    channel = await client.channels.get(channel_id=CHANNEL_ID)
    assert r["get_channel"].calls == [{"channel_id": CHANNEL_ID}]
    assert channel.name == "engineering"  # unwrapped from the response

    await client.users.list()
    await client.users.list_groups()
    assert r["list_users"].calls and r["list_user_groups"].calls

    await client.messages.get(message_id="m1", channel_id=CHANNEL_ID)
    assert r["fetch_message"].calls == [{"message_id": "m1", "channel_id": CHANNEL_ID}]

    page = await client.messages.list(channel_id=CHANNEL_ID, limit=5)
    assert r["list_messages"].calls == [{"channel_id": CHANNEL_ID, "limit": 5}]
    assert page.messages == []  # normalized page wrapper

    result = await client.search.page(text="alert", limit=10)
    assert r["search_messages"].calls == [{"text": "alert", "limit": 10}]
    assert result.has_more is False  # normalized

    replies = await client.threads.list_replies(root_message_id="m1")
    assert r["fetch_thread_replies"].calls == [{"root_message_id": "m1"}]
    assert replies == []

    scheduled_page = await client.scheduled.list(channel_id=CHANNEL_ID)
    assert r["fetch_scheduled_messages"].calls == [{"channel_id": CHANNEL_ID}]
    assert scheduled_page.scheduled_messages == []

    await client.scheduled.get(scheduled_message_id="s1")
    assert r["fetch_scheduled_message"].calls == [{"scheduled_message_id": "s1"}]


@pytest.mark.asyncio
async def test_read_error_becomes_structured_failure() -> None:
    client = make_client(my_info=Recorder(error=ConnectionError("down")))
    result = await client.identity.me()
    assert isinstance(result, FacadeFailure)
    assert result.reason == "transport_error"
    assert result.summary == "Pumble API operation myInfo failed."


@pytest.mark.asyncio
async def test_find_channel_success_and_failure_shapes() -> None:
    client = make_client()
    found = await client.channels.find("engineering")
    assert found.ok is True
    assert found.summary == "Found channel #engineering."
    assert found.ids == {"channel_id": CHANNEL_ID}
    assert found.channel.channel_type == "PUBLIC"

    missing = await client.channels.find("ghost")
    assert isinstance(missing, FacadeFailure)
    assert missing.reason == "not_found"


@pytest.mark.asyncio
async def test_find_user_success_shape() -> None:
    client = make_client()
    found = await client.users.find("user-1@example.invalid")
    assert found.ok is True
    assert found.summary == "Found user Example."
    assert found.ids == {"user_id": USER_ID}


@pytest.mark.asyncio
async def test_preflight_uses_facade_resolvers() -> None:
    client = make_client()
    result = await client.preflight(channel="engineering", user="ghost")
    assert result.ok is False
    assert result.channel.ok is True
    assert isinstance(result.user, FacadeFailure)


@pytest.mark.asyncio
async def test_resolver_cache_disabled_by_default() -> None:
    raw = make_raw()
    client = create_pumble_client(raw=raw)
    await client.channels.resolve("engineering")
    await client.channels.resolve("engineering")
    assert len(raw._recorders["list_channels"].calls) == 2
    assert client.cache.metrics() == {"hits": 0, "misses": 0, "evictions": 0}


@pytest.mark.asyncio
async def test_resolver_cache_enabled_caches_listings() -> None:
    raw = make_raw()
    client = create_pumble_client(raw=raw, resolver_cache=True)
    await client.channels.resolve("engineering")
    await client.channels.resolve("engineering")
    assert len(raw._recorders["list_channels"].calls) == 1
    assert client.cache.metrics()["hits"] == 1
    client.cache.clear()
    assert client.cache.info() == {"channels": "empty", "users": "empty"}


def test_blank_api_key_rejected() -> None:
    for blank in (None, "", "   "):
        with pytest.raises(ValueError, match="api_key must not be blank"):
            create_pumble_client(blank)


def test_http_base_url_rejected_outside_localhost() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        create_pumble_client("k", server_url="http://example.com")
    # Localhost HTTP is allowed for tests; construction succeeds.
    client = create_pumble_client("k", server_url="http://localhost:9999")
    assert client.raw is not None


def test_generated_client_is_built_without_global_retry_config() -> None:
    """Regression for the P04 finding: a client-wide retry_config would
    silently retry generated writes."""
    from pumble_keys.types import UNSET

    client = create_pumble_client("test-key-not-real")
    assert client.raw.sdk_configuration.retry_config is UNSET


def test_api_key_not_stored_on_facade() -> None:
    client = create_pumble_client("test-key-not-real")
    for value in vars(client).values():
        assert value != "test-key-not-real"
    assert "test-key-not-real" not in repr(vars(client))
