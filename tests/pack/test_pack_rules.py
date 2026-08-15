"""P43: wheel allowlist rules and the pyproject package-data patch."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tools.pack_smoke import REQUIRED_WHEEL_FILES, check_wheel
from tools.patch_generated import patch_text


def make_wheel(tmp_path: Path, names: list[str]) -> Path:
    wheel = tmp_path / "pkg-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name in names:
            archive.writestr(name, "x")
    return wheel


GOOD = [
    *REQUIRED_WHEEL_FILES,
    "pumble_keys/__init__.py",
    "pumble_keys_sdk-0.1.0.dist-info/METADATA",
]


def test_clean_wheel_passes(tmp_path: Path) -> None:
    assert check_wheel(make_wheel(tmp_path, GOOD)) == 0


def test_missing_required_asset_fails(tmp_path: Path) -> None:
    names = [n for n in GOOD if "app_assets/index.html" not in n]
    assert check_wheel(make_wheel(tmp_path, names)) == 1


def test_forbidden_entries_fail(tmp_path: Path) -> None:
    for bad in (
        "pumble_keys/tests/test_x.py",
        "pumble_keys/fixtures/replay.json",
        "pumble_keys/app/node_modules/x.js",
        "pumble_keys/static/app.js.map",
        "pumble_keys/.env",
        "pumble_keys/conftest.py",
    ):
        assert check_wheel(make_wheel(tmp_path, [*GOOD, bad])) == 1, bad


def test_unexpected_top_level_fails(tmp_path: Path) -> None:
    assert check_wheel(make_wheel(tmp_path, [*GOOD, "tests/leak.py"])) == 1


def test_package_data_patch_is_idempotent() -> None:
    generated = (
        'requires-python = ">=3.10"\n'
        'license = { text = "MIT" }\n'
        "[dependency-groups]\n"
        "[tool.setuptools.package-data]\n"
        '"*" = ["py.typed"]\n'
    )
    once = patch_text(generated)
    assert '"pumble_keys.knowledge"' in once
    assert '"pumble_keys.mcp_server.app_assets"' in once
    assert "[project.urls]" in once
    assert patch_text(once) == once
