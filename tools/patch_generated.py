#!/usr/bin/env python3
"""Documented idempotent patches for proven generator gaps.

Run after every `speakeasy run --pinned`, then `uv lock`. Every patch is
a no-op on already-patched output. Each entry is documented in
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
4. `[project.urls]` + `classifiers`: no generator key at the pinned
   version; PyPI needs repository/issue links and trove classifiers.
5. README installation section: `speakeasy run` renders the
   unpublished `git+<UNSET>.git` install variant plus a stale
   "run your first generation action" tip; the package is published
   to PyPI as `pumble_keys_sdk` by `.github/workflows/release.yml`.
6. `scripts/publish.sh`: generator boilerplate that publishes with a
   plaintext `$PYPI_TOKEN`, contradicting the trusted-publishing
   release path. Deleted on every run.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYPROJECT = REPO / "pyproject.toml"
README = REPO / "README.md"
PUBLISH_SH = REPO / "scripts" / "publish.sh"

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

LICENSE_LINE = 'license = { text = "MIT" }'
METADATA_BLOCK = """classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Typing :: Typed",
]

[project.urls]
Homepage = "https://github.com/apet97/pumble-python-sdk"
Repository = "https://github.com/apet97/pumble-python-sdk"
Issues = "https://github.com/apet97/pumble-python-sdk/issues"
Changelog = "https://github.com/apet97/pumble-python-sdk/blob/main/CHANGELOG.md"
"""

README_TIP = """> [!TIP]
> To finish publishing your SDK to PyPI you must [run your first generation action](https://www.speakeasy.com/docs/github-setup#step-by-step-guide).


"""
README_INSTALL_REPLACEMENTS = (
    ("uv add git+<UNSET>.git", "uv add pumble_keys_sdk"),
    ("pip install git+<UNSET>.git", "pip install pumble_keys_sdk"),
    ("poetry add git+<UNSET>.git", "poetry add pumble_keys_sdk"),
)


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
    if "[project.urls]" not in text:
        if LICENSE_LINE not in text:
            raise SystemExit(
                "FAIL: pyproject.toml license line changed shape — "
                "update tools/patch_generated.py"
            )
        text = text.replace(LICENSE_LINE, LICENSE_LINE + "\n" + METADATA_BLOCK, 1)
    return text


def patch_readme_text(text: str) -> str:
    """Return the patched README text. Pure and idempotent."""
    text = text.replace(README_TIP, "")
    for generated, patched in README_INSTALL_REPLACEMENTS:
        text = text.replace(generated, patched)
    if "<UNSET>" in text:
        raise SystemExit(
            "FAIL: README.md still contains <UNSET> after patching — "
            "the generator install section changed shape; update "
            "tools/patch_generated.py"
        )
    return text


def _apply(path: Path, patch: Callable[[str], str]) -> bool:
    before = path.read_text()
    after = patch(before)
    if after == before:
        return False
    path.write_text(after)
    return True


def main() -> int:
    changed = []
    if _apply(PYPROJECT, patch_text):
        changed.append("pyproject.toml (run `uv lock` to refresh the lock file)")
    if _apply(README, patch_readme_text):
        changed.append("README.md")
    if PUBLISH_SH.exists():
        PUBLISH_SH.unlink()
        if PUBLISH_SH.parent.exists() and not any(PUBLISH_SH.parent.iterdir()):
            PUBLISH_SH.parent.rmdir()
        changed.append("scripts/publish.sh (deleted)")
    if not changed:
        print("OK: all patch targets already patched (no-op).")
    else:
        print("OK: patched " + "; ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
