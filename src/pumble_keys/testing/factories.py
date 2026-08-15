"""Factories for generated models with sanitized deterministic defaults."""

from __future__ import annotations

from typing import Any

from pumble_keys import models

CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0002"
MESSAGE_ID = "0" * 20 + "0003"
WORKSPACE_ID = "0" * 20 + "0004"


def make_user(**overrides: Any) -> models.User:
    payload = {
        "id": USER_ID,
        "email": "user-1@example.invalid",
        "name": "User 1",
        "role": "MEMBER",
        "status": "ACTIVE",
        "workspaceId": WORKSPACE_ID,
        **overrides,
    }
    return models.User.model_validate(payload)


def make_channel(**overrides: Any) -> models.Channel:
    payload = {
        "id": CHANNEL_ID,
        "workspaceId": WORKSPACE_ID,
        "name": "example-channel",
        "channelType": "PUBLIC",
        "isMember": True,
        "isArchived": False,
        **overrides,
    }
    return models.Channel.model_validate(payload)


def make_channel_list_entry(**overrides: Any) -> models.ChannelListEntry:
    return models.ChannelListEntry.model_validate(
        {"channel": make_channel(**overrides).model_dump(by_alias=True)}
    )


def make_message(**overrides: Any) -> models.Message:
    payload = {
        "id": MESSAGE_ID,
        "channelId": CHANNEL_ID,
        "workspaceId": WORKSPACE_ID,
        "author": USER_ID,
        "text": "[redacted]",
        "timestamp": "2026-08-15T00:00:00Z",
        "timestampMilli": 1_786_752_000_000,
        **overrides,
    }
    return models.Message.model_validate(payload)


def make_message_ref(**overrides: Any) -> models.MessageRef:
    payload = {"id": MESSAGE_ID, "channelId": CHANNEL_ID, **overrides}
    return models.MessageRef.model_validate(payload)
