"""Hand-written async façade and helpers over the generated raw SDK.

This package is regen-safe: the Speakeasy generator never touches it.
Import cost stays small; nothing here pulls in MCP, telemetry backends,
or optional extras at import time.
"""

from pumble_keys.extensions.display import (
    display_channel,
    display_user,
    format_channel_candidate_label,
    format_user_candidate_label,
)
from pumble_keys.extensions.ids import (
    ChannelId,
    MessageId,
    PumbleId,
    ScheduledMessageId,
    UserGroupId,
    UserId,
    WorkspaceId,
    as_channel_id,
    as_message_id,
    as_scheduled_message_id,
    as_user_group_id,
    as_user_id,
    as_workspace_id,
    is_pumble_id_like,
    unbrand,
)
from pumble_keys.extensions.redaction import (
    REDACTED,
    redact_debug_headers,
    redact_debug_value,
    redact_sensitive_text,
)

__all__ = [
    "REDACTED",
    "ChannelId",
    "MessageId",
    "PumbleId",
    "ScheduledMessageId",
    "UserGroupId",
    "UserId",
    "WorkspaceId",
    "as_channel_id",
    "as_message_id",
    "as_scheduled_message_id",
    "as_user_group_id",
    "as_user_id",
    "as_workspace_id",
    "display_channel",
    "display_user",
    "format_channel_candidate_label",
    "format_user_candidate_label",
    "is_pumble_id_like",
    "redact_debug_headers",
    "redact_debug_value",
    "redact_sensitive_text",
    "unbrand",
]
