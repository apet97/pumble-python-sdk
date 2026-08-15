#!/usr/bin/env python3
"""Documented idempotent patch for proven generator gaps in `pyproject.toml`.

Run after every `speakeasy run --pinned`, then `uv lock`. The patch is a
no-op on already-patched output. Each entry is documented in
`docs/GENERATOR_DEVIATIONS.md` with its failing test and deletion
condition. Do not add entries for anything expressible in the OpenAPI,
an overlay, or `.speakeasy/gen.yaml`.

Patched gaps (pinned Speakeasy 1.763.6):

1. `requires-python`: the generator hardcodes `>=3.10`; the project
   contract is `>=3.11,<3.15`. No generator key exists.
2. `[project.scripts]`: the Python generator has no console-script key
   and silently drops one; the project ships `pumble-keys` and
   `pumble-keys-mcp`.
3. `[tool.setuptools.package-data]`: the generator emits only
   `py.typed`; the wheel must also carry the packaged knowledge base
   and the built MCP App asset (+ hash manifest).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYPROJECT = REPO / "pyproject.toml"

REQUIRES_GENERATED = 'requires-python = ">=3.10"'
REQUIRES_PATCHED = 'requires-python = ">=3.11,<3.15"'

SCRIPTS_BLOCK = """[project.scripts]
pumble-keys = "pumble_keys.cli.main:main"
pumble-keys-mcp = "pumble_keys.mcp_server.cli:main"
"""

PACKAGE_DATA_GENERATED = """[tool.setuptools.package-data]
"*" = ["py.typed"]"""
PACKAGE_DATA_PATCHED = """[tool.setuptools.package-data]
"*" = ["py.typed"]
"pumble_keys.knowledge" = ["*.md", "guides/*.md"]
"pumble_keys.mcp_server.app_assets" = ["*.html", "*.json"]"""


def patch_text(text: str) -> str:
    """Return the patched pyproject text. Pure and idempotent."""
    text = text.replace(REQUIRES_GENERATED, REQUIRES_PATCHED)
    if "[project.scripts]" not in text:
        anchor = "[dependency-groups]"
        if anchor not in text:
            raise SystemExit(
                "FAIL: pyproject.toml has no [dependency-groups] anchor; "
                "the generator layout changed — update tools/patch_generated.py"
            )
        text = text.replace(anchor, SCRIPTS_BLOCK + "\n" + anchor, 1)
    if '"pumble_keys.knowledge"' not in text:
        if PACKAGE_DATA_GENERATED not in text:
            raise SystemExit(
                "FAIL: pyproject.toml package-data block changed shape — "
                "update tools/patch_generated.py"
            )
        text = text.replace(PACKAGE_DATA_GENERATED, PACKAGE_DATA_PATCHED, 1)
    return text


def main() -> int:
    before = PYPROJECT.read_text()
    after = patch_text(before)
    if after == before:
        print("OK: pyproject.toml already patched (no-op).")
        return 0
    PYPROJECT.write_text(after)
    print("OK: patched pyproject.toml. Run `uv lock` to refresh the lock file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
