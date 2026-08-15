"""Checked-in manifest of the raw operation adapters.

Exactly 11 reads and 15 writes, in OpenAPI document order. A contract
test asserts this manifest matches ``contracts/operations.json``.
Destructive flags mark delete/cancel/remove operations.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RawParam:
    name: str
    annotation: Any
    required: bool = False


@dataclass(frozen=True)
class RawOperation:
    operation_id: str
    tool_name: str
    namespace: str
    method: str
    http: str
    path: str
    kind: str  # "read" | "write"
    params: tuple[RawParam, ...] = ()
    destructive: bool = False
    request_wrapped: bool = False

    def signature(self, ctx_annotation: Any) -> inspect.Signature:
        parameters = [
            inspect.Parameter(
                "ctx",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=ctx_annotation,
            )
        ]
        for param in self.params:
            parameters.append(
                inspect.Parameter(
                    param.name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=(
                        param.annotation if param.required else param.annotation | None
                    ),
                    default=(inspect.Parameter.empty if param.required else None),
                )
            )
        return inspect.Signature(parameters, return_annotation=dict[str, Any])


def _p(name: str, annotation: Any = str, *, required: bool = False) -> RawParam:
    return RawParam(name=name, annotation=annotation, required=required)


RAW_READ_OPERATIONS: tuple[RawOperation, ...] = (
    RawOperation(
        "listChannels",
        "raw_list_channels",
        "channels",
        "list_channels_async",
        "GET",
        "/listChannels",
        "read",
    ),
    RawOperation(
        "getChannel",
        "raw_get_channel",
        "channels",
        "get_channel_async",
        "GET",
        "/getChannel",
        "read",
        (_p("channel_id"), _p("channel")),
    ),
    RawOperation(
        "fetchMessage",
        "raw_fetch_message",
        "messages",
        "fetch_message_async",
        "GET",
        "/fetchMessage",
        "read",
        (_p("message_id", required=True), _p("channel_id"), _p("channel")),
    ),
    RawOperation(
        "fetchThreadReplies",
        "raw_fetch_thread_replies",
        "messages",
        "fetch_thread_replies_async",
        "GET",
        "/fetchThreadReplies",
        "read",
        (
            _p("root_message_id", required=True),
            _p("channel_id"),
            _p("channel"),
            _p("cursor"),
            _p("limit", int),
        ),
    ),
    RawOperation(
        "searchMessages",
        "raw_search_messages",
        "messages",
        "search_messages_async",
        "POST",
        "/searchMessages",
        "read",
        (
            _p("text"),
            _p("from_", list[str]),
            _p("in_", list[str]),
            _p("limit", int),
            _p("strategy"),
            _p("before_ts", int),
            _p("after_ts", int),
        ),
    ),
    RawOperation(
        "listMessages",
        "raw_list_messages",
        "messages",
        "list_messages_async",
        "GET",
        "/listMessages",
        "read",
        (
            _p("channel_id"),
            _p("channel"),
            _p("cursor"),
            _p("limit", int),
            _p("strategy"),
        ),
    ),
    RawOperation(
        "fetchScheduledMessages",
        "raw_fetch_scheduled_messages",
        "scheduled_messages",
        "fetch_scheduled_messages_async",
        "GET",
        "/fetchScheduledMessages",
        "read",
        (_p("channel_id"), _p("cursor"), _p("limit", int)),
    ),
    RawOperation(
        "fetchScheduledMessage",
        "raw_fetch_scheduled_message",
        "scheduled_messages",
        "fetch_scheduled_message_async",
        "GET",
        "/fetchScheduledMessage",
        "read",
        (_p("scheduled_message_id", required=True),),
    ),
    RawOperation(
        "listUsers",
        "raw_list_users",
        "users",
        "list_users_async",
        "GET",
        "/listUsers",
        "read",
    ),
    RawOperation(
        "listUserGroups",
        "raw_list_user_groups",
        "users",
        "list_user_groups_async",
        "GET",
        "/listUserGroups",
        "read",
    ),
    RawOperation(
        "myInfo",
        "raw_my_info",
        "users",
        "my_info_async",
        "GET",
        "/myInfo",
        "read",
    ),
)

RAW_WRITE_OPERATIONS: tuple[RawOperation, ...] = (
    RawOperation(
        "createChannel",
        "raw_create_channel",
        "channels",
        "create_channel_async",
        "POST",
        "/createChannel",
        "write",
        (
            _p("name", required=True),
            _p("type_", required=True),
            _p("description"),
        ),
    ),
    RawOperation(
        "addUsersToChannel",
        "raw_add_users_to_channel",
        "channels",
        "add_users_to_channel_async",
        "POST",
        "/addUsersToChannel",
        "write",
        (
            _p("channel_id", required=True),
            _p("user_ids", list[str], required=True),
        ),
    ),
    RawOperation(
        "removeUserFromChannel",
        "raw_remove_user_from_channel",
        "channels",
        "remove_user_from_channel_async",
        "POST",
        "/removeUserFromChannel",
        "write",
        (
            _p("channel_id", required=True),
            _p("user_id", required=True),
        ),
        destructive=True,
    ),
    RawOperation(
        "sendMessage",
        "raw_send_message",
        "messages",
        "send_message_async",
        "POST",
        "/sendMessage",
        "write",
        (
            _p("text", required=True),
            _p("channel_id"),
            _p("channel"),
            _p("thread_root_id"),
            _p("as_bot", bool),
        ),
        request_wrapped=True,
    ),
    RawOperation(
        "sendReply",
        "raw_send_reply",
        "messages",
        "send_reply_async",
        "POST",
        "/sendReply",
        "write",
        (
            _p("text", required=True),
            _p("message_id", required=True),
            _p("channel_id"),
            _p("channel"),
            _p("also_send_to_channel", bool),
            _p("as_bot", bool),
        ),
        request_wrapped=True,
    ),
    RawOperation(
        "dmUser",
        "raw_dm_user",
        "messages",
        "dm_user_async",
        "POST",
        "/dmUser",
        "write",
        (
            _p("user_id", required=True),
            _p("text", required=True),
            _p("as_bot", bool),
        ),
    ),
    RawOperation(
        "dmGroup",
        "raw_dm_group",
        "messages",
        "dm_group_async",
        "POST",
        "/dmGroup",
        "write",
        (
            _p("user_ids", list[str], required=True),
            _p("text", required=True),
            _p("as_bot", bool),
        ),
    ),
    RawOperation(
        "deleteMessage",
        "raw_delete_message",
        "messages",
        "delete_message_async",
        "DELETE",
        "/deleteMessage",
        "write",
        (
            _p("message_id", required=True),
            _p("channel_id"),
            _p("channel"),
        ),
        destructive=True,
    ),
    RawOperation(
        "addReaction",
        "raw_add_reaction",
        "messages",
        "add_reaction_async",
        "POST",
        "/addReaction",
        "write",
        (
            _p("message_id", required=True),
            _p("reaction", required=True),
            _p("channel_id"),
            _p("skin_tone", int),
        ),
    ),
    RawOperation(
        "removeReaction",
        "raw_remove_reaction",
        "messages",
        "remove_reaction_async",
        "DELETE",
        "/removeReaction",
        "write",
        (
            _p("message_id", required=True),
            _p("reaction", required=True),
            _p("channel_id"),
        ),
        destructive=True,
    ),
    RawOperation(
        "editMessage",
        "raw_edit_message",
        "messages",
        "edit_message_async",
        "POST",
        "/editMessage",
        "write",
        (
            _p("message_id", required=True),
            _p("channel_id", required=True),
            _p("text", required=True),
        ),
    ),
    RawOperation(
        "createScheduledMessage",
        "raw_create_scheduled_message",
        "scheduled_messages",
        "create_scheduled_message_async",
        "POST",
        "/createScheduledMessage",
        "write",
        (
            _p("channel_id", required=True),
            _p("text", required=True),
            _p("send_at", int, required=True),
            _p("thread_root_id"),
            _p("also_send_to_channel", bool),
        ),
    ),
    RawOperation(
        "editScheduledMessage",
        "raw_edit_scheduled_message",
        "scheduled_messages",
        "edit_scheduled_message_async",
        "POST",
        "/editScheduledMessage",
        "write",
        (
            _p("scheduled_message_id", required=True),
            _p("channel_id", required=True),
            _p("text", required=True),
            _p("send_at", int, required=True),
        ),
    ),
    RawOperation(
        "deleteScheduledMessage",
        "raw_delete_scheduled_message",
        "scheduled_messages",
        "delete_scheduled_message_async",
        "DELETE",
        "/deleteScheduledMessage",
        "write",
        (_p("scheduled_message_id", required=True),),
        destructive=True,
    ),
    RawOperation(
        "customStatus",
        "raw_custom_status",
        "users",
        "custom_status_async",
        "POST",
        "/customStatus",
        "write",
        (
            _p("code", required=True),
            _p("expires_at", int, required=True),
            _p("status"),
        ),
    ),
)

ALL_RAW_OPERATIONS: tuple[RawOperation, ...] = tuple(
    sorted(
        (*RAW_READ_OPERATIONS, *RAW_WRITE_OPERATIONS),
        key=lambda op: op.path,
    )
)
