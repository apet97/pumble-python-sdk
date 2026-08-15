"""Deterministic user/channel resolution with bounded ambiguity.

Ported from ``extensions/resolve.ts``. The behavioral contract:

- User precedence: exact ID, exact email, exact name, partial name.
- Channel precedence: exact ID, exact name, partial name; one leading
  ``#`` is stripped from the input.
- Inputs are trimmed; comparison is case-insensitive by default.
- Blank input is ``not_found`` with no candidates.
- Ambiguity returns at most ``max_candidates`` (default 5) candidates
  in API list order — never sets, never re-sorted.
- Normal not-found/ambiguity outcomes are values, never exceptions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Generic, Literal, Protocol, TypeVar

from pumble_keys.extensions.display import (
    format_channel_candidate_label,
    format_user_candidate_label,
)

DEFAULT_MAX_CANDIDATES = 5

TValue = TypeVar("TValue")
TCandidate = TypeVar("TCandidate")

ResolveFailureReason = Literal["not_found", "ambiguous"]


class ResolveUserClient(Protocol):
    async def list_users(self) -> list[Any]: ...


class ResolveChannelClient(Protocol):
    async def list_channels(self) -> list[Any]: ...


@dataclass(frozen=True)
class UserCandidate:
    id: str
    email: str
    name: str
    label: str


@dataclass(frozen=True)
class ChannelCandidate:
    id: str
    name: str
    channel_type: str
    label: str


@dataclass(frozen=True)
class ResolveSuccess(Generic[TValue]):
    value: TValue
    ok: Literal[True] = True


@dataclass(frozen=True)
class ResolveFailure(Generic[TCandidate]):
    reason: ResolveFailureReason
    candidates: tuple[TCandidate, ...]
    ok: Literal[False] = False


ResolveUserResult = ResolveSuccess[Any] | ResolveFailure[UserCandidate]
ResolveChannelResult = ResolveSuccess[Any] | ResolveFailure[ChannelCandidate]


def _normalise(value: str, case_insensitive: bool) -> str:
    trimmed = value.strip()
    return trimmed.lower() if case_insensitive else trimmed


def _normalise_maybe(value: Any, case_insensitive: bool) -> str | None:
    return _normalise(value, case_insensitive) if isinstance(value, str) else None


def _channel_input(value: str, case_insensitive: bool) -> str:
    trimmed = value.strip()
    without_prefix = trimmed.removeprefix("#")
    return _normalise(without_prefix, case_insensitive)


def _candidate_limit(max_candidates: float | None) -> int:
    if max_candidates is None or not math.isfinite(max_candidates):
        return DEFAULT_MAX_CANDIDATES
    return max(0, math.floor(max_candidates))


def _from_matches(matches, max_candidates, to_candidate):
    if not matches:
        return ResolveFailure(reason="not_found", candidates=())
    if len(matches) == 1:
        return ResolveSuccess(value=matches[0])
    limit = _candidate_limit(max_candidates)
    return ResolveFailure(
        reason="ambiguous",
        candidates=tuple(to_candidate(match) for match in matches[:limit]),
    )


def _user_candidate(user: Any) -> UserCandidate:
    return UserCandidate(
        id=user.id,
        email=user.email,
        name=user.name,
        label=format_user_candidate_label(id=user.id, email=user.email, name=user.name),
    )


def _channel_candidate(channel: Any) -> ChannelCandidate:
    channel_type = str(channel.channel_type)
    return ChannelCandidate(
        id=channel.id,
        name=channel.name,
        channel_type=channel_type,
        label=format_channel_candidate_label(
            id=channel.id, name=channel.name, channel_type=channel_type
        ),
    )


async def resolve_user(
    client: ResolveUserClient,
    input_value: str,
    *,
    case_insensitive: bool = True,
    max_candidates: int | None = None,
) -> ResolveUserResult:
    """Resolve a user by exact ID, exact email, exact name, or partial name."""
    target = _normalise(input_value, case_insensitive)
    if not target:
        return ResolveFailure(reason="not_found", candidates=())

    users = await client.list_users()
    for key in ("id", "email", "name"):
        exact = [
            user
            for user in users
            if _normalise_maybe(getattr(user, key, None), case_insensitive) == target
        ]
        if exact:
            return _from_matches(exact, max_candidates, _user_candidate)

    partial = [
        user
        for user in users
        if (
            normalised := _normalise_maybe(
                getattr(user, "name", None), case_insensitive
            )
        )
        is not None
        and target in normalised
    ]
    return _from_matches(partial, max_candidates, _user_candidate)


async def resolve_channel(
    client: ResolveChannelClient,
    input_value: str,
    *,
    case_insensitive: bool = True,
    max_candidates: int | None = None,
) -> ResolveChannelResult:
    """Resolve a channel by exact ID, exact name, or partial name.

    A leading ``#`` is accepted for human-friendly channel inputs.
    """
    target = _channel_input(input_value, case_insensitive)
    if not target:
        return ResolveFailure(reason="not_found", candidates=())

    entries = await client.list_channels()
    channels = [entry.channel for entry in entries]
    for key in ("id", "name"):
        exact = [
            channel
            for channel in channels
            if _normalise_maybe(getattr(channel, key, None), case_insensitive) == target
        ]
        if exact:
            return _from_matches(exact, max_candidates, _channel_candidate)

    partial = [
        channel
        for channel in channels
        if (
            normalised := _normalise_maybe(
                getattr(channel, "name", None), case_insensitive
            )
        )
        is not None
        and target in normalised
    ]
    return _from_matches(partial, max_candidates, _channel_candidate)
