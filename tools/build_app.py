#!/usr/bin/env python3
"""Build the MCP App and package the single HTML with a hash manifest.

Pipeline (run before the Python wheel build):

    uv run python tools/build_app.py            # build + copy + manifest
    uv run python tools/build_app.py --check    # verify freshness only

The manifest (`app_assets/manifest.json`) records the sha256 of the
packaged HTML and of the app source tree (`app/src`, `app/index.html`,
`app/package.json`, `app/package-lock.json`, `app/vite.config.ts`,
`app/tsconfig.json`). `--check` fails when the source changed but the
asset was not rebuilt, or when the packaged HTML does not match its
recorded hash — the P43 package gate runs it so a stale asset cannot
ship.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "app"
DIST_HTML = APP / "dist" / "index.html"
ASSETS = REPO / "src" / "pumble_keys" / "mcp_server" / "app_assets"
ASSET_HTML = ASSETS / "index.html"
MANIFEST = ASSETS / "manifest.json"

SOURCE_FILES = (
    "index.html",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "vite.config.ts",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_hash() -> str:
    """Deterministic hash over every app source input, path-labeled."""
    digest = hashlib.sha256()
    paths = [APP / name for name in SOURCE_FILES]
    paths.extend(sorted((APP / "src").rglob("*")))
    for path in paths:
        if not path.is_file():
            continue
        rel = path.relative_to(APP).as_posix()
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build() -> int:
    subprocess.run(["npm", "run", "build"], cwd=APP, check=True, capture_output=True)
    html = DIST_HTML.read_bytes()
    ASSET_HTML.write_bytes(html)
    MANIFEST.write_text(
        json.dumps(
            {
                "asset": "index.html",
                "asset_sha256": sha256_bytes(html),
                "source_sha256": source_hash(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"OK: packaged app asset {sha256_bytes(html)[:12]}… with manifest.")
    return 0


def check() -> int:
    if not MANIFEST.exists() or not ASSET_HTML.exists():
        print("FAIL: app asset or manifest missing; run tools/build_app.py")
        return 1
    manifest = json.loads(MANIFEST.read_text())
    asset_sha = sha256_bytes(ASSET_HTML.read_bytes())
    if asset_sha != manifest.get("asset_sha256"):
        print("FAIL: packaged index.html does not match manifest asset_sha256")
        return 1
    if source_hash() != manifest.get("source_sha256"):
        print(
            "FAIL: app source changed after the last build; "
            "run tools/build_app.py to rebuild the packaged asset"
        )
        return 1
    print("OK: packaged app asset is fresh.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    sys.exit(main())
