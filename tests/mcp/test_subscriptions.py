"""P34: Pumble webhooks bridged to modern MCP subscriptions (cues only)."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import anyio
import httpx
import pytest
from mcp.client.client import Client
from mcp.server.subscriptions import InMemorySubscriptionBus, ResourceUpdated
from mcp.server.transport_security import TransportSecuritySettings

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server
from pumble_keys.mcp_server.subscriptions import (
    CHANNELS_URI,
    ME_URI,
    channel_uri,
    publish_cues,
    resource_cues,
    thread_uri,
)
from pumble_keys.mcp_server.webhook_bridge import (
    WEBHOOK_PATH,
    create_webhook_bridge,
    mount_pumble_webhooks,
)
from pumble_keys.pumble_app.events import normalize_webhook_event
from pumble_keys.pumble_app.webhooks import sign_pumble_request

KEY = "test-key-not-real"
SIGNING_SECRET = "signing-secret-not-real"
HOST = "good.example.invalid"
CHANNEL_ID = "0" * 20 + "0001"
OTHER_CHANNEL_ID = "0" * 20 + "0002"
THREAD_ROOT_ID = "0" * 20 + "0003"


class Recorder:
    def __init__(self, value=None) -> None:
        self.value = value
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.value


def make_raw():
    return SimpleNamespace(
        channels=SimpleNamespace(
            list_channels_async=Recorder(
                [
                    SimpleNamespace(
                        channel=SimpleNamespace(
                            id=CHANNEL_ID,
                            name="engineering",
                            channel_type="PUBLIC",
                        )
                    )
                ]
            )
        ),
        users=SimpleNamespace(list_users_async=Recorder([])),
    )


def make_server(bus):
    return create_server(
        McpConfig(api_key=KEY),
        client_factory=lambda _c: create_pumble_client(raw=make_raw()),
        subscriptions=bus,
    )


def event_of(payload: dict):
    event = normalize_webhook_event(payload)
    assert event is not None
    return event


def message_payload(
    channel_id: str = CHANNEL_ID, thread_root: str | None = None
) -> dict:
    body = {"ty": "NEW_MESSAGE", "cId": channel_id, "mId": "m-1", "tx": "hi"}
    if thread_root is not None:
        body["trId"] = thread_root
    return body


async def next_event(subscription):
    with anyio.fail_after(2):
        return await subscription.__anext__()


class TestResourceCues:
    def test_message_updates_channel_and_thread(self) -> None:
        assert resource_cues(event_of(message_payload())) == (channel_uri(CHANNEL_ID),)
        assert resource_cues(event_of(message_payload(thread_root=THREAD_ROOT_ID))) == (
            channel_uri(CHANNEL_ID),
            thread_uri(CHANNEL_ID, THREAD_ROOT_ID),
        )

    def test_reaction_updates_channel_and_thread(self) -> None:
        event = event_of(
            {
                "ty": "REACTION_ADDED",
                "cId": CHANNEL_ID,
                "mId": THREAD_ROOT_ID,
                "rc": ":+1:",
            }
        )
        assert resource_cues(event) == (
            channel_uri(CHANNEL_ID),
            thread_uri(CHANNEL_ID, THREAD_ROOT_ID),
        )

    def test_channel_created_updates_catalog(self) -> None:
        event = event_of(
            {"ty": "CHANNEL_CREATED", "cId": OTHER_CHANNEL_ID, "cN": "new"}
        )
        assert resource_cues(event) == (CHANNELS_URI,)

    @pytest.mark.parametrize("kind", ["APP_UNINSTALLED", "APP_UNAUTHORIZED"])
    def test_auth_events_update_identity_and_catalog(self, kind: str) -> None:
        event = event_of({"eventType": kind, "body": {"id": "inst-1"}})
        assert resource_cues(event) == (ME_URI, CHANNELS_URI)

    def test_membership_event_has_no_cues(self) -> None:
        event = event_of({"ty": "WORKSPACE_USER_JOINED", "uId": "u-1"})
        assert resource_cues(event) == ()

    def test_cues_never_carry_message_content(self) -> None:
        payload = message_payload(thread_root=THREAD_ROOT_ID)
        payload["tx"] = "the secret launch text"
        for uri in resource_cues(event_of(payload)):
            assert "secret" not in uri
            assert "launch" not in uri


class TestBusDelivery:
    @pytest.mark.asyncio
    async def test_listen_ack_and_exact_filter(self) -> None:
        bus = InMemorySubscriptionBus()
        server = make_server(bus)
        async with (
            Client(server, mode="auto") as client,
            client.listen(
                resource_subscriptions=[channel_uri(CHANNEL_ID)]
            ) as subscription,
        ):
            assert subscription.honored.resource_subscriptions == [
                channel_uri(CHANNEL_ID)
            ]
            # A cue for another channel is filtered by the honored URI set.
            await publish_cues(
                bus, event_of(message_payload(channel_id=OTHER_CHANNEL_ID))
            )
            await publish_cues(bus, event_of(message_payload()))
            event = await next_event(subscription)
            assert event == ResourceUpdated(uri=channel_uri(CHANNEL_ID))

    @pytest.mark.asyncio
    async def test_duplicate_cues_collapse_for_an_unread_client(self) -> None:
        bus = InMemorySubscriptionBus()
        server = make_server(bus)
        async with (
            Client(server, mode="auto") as client,
            client.listen(
                resource_subscriptions=[
                    channel_uri(CHANNEL_ID),
                    CHANNELS_URI,
                ]
            ) as subscription,
        ):
            for _ in range(3):
                await publish_cues(bus, event_of(message_payload()))
            await publish_cues(
                bus,
                event_of({"ty": "CHANNEL_CREATED", "cId": OTHER_CHANNEL_ID}),
            )
            # Let the client ingest the whole burst before reading so
            # the identical cues are pending together (collapse is a
            # dedup of the unread backlog, not of the wire).
            await anyio.sleep(0.2)
            first = await next_event(subscription)
            second = await next_event(subscription)
            # Three identical cues collapse to one pending event; the
            # catalog cue proves the stream advanced past them.
            assert first == ResourceUpdated(uri=channel_uri(CHANNEL_ID))
            assert second == ResourceUpdated(uri=CHANNELS_URI)

    @pytest.mark.asyncio
    async def test_raising_listener_is_isolated(self) -> None:
        bus = InMemorySubscriptionBus()

        def bad_listener(_event) -> None:
            raise RuntimeError("boom")

        seen: list = []
        bus.subscribe(bad_listener)
        bus.subscribe(seen.append)
        published = await publish_cues(bus, event_of(message_payload()))
        assert published == (channel_uri(CHANNEL_ID),)
        assert seen == [ResourceUpdated(uri=channel_uri(CHANNEL_ID))]


def signed_headers(raw_body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    return {
        "x-pumble-request-timestamp": timestamp,
        "x-pumble-request-signature": sign_pumble_request(
            signing_secret=SIGNING_SECRET,
            timestamp=timestamp,
            raw_body=raw_body,
        ),
    }


def http_app(server, bridge):
    app = server.streamable_http_app(
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[HOST],
            allowed_origins=[f"http://{HOST}"],
        ),
    )
    return mount_pumble_webhooks(app, bridge)


class TestWebhookBridge:
    @pytest.mark.asyncio
    async def test_webhook_to_event_to_refetch(self) -> None:
        bus = InMemorySubscriptionBus()
        server = make_server(bus)
        bridge = create_webhook_bridge(signing_secret=SIGNING_SECRET, publisher=bus)
        app = http_app(server, bridge)
        raw_body = json.dumps(message_payload(thread_root=THREAD_ROOT_ID)).encode()
        # The HTTP manager's lifespan exit clears the stashed resource
        # state, so the whole flow runs inside its context.
        async with (
            server.session_manager.run(),
            Client(server, mode="auto") as client,
            client.listen(
                resource_subscriptions=[channel_uri(CHANNEL_ID)]
            ) as subscription,
        ):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as http:
                response = await http.post(
                    WEBHOOK_PATH,
                    content=raw_body,
                    headers=signed_headers(raw_body),
                )
            assert response.status_code == 204
            event = await next_event(subscription)
            assert isinstance(event, ResourceUpdated)
            # The cue carries the URI only; the client refetches.
            refetched = await client.read_resource("pumble://channels")
            payload = json.loads(refetched.contents[0].text)
            assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_bad_signature_is_401_and_publishes_nothing(self) -> None:
        bus = InMemorySubscriptionBus()
        server = make_server(bus)
        seen: list = []
        bus.subscribe(seen.append)
        bridge = create_webhook_bridge(signing_secret=SIGNING_SECRET, publisher=bus)
        app = http_app(server, bridge)
        raw_body = json.dumps(message_payload()).encode()
        headers = signed_headers(raw_body)
        headers["x-pumble-request-signature"] = "0" * 64
        async with server.session_manager.run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as http:
                response = await http.post(
                    WEBHOOK_PATH, content=raw_body, headers=headers
                )
        assert response.status_code == 401
        assert seen == []

    @pytest.mark.asyncio
    async def test_no_unsolicited_events_and_no_bodies_on_stream(self) -> None:
        bus = InMemorySubscriptionBus()
        server = make_server(bus)
        bridge = create_webhook_bridge(signing_secret=SIGNING_SECRET, publisher=bus)
        app = http_app(server, bridge)
        payload = message_payload(thread_root=THREAD_ROOT_ID)
        payload["tx"] = "SECRET-MESSAGE-TEXT"
        raw_body = json.dumps(payload).encode()
        # The listen filter names only the channel URI: the thread cue is
        # withheld, and nothing at all arrives without a subscription.
        async with (
            server.session_manager.run(),
            Client(server, mode="auto") as client,
            client.listen(
                resource_subscriptions=[channel_uri(CHANNEL_ID)]
            ) as subscription,
        ):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=f"http://{HOST}"
            ) as http:
                response = await http.post(
                    WEBHOOK_PATH,
                    content=raw_body,
                    headers=signed_headers(raw_body),
                )
            assert response.status_code == 204
            event = await next_event(subscription)
            assert isinstance(event, ResourceUpdated)
            assert "SECRET-MESSAGE-TEXT" not in event.uri
            with pytest.raises(TimeoutError):
                await next_event(subscription)
