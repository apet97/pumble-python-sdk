"""Hand-written async façade and helpers over the generated raw SDK.

This package is regen-safe: the Speakeasy generator never touches it.
Import cost stays small; nothing here pulls in MCP, telemetry backends,
or optional extras at import time.
"""

from pumble_keys.extensions.client import (
    ChannelSummary,
    PumbleClient,
    UserSummary,
    create_pumble_client,
)
from pumble_keys.extensions.display import (
    display_channel,
    display_user,
    format_channel_candidate_label,
    format_user_candidate_label,
)
from pumble_keys.extensions.errors import (
    CategorizedError,
    ErrorCategory,
    categorize_error,
)
from pumble_keys.extensions.find import (
    find_channel_by_name,
    find_user_by_email,
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
from pumble_keys.extensions.operations import (
    OPERATION_FAILURE_NEXT_ACTION,
    is_facade_operation_failure,
    operation_failure,
    operation_failure_reason,
)
from pumble_keys.extensions.pagination import list_all_messages
from pumble_keys.extensions.preflight import (
    PreflightResult,
    preflight_resolvers,
)
from pumble_keys.extensions.rate_limit import (
    RateLimiter,
    RateLimitQueueFullError,
)
from pumble_keys.extensions.redaction import (
    REDACTED,
    redact_debug_headers,
    redact_debug_value,
    redact_sensitive_text,
)
from pumble_keys.extensions.resolve import (
    ChannelCandidate,
    ResolveChannelResult,
    ResolveFailure,
    ResolveSuccess,
    ResolveUserResult,
    UserCandidate,
    resolve_channel,
    resolve_user,
)
from pumble_keys.extensions.resolver_cache import ResolverCache
from pumble_keys.extensions.results import (
    FacadeError,
    FacadeFailure,
    FacadeFailureReason,
    assert_facade_ok,
    create_facade_failure,
    create_facade_invalid_request,
    create_facade_operation_failure,
    is_facade_failure,
)
from pumble_keys.extensions.retries import (
    DEFAULT_RETRY_STATUSES,
    READ_OPERATION_IDS,
    is_safe_to_retry,
    mark_safe_to_retry,
    with_retries,
)
from pumble_keys.extensions.scheduled import ScheduledFacade
from pumble_keys.extensions.search import (
    HARD_PAGE_CAP,
    PageCapExceededError,
    search_all_messages,
)
from pumble_keys.extensions.status import StatusFacade
from pumble_keys.extensions.telemetry import (
    SPAN_ATTRIBUTE_ALLOWLIST,
    JsonlAuditWriter,
    NoopRecorder,
    create_otel_span_recorder,
    traced,
)
from pumble_keys.extensions.threads import (
    ThreadContext,
    ThreadContextMessage,
    get_thread_context,
    reply_to_thread,
)
from pumble_keys.extensions.writes import (
    FacadeWrites,
    WriteReceipt,
    WriteVerification,
)

__all__ = [
    "DEFAULT_RETRY_STATUSES",
    "HARD_PAGE_CAP",
    "OPERATION_FAILURE_NEXT_ACTION",
    "READ_OPERATION_IDS",
    "REDACTED",
    "SPAN_ATTRIBUTE_ALLOWLIST",
    "CategorizedError",
    "ChannelCandidate",
    "ChannelId",
    "ChannelSummary",
    "ErrorCategory",
    "FacadeError",
    "FacadeFailure",
    "FacadeFailureReason",
    "FacadeWrites",
    "JsonlAuditWriter",
    "MessageId",
    "NoopRecorder",
    "PageCapExceededError",
    "PreflightResult",
    "PumbleClient",
    "PumbleId",
    "RateLimitQueueFullError",
    "RateLimiter",
    "ResolveChannelResult",
    "ResolveFailure",
    "ResolveSuccess",
    "ResolveUserResult",
    "ResolverCache",
    "ScheduledFacade",
    "ScheduledMessageId",
    "StatusFacade",
    "ThreadContext",
    "ThreadContextMessage",
    "UserCandidate",
    "UserGroupId",
    "UserId",
    "UserSummary",
    "WorkspaceId",
    "WriteReceipt",
    "WriteVerification",
    "as_channel_id",
    "as_message_id",
    "as_scheduled_message_id",
    "as_user_group_id",
    "as_user_id",
    "as_workspace_id",
    "assert_facade_ok",
    "categorize_error",
    "create_facade_failure",
    "create_facade_invalid_request",
    "create_facade_operation_failure",
    "create_otel_span_recorder",
    "create_pumble_client",
    "display_channel",
    "display_user",
    "find_channel_by_name",
    "find_user_by_email",
    "format_channel_candidate_label",
    "format_user_candidate_label",
    "get_thread_context",
    "is_facade_failure",
    "is_facade_operation_failure",
    "is_pumble_id_like",
    "is_safe_to_retry",
    "list_all_messages",
    "mark_safe_to_retry",
    "operation_failure",
    "operation_failure_reason",
    "preflight_resolvers",
    "redact_debug_headers",
    "redact_debug_value",
    "redact_sensitive_text",
    "reply_to_thread",
    "resolve_channel",
    "resolve_user",
    "search_all_messages",
    "traced",
    "unbrand",
    "with_retries",
]
