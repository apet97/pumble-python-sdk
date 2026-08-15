"""P07: validated opaque ID aliases."""

from __future__ import annotations

import pytest

from pumble_keys.extensions import ids

VALID_ID = "0123456789abcdef01234567"

TAGGERS = [
    ids.as_channel_id,
    ids.as_message_id,
    ids.as_scheduled_message_id,
    ids.as_user_id,
    ids.as_user_group_id,
    ids.as_workspace_id,
]


@pytest.mark.parametrize("tagger", TAGGERS)
def test_valid_hex24_passes_and_is_identity(tagger) -> None:
    assert tagger(VALID_ID) == VALID_ID
    assert isinstance(tagger(VALID_ID), str)


@pytest.mark.parametrize("tagger", TAGGERS)
@pytest.mark.parametrize(
    "bad",
    [
        "",
        " ",
        "short",
        VALID_ID + "0",  # 25 chars
        VALID_ID[:-1],  # 23 chars
        "0123456789abcdef0123456g",  # non-hex char
        " " + VALID_ID[1:],  # leading space
        None,
        123,
    ],
)
def test_invalid_shapes_raise_value_error(tagger, bad) -> None:
    with pytest.raises(ValueError):
        tagger(bad)


def test_uppercase_hex_is_accepted() -> None:
    assert ids.as_channel_id(VALID_ID.upper()) == VALID_ID.upper()


def test_is_pumble_id_like_does_not_raise() -> None:
    assert ids.is_pumble_id_like(VALID_ID) is True
    assert ids.is_pumble_id_like("nope") is False
    assert ids.is_pumble_id_like(None) is False
    assert ids.is_pumble_id_like(42) is False


def test_unbrand_is_identity() -> None:
    channel_id = ids.as_channel_id(VALID_ID)
    assert ids.unbrand(channel_id) == VALID_ID


def test_error_message_names_the_helper() -> None:
    with pytest.raises(ValueError, match="as_message_id"):
        ids.as_message_id("bad")
