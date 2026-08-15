"""P44: workflow files stay valid, pinned, and complete."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"

USES = re.compile(r"uses:\s*(\S+)")
SHA_PINNED = re.compile(r"@[0-9a-f]{40}$")


def workflow_texts() -> dict[str, str]:
    files = sorted(WORKFLOWS.glob("*.yml"))
    assert [f.name for f in files] == ["ci.yml", "live.yml", "release.yml"]
    return {f.name: f.read_text() for f in files}


def test_workflows_parse() -> None:
    for name, text in workflow_texts().items():
        data = yaml.safe_load(text)
        assert data and "jobs" in data, name
    assert yaml.safe_load((REPO / ".github" / "dependabot.yml").read_text())


def test_every_action_is_sha_pinned() -> None:
    for name, text in workflow_texts().items():
        references = USES.findall(text)
        assert references, name
        for reference in references:
            assert SHA_PINNED.search(reference), f"{name}: {reference}"


def test_ci_covers_the_mandated_gates() -> None:
    ci = workflow_texts()["ci.yml"]
    for required in (
        '"3.11"',
        '"3.14"',
        "ruff",
        "mypy",
        "pytest",
        "sanitize_fixture.py --check",
        "scan_secrets.py --all",
        "check_generated_boundaries.py",
        "pack_smoke.py",
        "pip-audit",
        "npm ci --prefix app",
    ):
        assert required in ci, required


def test_live_workflow_is_gated_and_guarded() -> None:
    live = workflow_texts()["live.yml"]
    assert "workflow_dispatch" in live and "schedule" in live
    assert "environment: sacrificial-workspace" in live
    assert "PUMBLE_LIVE" in live and "secrets.PUMBLE_API_KEY" in live


def test_release_workflow_verifies_before_trusted_publishing() -> None:
    release = workflow_texts()["release.yml"]
    assert "merge-base --is-ancestor" in release  # reviewed-commit gate
    assert "Version consistency" in release
    assert "environment: pypi" in release
    assert "id-token: write" in release  # trusted publishing (OIDC)
    assert "attestations: true" in release  # provenance
    assert "password" not in release  # no long-lived API tokens


def test_no_floating_tool_versions() -> None:
    for name, text in workflow_texts().items():
        assert 'node-version: "22.12.0"' in text or "setup-node" not in text, name
        assert "@latest" not in text, name
