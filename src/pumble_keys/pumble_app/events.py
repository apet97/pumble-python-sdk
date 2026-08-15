"""Typed Pumble webhook events.

Ported from ``extensions/webhook-events.ts`` and the normalizer in
``extensions/webhooks.ts``. Seven event types; Pydantic models describe
the known compact fields (``aId``, ``cId``, ``tx``, ``mId``, …) while
unknown fields are preserved (``extra="allow"``) for forward
compatibility. The raw payload rides along on the event but is excluded
from serialization so message content is not re-emitted by accident.

Two wire forms are supported:

- the full envelope: ``{"eventType": ..., "body": <dict or JSON
  string>, "workspaceId": ..., "workspaceUserIds": [...]}``;
- the compact body form: the notification body itself with its ``ty``
  discriminator.
"""

from __future__ import annotations

import json
from typing import Any, Literal

import pydantic

PumbleWebhookEventType = Literal[
    "NEW_MESSAGE",
    "UPDATED_MESSAGE",
    "REACTION_ADDED",
    "CHANNEL_CREATED",
    "APP_UNINSTALLED",
    "APP_UNAUTHORIZED",
    "WORKSPACE_USER_JOINED",
]

KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    (
        "NEW_MESSAGE",
        "UPDATED_MESSAGE",
        "REACTION_ADDED",
        "CHANNEL_CREATED",
        "APP_UNINSTALLED",
        "APP_UNAUTHORIZED",
        "WORKSPACE_USER_JOINED",
    )
)


class _NotificationBase(pydantic.BaseModel):
    """Compact notification base: unknown fields are preserved."""

    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    w_id: str | None = pydantic.Field(default=None, alias="wId")
    ty: str | None = None
    rid: str | None = None


class NotificationMessage(_NotificationBase):
    m_id: str | None = pydantic.Field(default=None, alias="mId")
    c_id: str | None = pydantic.Field(default=None, alias="cId")
    tr_id: str | None = pydantic.Field(default=None, alias="trId")
    a_id: str | None = pydantic.Field(default=None, alias="aId")
    tx: str | None = None
    bl: list[dict[str, Any]] | None = None
    ts: str | None = None
    tsm: int | None = None
    st: str | None = None
    l_id: str | None = pydantic.Field(default=None, alias="lId")
    e: bool | None = None
    eph: bool | None = None


class NotificationReaction(_NotificationBase):
    c_id: str | None = pydantic.Field(default=None, alias="cId")
    m_id: str | None = pydantic.Field(default=None, alias="mId")
    mat: str | None = None
    u_id: str | None = pydantic.Field(default=None, alias="uId")
    rc: str | None = None


class NotificationChannel(_NotificationBase):
    c_id: str | None = pydantic.Field(default=None, alias="cId")
    c_n: str | None = pydantic.Field(default=None, alias="cN")
    c_u: list[str] | None = pydantic.Field(default=None, alias="cU")
    c_t: str | None = pydantic.Field(default=None, alias="cT")


class NotificationWorkspaceUserJoined(_NotificationBase):
    u_n: str | None = pydantic.Field(default=None, alias="uN")
    u_e: str | None = pydantic.Field(default=None, alias="uE")
    u_id: str | None = pydantic.Field(default=None, alias="uId")
    tz: str | None = None
    sts: str | None = None
    ro: str | None = None


class NotificationAppUninstalled(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = None
    app: str | None = None
    workspace: str | None = None
    installed_by: str | None = pydantic.Field(default=None, alias="installedBy")
    bot_user: str | None = pydantic.Field(default=None, alias="botUser")
    uninstalled_at: Any = pydantic.Field(default=None, alias="uninstalledAt")


class NotificationAppUnauthorized(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = None
    app: str | None = None
    app_installation: str | None = pydantic.Field(default=None, alias="appInstallation")
    workspace_user: str | None = pydantic.Field(default=None, alias="workspaceUser")
    workspace: str | None = None
    granted_scopes: list[str] | None = pydantic.Field(
        default=None, alias="grantedScopes"
    )
    access_granted: bool | None = pydantic.Field(default=None, alias="accessGranted")


_BODY_MODEL_BY_TYPE: dict[str, type[pydantic.BaseModel]] = {
    "NEW_MESSAGE": NotificationMessage,
    "UPDATED_MESSAGE": NotificationMessage,
    "REACTION_ADDED": NotificationReaction,
    "CHANNEL_CREATED": NotificationChannel,
    "APP_UNINSTALLED": NotificationAppUninstalled,
    "APP_UNAUTHORIZED": NotificationAppUnauthorized,
    "WORKSPACE_USER_JOINED": NotificationWorkspaceUserJoined,
}


class PumbleWebhookEvent(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    type: PumbleWebhookEventType
    body: (
        NotificationMessage
        | NotificationReaction
        | NotificationChannel
        | NotificationWorkspaceUserJoined
        | NotificationAppUninstalled
        | NotificationAppUnauthorized
    )
    workspace_id: str | None = None
    workspace_user_ids: tuple[str, ...] | None = None
    raw: Any = pydantic.Field(default=None, exclude=True, repr=False)


def _string_array(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def _workspace_id_from_body(body: dict[str, Any]) -> str | None:
    compact = body.get("wId")
    if isinstance(compact, str):
        return compact
    full = body.get("workspace")
    return full if isinstance(full, str) else None


def _parse_envelope_body(body: Any) -> Any:
    if not isinstance(body, str):
        return body
    return json.loads(body)  # malformed JSON propagates, mirroring the TS


def _event_for(
    event_type: str,
    body: dict[str, Any],
    raw: Any,
    *,
    workspace_id: str | None,
    workspace_user_ids: tuple[str, ...] | None = None,
) -> PumbleWebhookEvent | None:
    model = _BODY_MODEL_BY_TYPE[event_type]
    try:
        parsed = model.model_validate(body)
    except pydantic.ValidationError:
        return None
    return PumbleWebhookEvent(
        type=event_type,  # type: ignore[arg-type]
        body=parsed,
        workspace_id=workspace_id,
        workspace_user_ids=workspace_user_ids,
        raw=raw,
    )


def normalize_webhook_event(payload: Any) -> PumbleWebhookEvent | None:
    """Normalize an envelope or compact payload; ``None`` when unknown.

    A malformed JSON-string envelope body raises ``ValueError``
    (mirroring the source SDK); the P20 receiver maps that to HTTP 400.
    """
    if not isinstance(payload, dict):
        return None

    event_type = payload.get("eventType")
    if isinstance(event_type, str) and event_type in KNOWN_EVENT_TYPES:
        body = _parse_envelope_body(payload.get("body"))
        if not isinstance(body, dict):
            return None
        workspace_id = payload.get("workspaceId")
        if not isinstance(workspace_id, str):
            workspace_id = _workspace_id_from_body(body)
        return _event_for(
            event_type,
            body,
            payload,
            workspace_id=workspace_id,
            workspace_user_ids=_string_array(payload.get("workspaceUserIds")),
        )

    compact_type = payload.get("ty")
    if isinstance(compact_type, str) and compact_type in KNOWN_EVENT_TYPES:
        return _event_for(
            compact_type,
            payload,
            payload,
            workspace_id=_workspace_id_from_body(payload),
        )

    return None
