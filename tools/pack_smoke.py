#!/usr/bin/env python3
"""Package hardening gate: build, inspect, fresh-install, smoke.

    uv run python tools/pack_smoke.py

Steps:

1. `tools/build_app.py --check` — the packaged App asset is fresh.
2. `uv build` into a temp dist directory (sdist + wheel).
3. `twine check` on both artifacts.
4. Wheel content allowlist: only `pumble_keys/` + `*.dist-info/`
   entries; required assets present; tests/fixtures/secrets/dev files
   rejected.
5. Fresh venv install (isolated, cwd outside the repo) and smoke:
   raw SDK import, façade client, PumbleApp, CLI help, MCP tool list,
   packaged App resource read.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

REQUIRED_WHEEL_FILES = (
    "pumble_keys/py.typed",
    "pumble_keys/knowledge/index.md",
    "pumble_keys/knowledge/guides/safe-writes.md",
    "pumble_keys/knowledge/guides/search-tips.md",
    "pumble_keys/mcp_server/app_assets/index.html",
    "pumble_keys/mcp_server/app_assets/manifest.json",
)

FORBIDDEN_MARKERS = (
    "tests/",
    "fixtures/",
    "node_modules",
    ".map",
    ".env",
    "conftest",
    ".speakeasy",
    "gen.yaml",
    "live_receipt",
)

SMOKE_SCRIPT = """
import asyncio
import subprocess
import sys

import pumble_keys  # generated raw SDK
from pumble_keys import PumbleSDK
from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.pumble_app.app import PumbleApp

client = create_pumble_client("smoke-key-not-real")
asyncio.run(client.aclose())
PumbleApp(signing_secret="smoke-secret-not-real")

from pathlib import Path

scripts_dir = Path(sys.executable).parent
for command in ("pumble-keys", "pumble-keys-mcp"):
    result = subprocess.run(
        [str(scripts_dir / command), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (command, result.stderr[:400])

from pumble_keys.mcp_server.app import load_app_html
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.server import create_server

html = load_app_html()
assert html.lstrip().lower().startswith("<!doctype html"), "app asset"

server = create_server(McpConfig(api_key="smoke-key-not-real"))
tools = asyncio.run(server.list_tools())
names = [tool.name for tool in tools]
assert "whoami" in names and "open_pumble_workspace" in names, names
print("SMOKE_OK", len(names), "tools")
"""


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def check_wheel(wheel: Path) -> int:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    for name in names:
        top = name.split("/", 1)[0]
        if top != "pumble_keys" and not top.endswith(".dist-info"):
            return fail(f"unexpected top-level wheel entry: {name}")
        lowered = name.lower()
        for marker in FORBIDDEN_MARKERS:
            if marker in lowered:
                return fail(f"forbidden wheel entry: {name}")
    for required in REQUIRED_WHEEL_FILES:
        if required not in names:
            return fail(f"required wheel file missing: {required}")
    print(f"OK: wheel contents clean ({len(names)} entries).")
    return 0


def main() -> int:
    if (
        subprocess.run(
            [sys.executable, str(REPO / "tools" / "build_app.py"), "--check"],
            cwd=REPO,
            check=False,
        ).returncode
        != 0
    ):
        return fail("app asset stale; run tools/build_app.py")

    with tempfile.TemporaryDirectory(prefix="pumble-pack-") as tmp:
        dist = Path(tmp) / "dist"
        if (
            subprocess.run(
                ["uv", "build", "--out-dir", str(dist)], cwd=REPO, check=False
            ).returncode
            != 0
        ):
            return fail("uv build failed")
        # uv drops a .gitignore into the out dir; keep artifacts only.
        artifacts = [
            p
            for p in sorted(dist.iterdir())
            if p.suffix == ".whl" or p.name.endswith(".tar.gz")
        ]
        wheels = [p for p in artifacts if p.suffix == ".whl"]
        sdists = [p for p in artifacts if p.name.endswith(".tar.gz")]
        if len(wheels) != 1 or len(sdists) != 1:
            return fail(f"expected one wheel and one sdist, got {artifacts}")

        if (
            subprocess.run(
                ["uv", "run", "twine", "check", *map(str, artifacts)],
                cwd=REPO,
                check=False,
            ).returncode
            != 0
        ):
            return fail("twine check failed")

        if check_wheel(wheels[0]) != 0:
            return 1

        env_dir = Path(tmp) / "venv"
        if (
            subprocess.run(
                ["uv", "venv", "--quiet", str(env_dir)], cwd=tmp, check=False
            ).returncode
            != 0
        ):
            return fail("venv creation failed")
        python = env_dir / "bin" / "python"
        if (
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--quiet",
                    "--python",
                    str(python),
                    str(wheels[0]),
                ],
                cwd=tmp,
                check=False,
            ).returncode
            != 0
        ):
            return fail("wheel install failed")

        script = Path(tmp) / "smoke.py"
        script.write_text(SMOKE_SCRIPT)
        # -I: isolated mode; cwd=tmp: no repository path leakage.
        smoke = subprocess.run([str(python), "-I", str(script)], cwd=tmp, check=False)
        if smoke.returncode != 0:
            return fail("fresh-environment smoke failed")

    print("OK: package smoke passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
