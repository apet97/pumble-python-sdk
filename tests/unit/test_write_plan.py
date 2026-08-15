"""P28: write-plan helpers — excerpt edge cases."""

from __future__ import annotations

from pumble_keys.extensions.write_plan import excerpt_text


def test_excerpt_text_of_none_is_empty() -> None:
    assert excerpt_text(None) == ""
