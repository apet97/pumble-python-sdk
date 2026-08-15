#!/usr/bin/env python3
"""Repo-wide secret scan over git-tracked text files.

    uv run python tools/scan_secrets.py --changed   # PR gate
    uv run python tools/scan_secrets.py --all       # full gate

Reuses the shape-based detectors from ``tools/sanitize_fixture.py``
(API-key-shaped 32-hex, live-ID-shaped 24-hex outside the synthetic
convention, e-mails outside reserved test domains, private-content
markers) so no real value is ever written into a denylist.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanitize_fixture import scan_text

REPO = Path(__file__).resolve().parent.parent

SKIP_SUFFIXES = (".png", ".jpg", ".gif", ".ico", ".woff", ".woff2", ".lock")
SKIP_PATHS = ("uv.lock", "app/package-lock.json")


def tracked_files(changed_only: bool) -> list[str]:
    if changed_only:
        out = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    else:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--changed", action="store_true")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    findings: list[str] = []
    scanned = 0
    for rel in tracked_files(changed_only=args.changed):
        if rel in SKIP_PATHS or rel.endswith(SKIP_SUFFIXES):
            continue
        path = REPO / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: nothing text-shaped to leak
        scanned += 1
        findings.extend(scan_text(text, rel))

    if findings:
        for finding in findings:
            print(f"FAIL: {finding}")
        return 1
    print(f"OK: no secret-shaped content in {scanned} tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
