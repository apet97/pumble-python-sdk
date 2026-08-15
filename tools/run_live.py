#!/usr/bin/env python3
"""Run the live sacrificial-workspace suite and stamp the receipt.

    PUMBLE_LIVE=1 uv run python tools/run_live.py --profile full --require-cleanup

Requirements (environment only — the runner REFUSES key material on
argv): ``PUMBLE_API_KEY``, ``PUMBLE_LIVE_CHANNEL_ID``. The receipt
(``PUMBLE_LIVE_RECEIPT``, default ``live_receipt.json``) is machine
readable: commit, OpenAPI spec sha256, operation counts, hashed
created/deleted IDs, cleanup residue, and skipped checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["full", "read"], default="full")
    parser.add_argument("--require-cleanup", action="store_true")
    args = parser.parse_args()

    for argument in sys.argv[1:]:
        if len(argument) >= 24 and all(
            c in "0123456789abcdef" for c in argument.lower()
        ):
            print("FAIL: never pass key or ID material on argv; use env vars")
            return 2
    if os.environ.get("PUMBLE_LIVE") != "1":
        print("FAIL: set PUMBLE_LIVE=1 explicitly to run the live suite")
        return 2
    for name in ("PUMBLE_API_KEY", "PUMBLE_LIVE_CHANNEL_ID"):
        if not os.environ.get(name):
            print(f"FAIL: {name} missing from the environment")
            return 2

    receipt_path = Path(os.environ.get("PUMBLE_LIVE_RECEIPT", "live_receipt.json"))
    selection = ["tests/live"]
    if args.profile == "read":
        selection = [
            "tests/live/test_live_suite.py::test_00_workspace_guard",
            "tests/live/test_live_suite.py::test_01_read_smoke",
        ]
    completed = subprocess.run(
        ["uv", "run", "pytest", "-q", *selection], cwd=REPO, check=False
    )

    receipt = {}
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    receipt.update(
        {
            "commit": commit,
            "spec_sha256": hashlib.sha256(
                (REPO / "PumbleOpenApi.yaml").read_bytes()
            ).hexdigest(),
            "profile": args.profile,
            "finished_at": int(time.time()),
            "pytest_exit": completed.returncode,
        }
    )
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"receipt: {receipt_path}")

    if completed.returncode != 0:
        return completed.returncode
    if args.require_cleanup and receipt.get("cleanup_residue"):
        print("FAIL: cleanup residue is nonzero")
        return 1
    print("OK: live suite passed with zero residue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
