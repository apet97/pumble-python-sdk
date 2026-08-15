"""P07: compact display labels match the TypeScript contract exactly."""

from __future__ import annotations

from dataclasses import dataclass

from pumble_keys.extensions.display import (
    display_channel,
    display_user,
    format_channel_candidate_label,
    format_user_candidate_label,
)


@dataclass
class FakeChannel:
    name: str


@dataclass
class FakeUser:
    name: str
    email: str


def test_display_channel_adds_leading_hash() -> None:
    assert display_channel(FakeChannel(name="engineering")) == "#engineering"


def test_display_channel_keeps_existing_hash() -> None:
    assert display_channel(FakeChannel(name="#engineering")) == "#engineering"


def test_display_user_prefers_name() -> None:
    user = FakeUser(name="Example Name", email="user-1@example.invalid")
    assert display_user(user) == "Example Name"


def test_display_user_falls_back_to_email_for_blank_name() -> None:
    for blank in ("", "   "):
        user = FakeUser(name=blank, email="user-1@example.invalid")
        assert display_user(user) == "user-1@example.invalid"


def test_user_candidate_label_with_name() -> None:
    label = format_user_candidate_label(
        id="0" * 24, email="user-1@example.invalid", name=" Example Name "
    )
    assert label == "Example Name user-1@example.invalid | " + "0" * 24


def test_user_candidate_label_blank_name_omits_name() -> None:
    label = format_user_candidate_label(
        id="0" * 24, email="user-1@example.invalid", name="  "
    )
    assert label == "user-1@example.invalid | " + "0" * 24


def test_channel_candidate_label_format() -> None:
    label = format_channel_candidate_label(
        id="0" * 24, name="engineering", channel_type="PUBLIC"
    )
    assert label == "#engineering | PUBLIC | " + "0" * 24
