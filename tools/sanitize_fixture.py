#!/usr/bin/env python3
"""Fixture sanitizer: prove the replay corpus contains no live data.

The scanner detects secrets by SHAPE, never by a denylist of the real
values (a denylist would itself commit them):

- 32-hex strings — Pumble API-key shaped;
- 24-hex strings that do not follow the synthetic convention (at least
  twelve leading zeros) — live workspace/user/channel/message IDs;
- e-mail addresses outside the reserved test domains;
- the explicit private-content markers (bracketed "private" tag and
  the do-not-commit tag) used to mark text that must never land.

Usage:

    uv run python tools/sanitize_fixture.py --check   # gate mode
    uv run python tools/sanitize_fixture.py FILE...   # scan given files
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = ("fixtures", "tests/parity")

# pumble.com appears in the vendor's own OpenAPI contact examples.
ALLOWED_EMAIL_DOMAINS = (
    "example.invalid",
    "example.com",
    "pumble.invalid",
    "pumble.com",
)

HEX32 = re.compile(r"\b[0-9a-f]{32}\b", re.IGNORECASE)
HEX24 = re.compile(r"\b[0-9a-f]{24}\b", re.IGNORECASE)
EMAIL = re.compile(r"\b[\w.+-]+@([\w-]+\.[\w.-]+)\b")
# Assembled so this file stays clean under its own repo-wide scan.
PRIVATE_MARKERS = ("[pri" + "vate]", "DO-NOT" + "-COMMIT")
SYNTHETIC_PREFIX = "0" * 12


def _is_synthetic_id(value: str) -> bool:
    """Obviously-synthetic 24-hex shapes; anything else is suspect.

    Accepted conventions (real Mongo-style IDs start with a timestamp
    and match none of these): twelve leading zeros; one character
    repeated for the first twenty positions (aaaa…0001); a short block
    cycled through the whole value (abcdef×4); the ascending
    0123456789abcdef sequence; adjacent identical pairs (bbccdd…).
    """
    lowered = value.lower()
    if lowered.startswith(SYNTHETIC_PREFIX):
        return True
    if lowered[:20] == lowered[0] * 20:
        return True
    for size in (1, 2, 3, 4, 6, 8, 12):
        block = lowered[:size]
        if block * (24 // size) == lowered:
            return True
    if lowered in "0123456789abcdef" * 3:
        return True
    return all(lowered[i] == lowered[i + 1] for i in range(0, 24, 2))


def scan_text(text: str, origin: str) -> list[str]:
    findings: list[str] = []
    for match in HEX32.finditer(text):
        if set(match.group(0)) != {"0"}:
            findings.append(f"{origin}: API-key-shaped 32-hex string")
    for match in HEX24.finditer(text):
        value = match.group(0)
        if not _is_synthetic_id(value):
            findings.append(f"{origin}: live-ID-shaped 24-hex string {value[:4]}…")
    for match in EMAIL.finditer(text):
        domain = match.group(1).lower()
        if domain not in ALLOWED_EMAIL_DOMAINS:
            findings.append(f"{origin}: e-mail outside reserved domains ({domain})")
    for marker in PRIVATE_MARKERS:
        if marker in text:
            findings.append(f"{origin}: private-content marker {marker!r}")
    return findings


def scan_paths(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        files = (
            sorted(p for p in path.rglob("*") if p.is_file())
            if path.is_dir()
            else [path]
        )
        for file in files:
            if file.suffix in (".pyc",) or "__pycache__" in file.parts:
                continue
            try:
                text = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                findings.append(f"{file}: unreadable as UTF-8 text")
                continue
            try:
                origin = str(file.relative_to(REPO))
            except ValueError:
                origin = str(file)
            findings.extend(scan_text(text, origin))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check or not args.files:
        targets = [REPO / target for target in DEFAULT_TARGETS]
        targets = [target for target in targets if target.exists()]
    else:
        targets = [Path(file) for file in args.files]

    findings = scan_paths(targets)
    if findings:
        for finding in findings:
            print(f"FAIL: {finding}")
        return 1
    print(f"OK: no live data in {len(targets)} target(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
