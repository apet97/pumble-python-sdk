"""P06: schema fidelity — 32 schemas, casing, nullability, epoch-ms, datetimes.

Fixtures are sanitized: IDs use the reference sanitizer's placeholder
alphabet (24-char lowercase hex), emails use `@example.invalid`, and all
text is synthetic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent

# Ledger schema name -> importable generated symbol(s).
# `maintainOpenAPIOrder` keeps names close to the document; the pinned
# generator renames two and inlines the two thread-info schemas per parent.
SCHEMA_SYMBOLS: dict[str, list[str]] = {
    "LegacyError": ["errors.LegacyErrorData"],
    "StructuredError": ["errors.StructuredErrorData"],
    "Error": ["errors.ErrorUnion"],
    "MessageRef": ["models.MessageRef"],
    "ChannelRef": ["models.ChannelRef"],
    "ScheduledMessageRef": ["models.ScheduledMessageRef"],
    "ChannelType": ["models.ChannelType"],
    "UserStatus": ["models.UserStatus"],
    "UserRole": ["models.UserRole"],
    "PostingPermissionsGroup": ["models.PostingPermissionsGroup"],
    "ListMessagesStrategy": ["models.ListMessagesStrategy"],
    "SearchStrategy": ["models.SearchStrategy"],
    "RecurrenceType": ["models.RecurrenceType"],
    "Avatar": ["models.Avatar"],
    "CustomStatusObject": ["models.CustomStatus"],
    "PostingPermissions": ["models.PostingPermissions"],
    "Recurrence": ["models.Recurrence"],
    "RichTextElement": ["models.RichTextElement"],
    "MessageBlock": ["models.MessageBlock"],
    "Reaction": ["models.Reaction"],
    "ThreadReplyInfo": [
        "models.MessageThreadReplyInfo",
        "models.SearchHitThreadReplyInfo",
    ],
    "ThreadRootInfo": [
        "models.MessageThreadRootInfo",
        "models.SearchHitThreadRootInfo",
    ],
    "User": ["models.User"],
    "UserGroup": ["models.UserGroup"],
    "Channel": ["models.Channel"],
    "ChannelListEntry": ["models.ChannelListEntry"],
    "Message": ["models.Message"],
    "MessageList": ["models.MessageList"],
    "ScheduledMessage": ["models.ScheduledMessage"],
    "ScheduledMessageList": ["models.ScheduledMessageList"],
    "SearchHit": ["models.SearchHit"],
    "SearchMessagesResult": ["models.SearchMessagesResult"],
}

CHANNEL_ID = "0" * 20 + "0001"
WORKSPACE_ID = "0" * 20 + "0002"
USER_ID = "0" * 20 + "0003"
MESSAGE_ID = "0" * 20 + "0004"

MESSAGE_FIXTURE = {
    "id": MESSAGE_ID,
    "channelId": CHANNEL_ID,
    "workspaceId": WORKSPACE_ID,
    "author": USER_ID,
    "text": "example message text",
    "timestamp": "2026-08-15T00:00:00Z",
    "timestampMilli": 1786838400000,
    "authorAppId": None,
    "blocks": None,
    "reactions": [{"code": ":+1:", "user": USER_ID}],
    "threadRootInfo": {
        "replyCount": 2,
        "lastReplyTimestampMilli": 1786838460000,
    },
    "deleted": False,
    "edited": False,
    "subtype": "",
}


def _resolve(symbol: str):
    from pumble_keys import models
    from pumble_keys.models import errors

    module_name, attr = symbol.split(".")
    return getattr({"models": models, "errors": errors}[module_name], attr)


def test_ledger_has_32_schemas_and_all_resolve() -> None:
    ledger = json.loads((REPO / "contracts" / "schemas.json").read_text())
    assert len(ledger) == 32
    assert sorted(ledger) == sorted(SCHEMA_SYMBOLS)
    for name in ledger:
        for symbol in SCHEMA_SYMBOLS[name]:
            assert _resolve(symbol) is not None, f"{name}: {symbol}"


def test_message_field_casing_round_trips() -> None:
    from pumble_keys import models

    message = models.Message.model_validate(MESSAGE_FIXTURE)
    assert message.channel_id == CHANNEL_ID
    assert message.workspace_id == WORKSPACE_ID

    dumped = message.model_dump(mode="json", by_alias=True)
    for key in (
        "channelId",
        "workspaceId",
        "timestampMilli",
        "threadRootInfo",
    ):
        assert key in dumped, key
    assert "channel_id" not in dumped
    assert dumped["threadRootInfo"]["replyCount"] == 2


def test_epoch_millisecond_fields_stay_integers() -> None:
    from pumble_keys import models

    message = models.Message.model_validate(MESSAGE_FIXTURE)
    assert message.timestamp_milli == 1786838400000
    assert isinstance(message.timestamp_milli, int)

    dumped = message.model_dump(mode="json", by_alias=True)
    assert dumped["timestampMilli"] == 1786838400000
    assert isinstance(dumped["timestampMilli"], int)


def test_datetime_fields_are_timezone_aware_and_round_trip() -> None:
    from pumble_keys import models

    message = models.Message.model_validate(MESSAGE_FIXTURE)
    assert isinstance(message.timestamp, datetime)
    assert message.timestamp.tzinfo is not None
    assert message.timestamp == datetime(2026, 8, 15, tzinfo=UTC)

    dumped = message.model_dump(mode="json", by_alias=True)
    assert datetime.fromisoformat(dumped["timestamp"]) == message.timestamp


def test_nullable_versus_optional_distinction() -> None:
    from pumble_keys import models

    message = models.Message.model_validate(MESSAGE_FIXTURE)
    # Nullable field explicitly null in the payload survives as None.
    assert message.author_app_id is None
    dumped = message.model_dump(mode="json", by_alias=True)
    assert dumped["authorAppId"] is None

    # Optional field absent from the payload stays absent when dumped.
    without_optional = {k: v for k, v in MESSAGE_FIXTURE.items() if k != "authorAppId"}
    dumped_absent = models.Message.model_validate(without_optional).model_dump(
        mode="json", by_alias=True
    )
    assert "authorAppId" not in dumped_absent


def test_required_fields_are_enforced() -> None:
    import pydantic

    from pumble_keys import models

    incomplete = {k: v for k, v in MESSAGE_FIXTURE.items() if k != "channelId"}
    with pytest.raises(pydantic.ValidationError):
        models.Message.model_validate(incomplete)


def test_forward_compatible_enum_accepts_unknown_value() -> None:
    from pumble_keys import models

    channel = models.Channel.model_validate(
        {
            "id": CHANNEL_ID,
            "workspaceId": WORKSPACE_ID,
            "name": "example-channel",
            "channelType": "FUTURE_UNKNOWN_TYPE",
            "isMember": True,
            "isArchived": False,
        }
    )
    assert str(channel.channel_type) == "FUTURE_UNKNOWN_TYPE"
