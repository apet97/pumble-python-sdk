"""P39: packaged app asset — manifest binding and freshness gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_app import ASSET_HTML, MANIFEST, check, source_hash

REPO = Path(__file__).resolve().parents[2]


def read_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_manifest_binds_the_packaged_asset() -> None:
    manifest = read_manifest()
    asset_sha = hashlib.sha256(ASSET_HTML.read_bytes()).hexdigest()
    assert manifest["asset"] == "index.html"
    assert manifest["asset_sha256"] == asset_sha
    assert manifest["source_sha256"] == source_hash()


def test_check_passes_on_a_fresh_tree() -> None:
    assert check() == 0


def test_check_fails_when_the_asset_is_stale(tmp_path, monkeypatch) -> None:
    from tools import build_app

    tampered = tmp_path / "index.html"
    tampered.write_bytes(ASSET_HTML.read_bytes() + b"<!-- drift -->")
    monkeypatch.setattr(build_app, "ASSET_HTML", tampered)
    assert build_app.check() == 1


def test_check_fails_when_source_changed_without_rebuild(monkeypatch) -> None:
    from tools import build_app

    monkeypatch.setattr(build_app, "source_hash", lambda: "0" * 64)
    assert build_app.check() == 1


def test_resource_serves_exactly_the_packaged_bytes() -> None:
    from pumble_keys.mcp_server.app import load_app_html

    assert load_app_html().encode() == ASSET_HTML.read_bytes()
