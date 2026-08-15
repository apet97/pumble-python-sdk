"""Immutable MCP profile values.

- ``curated`` — 7 compact reads + preview/confirmed writes + the App.
- ``curated-interactive`` — curated plus the MRTR tools (P33).
- ``readonly`` — exact adapters for all 11 read operations; no App.
- ``readwrite`` — exact adapters for all 26 operations behind explicit
  gates; ``dry_run`` is an option on this profile, not a profile.
"""

from __future__ import annotations

from enum import Enum


class Profile(str, Enum):
    CURATED = "curated"
    CURATED_INTERACTIVE = "curated-interactive"
    READONLY = "readonly"
    READWRITE = "readwrite"

    @classmethod
    def parse(cls, value: str) -> Profile:
        try:
            return cls(value)
        except ValueError as error:
            valid = ", ".join(profile.value for profile in cls)
            raise ValueError(
                f"unknown MCP profile {value!r}; expected one of: {valid}"
            ) from error


APP_ENABLED_PROFILES: frozenset[Profile] = frozenset(
    {Profile.CURATED, Profile.CURATED_INTERACTIVE}
)
