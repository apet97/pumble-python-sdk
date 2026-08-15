"""P40: the fixture sanitizer is a mandatory offline gate."""

from __future__ import annotations

from pathlib import Path

from tools.sanitize_fixture import scan_paths, scan_text

# Dirty literals are assembled at runtime so this file itself stays
# clean under the scanner (which also walks tests/parity).
API_KEY_SHAPED = "abc123" + "d" * 26
LIVE_ID_SHAPED = "64ad13" + "0" * 18
PRIVATE_MARKER = "[pri" + "vate]"


def test_detects_api_key_shaped_strings() -> None:
    assert scan_text(f"key={API_KEY_SHAPED}", "case")
    assert not scan_text("key=" + "0" * 32, "case")  # all-zero synthetic


def test_detects_live_object_ids_but_not_synthetic_ones() -> None:
    assert scan_text(f"id={LIVE_ID_SHAPED}", "case")
    assert not scan_text("id=" + "0" * 20 + "0001", "case")


def test_detects_emails_outside_reserved_domains() -> None:
    assert scan_text("mail: someone@" + "gmail.com", "case")
    assert not scan_text("mail: probe@example.invalid", "case")


def test_detects_private_content_markers() -> None:
    assert scan_text(f"text: {PRIVATE_MARKER} secret", "case")


def test_scan_paths_flags_a_dirty_fixture(tmp_path: Path) -> None:
    dirty = tmp_path / "dirty.json"
    dirty.write_text(f'{{"apiKey": "{API_KEY_SHAPED}"}}')
    assert scan_paths([dirty])


def test_committed_corpus_is_clean() -> None:
    repo = Path(__file__).resolve().parents[2]
    findings = scan_paths([repo / "fixtures", repo / "tests" / "parity"])
    assert findings == []
