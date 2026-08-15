"""Shared loaders for the replay-parity suite."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPLAY = REPO / "fixtures" / "replay"


def load(group: str, name: str) -> dict:
    return json.loads((REPLAY / group / f"{name}.json").read_text())


def fixture_names(group: str) -> list[str]:
    return sorted(path.stem for path in (REPLAY / group).glob("*.json"))
