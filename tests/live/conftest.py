"""Live sacrificial-workspace suite: gating, ledger, and receipt.

Runs ONLY with explicit opt-in:

- ``PUMBLE_LIVE=1``
- ``PUMBLE_API_KEY`` (environment only — never a file or argv)
- ``PUMBLE_LIVE_CHANNEL_ID`` — the sacrificial channel; its presence in
  the key's channel list is the workspace marker. The session aborts
  before any write if the marker is missing.

Everything created carries the ``PYSDK-PROBE-<stamp>-<nonce>`` prefix,
is verified by direct read, and is deleted before the session ends.
The receipt (``PUMBLE_LIVE_RECEIPT``, default ``live_receipt.json``)
records operation counts and sha256-hashed IDs only — no message
content, no e-mails, no raw live IDs.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path

import pytest

LIVE = os.environ.get("PUMBLE_LIVE") == "1"

pytestmark = pytest.mark.skipif(not LIVE, reason="PUMBLE_LIVE=1 not set")


def _require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        pytest.exit(f"live suite requires {name} in the environment", 2)
    return value


def hash_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


class Ledger:
    """Session evidence: counts and hashed IDs, never content."""

    def __init__(self) -> None:
        self.reads: dict[str, int] = {}
        self.writes: dict[str, int] = {}
        self.created: dict[str, dict] = {}  # id -> {kind, id_hash}
        self.deleted: list[dict] = []
        self.skipped: list[str] = []

    def read(self, operation: str) -> None:
        self.reads[operation] = self.reads.get(operation, 0) + 1

    def write(self, operation: str) -> None:
        self.writes[operation] = self.writes.get(operation, 0) + 1

    def track(self, kind: str, object_id: str) -> None:
        self.created[object_id] = {"kind": kind, "id_hash": hash_id(object_id)}

    def untrack(self, object_id: str) -> None:
        entry = self.created.pop(object_id, None)
        if entry is not None:
            self.deleted.append(entry)

    def residue(self) -> list[dict]:
        return list(self.created.values())

    def receipt(self) -> dict:
        return {
            "suite": "pumble-python-sdk live",
            "probe_prefix": PROBE_PREFIX,
            "read_counts": dict(sorted(self.reads.items())),
            "write_counts": dict(sorted(self.writes.items())),
            "created_total": len(self.deleted) + len(self.created),
            "deleted": self.deleted,
            "cleanup_residue": self.residue(),
            "skipped": self.skipped,
        }


PROBE_PREFIX = f"PYSDK-PROBE-{int(time.time())}-{secrets.token_hex(4)}"

_ledger = Ledger()


@pytest.fixture(scope="session")
def ledger() -> Ledger:
    return _ledger


@pytest.fixture(scope="session")
def probe_prefix() -> str:
    return PROBE_PREFIX


@pytest.fixture(scope="session")
def live_channel_id() -> str:
    return _require_env("PUMBLE_LIVE_CHANNEL_ID")


@pytest.fixture(scope="session")
def api_key() -> str:
    return _require_env("PUMBLE_API_KEY")


def pytest_sessionfinish(session, exitstatus) -> None:
    if not LIVE:
        return
    path = Path(os.environ.get("PUMBLE_LIVE_RECEIPT", "live_receipt.json"))
    receipt = _ledger.receipt()
    receipt["exit_status"] = int(exitstatus)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
