#!/usr/bin/env python3
"""Validate the packet table in IMPLEMENTATION_STATUS.md.

Rules:
- Exactly 46 packets, P00 through P45, in order, no duplicates.
- Every status is NOT_STARTED, IN_PROGRESS, DONE, or BLOCKED.
- At most one packet is IN_PROGRESS.
- No packet is DONE or IN_PROGRESS while an earlier packet is NOT_STARTED
  (packets must not be skipped).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

STATUS_FILE = Path(__file__).resolve().parent.parent / "IMPLEMENTATION_STATUS.md"
VALID = {"NOT_STARTED", "IN_PROGRESS", "DONE", "BLOCKED"}
ROW = re.compile(r"^\| (P\d{2}) [^|]*\| (\S+) \|")


def parse_rows(text: str) -> list[tuple[str, str]]:
    rows = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match:
            rows.append((match.group(1), match.group(2)))
    return rows


def check(rows: list[tuple[str, str]]) -> list[str]:
    errors = []
    expected = [f"P{i:02d}" for i in range(46)]
    ids = [packet for packet, _ in rows]
    if ids != expected:
        errors.append(f"packet ids/order wrong: got {len(ids)} rows")
    for packet, status in rows:
        if status not in VALID:
            errors.append(f"{packet}: invalid status {status!r}")
    in_progress = [packet for packet, status in rows if status == "IN_PROGRESS"]
    if len(in_progress) > 1:
        errors.append(f"multiple IN_PROGRESS: {', '.join(in_progress)}")
    seen_not_started = None
    for packet, status in rows:
        if status == "NOT_STARTED" and seen_not_started is None:
            seen_not_started = packet
        elif status in ("DONE", "IN_PROGRESS") and seen_not_started is not None:
            errors.append(f"{packet} is {status} but {seen_not_started} was skipped")
    return errors


def main() -> int:
    rows = parse_rows(STATUS_FILE.read_text())
    errors = check(rows)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    done = sum(1 for _, status in rows if status == "DONE")
    print(f"status OK: {done}/46 packets DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
