"""Pumble change cues for the 2026 subscription model.

Events are cues only: each notification names a resource URI and the
client refetches that resource. Message bodies, names, and any other
content never ride the subscription stream — the URIs carry IDs only.

Delivery seam: ``EventPublisher`` is the minimal protocol the webhook
bridge publishes through. The SDK's ``SubscriptionBus`` satisfies it;
pass one bus to both ``create_server(..., subscriptions=bus)`` and the
bridge so webhook cues reach open ``subscriptions/listen`` streams. The
in-process ``InMemorySubscriptionBus`` fans out to THIS process only:
with several server processes each has its own bus, so multi-process
deployments must supply a shared ``SubscriptionBus`` adapter (for
example Redis pub/sub). This package does not provide one.

Slow subscribers are bounded by the SDK's ``ListenHandler``: each listen
stream buffers up to 1024 events and a stream whose client stopped
reading is ended at the cap — the client re-listens and refetches
(there is no replay). A raising bus listener is isolated by the bus.
"""

from __future__ import annotations

from typing import Protocol

from mcp.server.subscriptions import ResourceUpdated, ServerEvent

from pumble_keys.pumble_app.events import PumbleWebhookEvent

ME_URI = "pumble://me"
CHANNELS_URI = "pumble://channels"

_MESSAGE_EVENTS = frozenset({"NEW_MESSAGE", "UPDATED_MESSAGE"})
_AUTH_EVENTS = frozenset({"APP_UNINSTALLED", "APP_UNAUTHORIZED"})


class EventPublisher(Protocol):
    """The publish half of a subscription bus."""

    async def publish(self, event: ServerEvent) -> None: ...


def channel_uri(channel_id: str) -> str:
    return f"pumble://channel/{channel_id}"


def thread_uri(channel_id: str, message_id: str) -> str:
    return f"pumble://thread/{channel_id}/{message_id}"


def resource_cues(event: PumbleWebhookEvent) -> tuple[str, ...]:
    """The resource URIs a Pumble webhook event invalidates (IDs only).

    - message events: the channel context, plus the thread context when
      the message is a thread reply;
    - reactions: the channel context, plus the thread the message roots;
    - channel created: the channel catalog;
    - uninstall/unauthorize: the identity and the channel catalog;
    - workspace membership: no served resource changes — no cue.
    """
    body = event.body
    cues: list[str] = []
    if event.type in _MESSAGE_EVENTS or event.type == "REACTION_ADDED":
        cid = getattr(body, "c_id", None)
        if cid:
            cues.append(channel_uri(cid))
            root = (
                getattr(body, "m_id", None)
                if event.type == "REACTION_ADDED"
                else getattr(body, "tr_id", None)
            )
            if root:
                cues.append(thread_uri(cid, root))
    elif event.type == "CHANNEL_CREATED":
        cues.append(CHANNELS_URI)
    elif event.type in _AUTH_EVENTS:
        cues.extend((ME_URI, CHANNELS_URI))
    return tuple(dict.fromkeys(cues))


async def publish_cues(
    publisher: EventPublisher, event: PumbleWebhookEvent
) -> tuple[str, ...]:
    """Publish one ``ResourceUpdated`` per cued URI; returns the URIs."""
    cues = resource_cues(event)
    for uri in cues:
        await publisher.publish(ResourceUpdated(uri=uri))
    return cues
