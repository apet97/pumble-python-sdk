"""CLI formatting helpers — pure-function branch coverage."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from pumble_keys.cli import formatting as fmt


@dataclass
class _Receipt:
    id: str
    nested: dict


def test_to_jsonable_dataclass() -> None:
    value = _Receipt(id="abc", nested={"k": ("a", "b")})
    assert fmt.to_jsonable(value) == {"id": "abc", "nested": {"k": ["a", "b"]}}


def test_mask_key_short_key_is_none() -> None:
    assert fmt.mask_key("abc") == "(none)"
    assert fmt.mask_key("") == "(none)"


def test_iso_non_int_is_empty() -> None:
    assert fmt._iso("not-a-timestamp") == ""
    assert fmt._iso(None) == ""


def test_format_timestamp_str_passthrough() -> None:
    message = SimpleNamespace(timestamp="2026-08-15T00:00:00Z")
    assert fmt.format_timestamp(message) == "2026-08-15T00:00:00Z"


def test_normalise_emoji_code_passthrough() -> None:
    assert fmt.normalise_emoji_code(":wave:") == ":wave:"


def test_format_timestamp_falls_back_to_milli() -> None:
    message = SimpleNamespace(timestamp=None, timestamp_milli=1_786_752_000_000)
    assert fmt.format_timestamp(message) == "2026-08-15T00:00:00Z"
