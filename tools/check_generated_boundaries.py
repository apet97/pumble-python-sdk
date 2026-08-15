#!/usr/bin/env python3
"""Reject manual edits to generator-owned files.

Compares changed Git paths (staged and unstaged) against
`contracts/generated-ownership.json`. A change under a generated pattern
fails unless it also matches a hand-written exception or the run is an
intentional generator run (`--generator-run`).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OWNERSHIP = REPO / "contracts" / "generated-ownership.json"


def _matches(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        # `a/**` must also match `a/b` one level deep and `a` itself.
        base = pattern.removesuffix("/**")
        if base != pattern and (path == base or path.startswith(base + "/")):
            return True
    return False


def violations(changed: list[str], ownership: dict) -> list[str]:
    generated = ownership["generated_patterns"]
    exceptions = ownership["handwritten_exceptions"]
    return [
        path
        for path in changed
        if _matches(path, generated) and not _matches(path, exceptions)
    ]


def changed_paths() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generator-run",
        action="store_true",
        help="allow generated-path changes for an intentional generator run",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        help="check these paths instead of the Git diff (for tests)",
    )
    args = parser.parse_args()

    ownership = json.loads(OWNERSHIP.read_text())
    changed = args.paths if args.paths is not None else changed_paths()

    if args.generator_run:
        print("generator run: generated-path changes allowed")
        return 0

    bad = violations(changed, ownership)
    if bad:
        print(
            "manual edit under generated ownership:\n  " + "\n  ".join(bad),
            file=sys.stderr,
        )
        print(
            "Fix the OpenAPI, overlay, or generator config and regenerate "
            "with --generator-run.",
            file=sys.stderr,
        )
        return 1
    print(f"generated boundaries OK ({len(changed)} changed paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
