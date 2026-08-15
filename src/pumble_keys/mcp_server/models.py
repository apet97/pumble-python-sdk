"""Pydantic input/output models for the curated MCP tools.

Every model is compact by design: tool payloads must never dump an
unbounded history or a raw generated object into the model context.
Normal operational failures are values (``CuratedFailure``), never
protocol errors.
"""

from __future__ import annotations

from typing import Literal

import pydantic

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


class CuratedFailure(pydantic.BaseModel):
    """Uniform curated failure value (mirrors the façade contract)."""

    ok: Literal[False] = False
    reason: str
    summary: str
    choices: list[Choice] = []
    next_actions: list[str] = []


class Choice(pydantic.BaseModel):
    id: str
    label: str
    name: str | None = None
    email: str | None = None


class WhoamiResult(pydantic.BaseModel):
    ok: Literal[True] = True
    id: str
    name: str
    email: str
    role: str | None = None


class ChannelInfo(pydantic.BaseModel):
    id: str
    name: str
    channel_type: str


class UserInfo(pydantic.BaseModel):
    id: str
    name: str
    email: str


class FindChannelResult(pydantic.BaseModel):
    ok: Literal[True] = True
    summary: str
    channel: ChannelInfo


class FindUserResult(pydantic.BaseModel):
    ok: Literal[True] = True
    summary: str
    user: UserInfo


class ListChannelsResult(pydantic.BaseModel):
    ok: Literal[True] = True
    channels: list[ChannelInfo]
    count: int
    truncated: bool


class CompactMessage(pydantic.BaseModel):
    id: str
    channel_id: str
    author: str
    text: str
    timestamp_milli: int | None = None


class SearchResult(pydantic.BaseModel):
    ok: Literal[True] = True
    hits: list[CompactMessage]
    count: int
    total_elements: int | None = None
    has_more: bool | None = None


class ChannelContextResult(pydantic.BaseModel):
    ok: Literal[True] = True
    channel_id: str
    messages: list[CompactMessage]
    next_cursor: str | None = None
    resource_uri: str


class ThreadContextResult(pydantic.BaseModel):
    ok: Literal[True] = True
    channel_id: str
    root: CompactMessage
    replies: list[CompactMessage]
    participants: list[str]
    reply_count: int
    resource_uri: str


CuratedFailure.model_rebuild()
