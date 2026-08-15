"""P10: find helpers — thin conveniences over the listings."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from pumble_keys.extensions.find import find_channel_by_name, find_user_by_email


@dataclass
class FakeUser:
    id: str
    email: str
    name: str


@dataclass
class FakeChannel:
    id: str
    name: str


@dataclass
class FakeEntry:
    channel: FakeChannel


@dataclass
class FakeClient:
    users_list: list[FakeUser] = field(default_factory=list)
    channels_list: list[FakeChannel] = field(default_factory=list)

    async def list_users(self):
        return self.users_list

    async def list_channels(self):
        return [FakeEntry(channel=c) for c in self.channels_list]


UID = "0" * 20 + "0001"


@pytest.mark.asyncio
async def test_find_user_by_email_case_insensitive_default() -> None:
    user = FakeUser(id=UID, email="User-1@Example.invalid", name="U")
    client = FakeClient(users_list=[user])
    assert await find_user_by_email(client, " user-1@example.INVALID ") is user


@pytest.mark.asyncio
async def test_find_user_by_email_case_sensitive_option() -> None:
    user = FakeUser(id=UID, email="User-1@example.invalid", name="U")
    client = FakeClient(users_list=[user])
    assert (
        await find_user_by_email(
            client, "user-1@example.invalid", case_insensitive=False
        )
        is None
    )


@pytest.mark.asyncio
async def test_find_user_no_match_returns_none() -> None:
    assert await find_user_by_email(FakeClient(), "x@example.invalid") is None


@pytest.mark.asyncio
async def test_find_channel_by_name() -> None:
    channel = FakeChannel(id=UID, name="Engineering")
    client = FakeClient(channels_list=[channel])
    assert await find_channel_by_name(client, "engineering") is channel
    assert await find_channel_by_name(client, "missing") is None
