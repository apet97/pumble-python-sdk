"""P05 evidence: the generated `pyproject.toml` matches the project contract.

The pinned generator owns `pyproject.toml`. Three project requirements
have no generator configuration key and are applied by the documented
idempotent patch (`tools/patch_generated.py`). These tests fail on
unpatched generator output, so a regeneration that skips the patch
cannot land silently.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "tools"))


def _pyproject() -> dict:
    return tomllib.loads((REPO / "pyproject.toml").read_text())


def test_requires_python_matches_project_contract() -> None:
    assert _pyproject()["project"]["requires-python"] == ">=3.11,<3.15"


def test_console_scripts_are_declared() -> None:
    scripts = _pyproject()["project"].get("scripts", {})
    assert scripts == {
        "pumble-keys": "pumble_keys.cli.main:main",
        "pumble-keys-mcp": "pumble_keys.mcp_server.cli:main",
    }


def test_dev_group_contains_release_tooling() -> None:
    dev = _pyproject()["dependency-groups"]["dev"]
    names = {spec.split(" ")[0].split(">=")[0].split("==")[0] for spec in dev}
    for tool in ("mypy", "build", "twine", "pip-audit"):
        assert tool in names, f"missing dev tool: {tool}"


def test_patch_script_is_idempotent() -> None:
    import patch_generated

    before = (REPO / "pyproject.toml").read_text()
    changed = patch_generated.patch_text(before)
    assert patch_generated.patch_text(changed) == changed


def test_committed_pyproject_is_already_patched() -> None:
    import patch_generated

    committed = (REPO / "pyproject.toml").read_text()
    assert patch_generated.patch_text(committed) == committed
