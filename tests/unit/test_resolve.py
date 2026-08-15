"""P10: resolver precedence, ambiguity bounds, and value-not-exception outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from pumble_keys.extensions.resolve import (
    ChannelCandidate,
    ResolveFailure,
    ResolveSuccess,
    resolve_channel,
    resolve_user,
)


@dataclass
class FakeUser:
    id: str
    email: str
    name: str


@dataclass
class FakeChannel:
    id: str
    name: str
    channel_type: str = "PUBLIC"


@dataclass
class FakeEntry:
    channel: FakeChannel


@dataclass
class FakeUsersClient:
    users: list[FakeUser] = field(default_factory=list)
    calls: int = 0

    async def list_users(self) -> list[FakeUser]:
        self.calls += 1
        return self.users


@dataclass
class FakeChannelsClient:
    channels: list[FakeChannel] = field(default_factory=list)
    calls: int = 0

    async def list_channels(self) -> list[FakeEntry]:
        self.calls += 1
        return [FakeEntry(channel=c) for c in self.channels]


UID = [f"{'0' * 20}{i:04d}" for i in range(10)]


def users_client(*users: FakeUser) -> FakeUsersClient:
    return FakeUsersClient(users=list(users))


def channels_client(*channels: FakeChannel) -> FakeChannelsClient:
    return FakeChannelsClient(channels=list(channels))


@pytest.mark.asyncio
async def test_blank_input_is_not_found_without_api_call() -> None:
    client = users_client()
    for blank in ("", "   ", "\t"):
        result = await resolve_user(client, blank)
        assert isinstance(result, ResolveFailure)
        assert result.reason == "not_found"
        assert result.candidates == ()
    assert client.calls == 0

    channel_result = await resolve_channel(channels_client(), "  # ")
    assert channel_result.reason == "not_found"


@pytest.mark.asyncio
async def test_user_exact_id_beats_email_and_name() -> None:
    decoy = FakeUser(id=UID[1], email=f"{UID[0]}@example.invalid", name=UID[0])
    target = FakeUser(id=UID[0], email="a@example.invalid", name="A")
    result = await resolve_user(users_client(decoy, target), UID[0])
    assert isinstance(result, ResolveSuccess)
    assert result.value is target


@pytest.mark.asyncio
async def test_user_exact_email_beats_name() -> None:
    named = FakeUser(id=UID[1], email="b@example.invalid", name="a@example.invalid")
    emailed = FakeUser(id=UID[2], email="a@example.invalid", name="B")
    result = await resolve_user(users_client(named, emailed), "a@example.invalid")
    assert isinstance(result, ResolveSuccess)
    assert result.value is emailed


@pytest.mark.asyncio
async def test_user_exact_name_beats_partial() -> None:
    partial = FakeUser(id=UID[1], email="p@example.invalid", name="Anna-Maria")
    exact = FakeUser(id=UID[2], email="e@example.invalid", name="Anna")
    result = await resolve_user(users_client(partial, exact), "anna")
    assert isinstance(result, ResolveSuccess)
    assert result.value is exact


@pytest.mark.asyncio
async def test_user_partial_name_match() -> None:
    user = FakeUser(id=UID[1], email="x@example.invalid", name="Example Person")
    result = await resolve_user(users_client(user), "ample per")
    assert isinstance(result, ResolveSuccess)
    assert result.value is user


@pytest.mark.asyncio
async def test_duplicate_exact_matches_are_ambiguous() -> None:
    twin_a = FakeUser(id=UID[1], email="a@example.invalid", name="Twin")
    twin_b = FakeUser(id=UID[2], email="b@example.invalid", name="Twin")
    result = await resolve_user(users_client(twin_a, twin_b), "Twin")
    assert isinstance(result, ResolveFailure)
    assert result.reason == "ambiguous"
    assert [c.id for c in result.candidates] == [UID[1], UID[2]]
    assert result.candidates[0].label == f"Twin a@example.invalid | {UID[1]}"


@pytest.mark.asyncio
async def test_candidate_cap_default_five_and_api_order() -> None:
    users = [
        FakeUser(id=UID[i], email=f"u{i}@example.invalid", name=f"Common {i}")
        for i in range(1, 9)
    ]
    result = await resolve_user(users_client(*users), "common")
    assert isinstance(result, ResolveFailure)
    assert len(result.candidates) == 5
    assert [c.id for c in result.candidates] == [UID[i] for i in range(1, 6)]


@pytest.mark.asyncio
async def test_candidate_cap_override() -> None:
    users = [
        FakeUser(id=UID[i], email=f"u{i}@example.invalid", name=f"Common {i}")
        for i in range(1, 5)
    ]
    result = await resolve_user(users_client(*users), "common", max_candidates=2)
    assert isinstance(result, ResolveFailure)
    assert len(result.candidates) == 2


@pytest.mark.asyncio
async def test_case_sensitive_option() -> None:
    user = FakeUser(id=UID[1], email="a@example.invalid", name="Anna")
    insensitive = await resolve_user(users_client(user), "anna")
    assert isinstance(insensitive, ResolveSuccess)
    sensitive = await resolve_user(users_client(user), "anna", case_insensitive=False)
    assert isinstance(sensitive, ResolveFailure)
    assert sensitive.reason == "not_found"


@pytest.mark.asyncio
async def test_channel_precedence_and_hash_stripping() -> None:
    by_id = FakeChannel(id=UID[1], name="one")
    by_name = FakeChannel(id=UID[2], name=UID[1])
    client = channels_client(by_id, by_name)

    result = await resolve_channel(client, UID[1])
    assert isinstance(result, ResolveSuccess)
    assert result.value is by_id  # exact id beats exact name

    hashed = await resolve_channel(channels_client(by_id), "#one")
    assert isinstance(hashed, ResolveSuccess)
    assert hashed.value is by_id

    double_hash = await resolve_channel(channels_client(by_id), "##one")
    assert isinstance(double_hash, ResolveFailure)  # only one '#' stripped


@pytest.mark.asyncio
async def test_channel_partial_and_ambiguity_labels() -> None:
    eng = FakeChannel(id=UID[1], name="engineering")
    eng_alerts = FakeChannel(id=UID[2], name="engineering-alerts")
    result = await resolve_channel(channels_client(eng, eng_alerts), "engineer")
    assert isinstance(result, ResolveFailure)
    assert result.reason == "ambiguous"
    assert result.candidates[0] == ChannelCandidate(
        id=UID[1],
        name="engineering",
        channel_type="PUBLIC",
        label=f"#engineering | PUBLIC | {UID[1]}",
    )


@pytest.mark.asyncio
async def test_channel_not_found_returns_value() -> None:
    result = await resolve_channel(
        channels_client(FakeChannel(id=UID[1], name="one")), "missing"
    )
    assert isinstance(result, ResolveFailure)
    assert result.reason == "not_found"
    assert result.candidates == ()
