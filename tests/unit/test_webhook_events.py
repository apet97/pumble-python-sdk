"""P19: typed webhook events — seven types, both wire forms, forward compat."""

from __future__ import annotations

import json

import pytest

from pumble_keys.pumble_app.events import (
    KNOWN_EVENT_TYPES,
    NotificationAppUnauthorized,
    NotificationAppUninstalled,
    NotificationChannel,
    NotificationMessage,
    NotificationReaction,
    NotificationWorkspaceUserJoined,
    normalize_webhook_event,
)

WID = "0" * 20 + "0001"
CID = "0" * 20 + "0002"
MID = "0" * 20 + "0003"
UID = "0" * 20 + "0004"

FIXTURES = {
    "NEW_MESSAGE": {
        "ty": "NEW_MESSAGE",
        "wId": WID,
        "aId": UID,
        "cId": CID,
        "mId": MID,
        "tx": "[redacted]",
        "eph": False,
    },
    "UPDATED_MESSAGE": {
        "ty": "UPDATED_MESSAGE",
        "wId": WID,
        "cId": CID,
        "mId": MID,
        "tx": "[redacted]",
        "e": True,
    },
    "REACTION_ADDED": {
        "ty": "REACTION_ADDED",
        "wId": WID,
        "cId": CID,
        "mId": MID,
        "uId": UID,
        "rc": ":+1:",
    },
    "CHANNEL_CREATED": {
        "ty": "CHANNEL_CREATED",
        "wId": WID,
        "cId": CID,
        "cN": "example-channel",
        "cT": "PUBLIC",
        "cU": [UID],
    },
    "APP_UNINSTALLED": {
        "ty": "APP_UNINSTALLED",
        "id": MID,
        "app": CID,
        "workspace": WID,
        "installedBy": UID,
        "uninstalledAt": "2026-08-15T00:00:00Z",
    },
    "APP_UNAUTHORIZED": {
        "ty": "APP_UNAUTHORIZED",
        "id": MID,
        "app": CID,
        "workspace": WID,
        "workspaceUser": UID,
        "grantedScopes": ["messages:read"],
        "accessGranted": False,
    },
    "WORKSPACE_USER_JOINED": {
        "ty": "WORKSPACE_USER_JOINED",
        "wId": WID,
        "uId": UID,
        "uN": "User 1",
        "uE": "user-1@example.invalid",
        "ro": "MEMBER",
    },
}

BODY_TYPES = {
    "NEW_MESSAGE": NotificationMessage,
    "UPDATED_MESSAGE": NotificationMessage,
    "REACTION_ADDED": NotificationReaction,
    "CHANNEL_CREATED": NotificationChannel,
    "APP_UNINSTALLED": NotificationAppUninstalled,
    "APP_UNAUTHORIZED": NotificationAppUnauthorized,
    "WORKSPACE_USER_JOINED": NotificationWorkspaceUserJoined,
}


@pytest.mark.parametrize("event_type", sorted(KNOWN_EVENT_TYPES))
def test_compact_form_per_event(event_type: str) -> None:
    payload = FIXTURES[event_type]
    event = normalize_webhook_event(payload)
    assert event is not None
    assert event.type == event_type
    assert isinstance(event.body, BODY_TYPES[event_type])
    assert event.raw is payload


@pytest.mark.parametrize("event_type", sorted(KNOWN_EVENT_TYPES))
def test_envelope_form_per_event(event_type: str) -> None:
    payload = {
        "eventType": event_type,
        "workspaceId": WID,
        "workspaceUserIds": [UID],
        "body": FIXTURES[event_type],
    }
    event = normalize_webhook_event(payload)
    assert event is not None
    assert event.type == event_type
    assert event.workspace_id == WID
    assert event.workspace_user_ids == (UID,)


def test_envelope_with_json_string_body() -> None:
    payload = {
        "eventType": "NEW_MESSAGE",
        "body": json.dumps(FIXTURES["NEW_MESSAGE"]),
    }
    event = normalize_webhook_event(payload)
    assert event is not None
    assert event.body.m_id == MID
    assert event.workspace_id == WID  # recovered from the body's wId


def test_compact_field_names_are_the_wire_names() -> None:
    event = normalize_webhook_event(FIXTURES["NEW_MESSAGE"])
    body = event.body
    assert body.a_id == UID
    assert body.c_id == CID
    assert body.tx == "[redacted]"
    assert body.m_id == MID
    assert body.eph is False


def test_unknown_fields_are_preserved() -> None:
    payload = {**FIXTURES["NEW_MESSAGE"], "futureField": {"nested": 1}}
    event = normalize_webhook_event(payload)
    assert event.body.model_extra["futureField"] == {"nested": 1}
    dumped = event.body.model_dump(by_alias=True)
    assert dumped["futureField"] == {"nested": 1}


def test_unknown_event_type_returns_none() -> None:
    assert normalize_webhook_event({"ty": "SOMETHING_ELSE"}) is None
    assert normalize_webhook_event({"eventType": "SOMETHING_ELSE"}) is None


@pytest.mark.parametrize(
    "payload",
    [None, "string", 42, [], {"no": "discriminator"}],
)
def test_malformed_payloads_return_none(payload) -> None:
    assert normalize_webhook_event(payload) is None


def test_envelope_with_non_dict_body_returns_none() -> None:
    assert normalize_webhook_event({"eventType": "NEW_MESSAGE", "body": [1, 2]}) is None


def test_envelope_with_malformed_json_body_raises() -> None:
    with pytest.raises(ValueError):
        normalize_webhook_event({"eventType": "NEW_MESSAGE", "body": "{not json"})


def test_raw_is_excluded_from_serialization() -> None:
    event = normalize_webhook_event(FIXTURES["NEW_MESSAGE"])
    dumped = event.model_dump()
    assert "raw" not in dumped
    assert "raw" not in repr(event)


def test_invalid_workspace_user_ids_are_dropped() -> None:
    payload = {
        "eventType": "NEW_MESSAGE",
        "body": FIXTURES["NEW_MESSAGE"],
        "workspaceUserIds": [1, 2],
    }
    event = normalize_webhook_event(payload)
    assert event.workspace_user_ids is None
