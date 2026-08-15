import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import check_generated_boundaries as boundaries
import check_status as status

OWNERSHIP = json.loads((REPO / "contracts" / "generated-ownership.json").read_text())


def test_manual_edit_under_generated_path_is_rejected() -> None:
    bad = boundaries.violations(["src/pumble_keys/sdk.py"], OWNERSHIP)
    assert bad == ["src/pumble_keys/sdk.py"]


def test_handwritten_paths_are_allowed() -> None:
    paths = [
        "src/pumble_keys/extensions/resolve.py",
        "src/pumble_keys/mcp_server/server.py",
        "tests/unit/test_resolve.py",
        "README.md",
    ]
    assert boundaries.violations(paths, OWNERSHIP) == []


def _rows(states: list[str]) -> list[tuple[str, str]]:
    return [(f"P{i:02d}", state) for i, state in enumerate(states)]


def test_current_status_file_is_valid() -> None:
    rows = status.parse_rows((REPO / "IMPLEMENTATION_STATUS.md").read_text())
    assert status.check(rows) == []


def test_skipped_packet_is_rejected() -> None:
    states = ["DONE", "NOT_STARTED", "DONE"] + ["NOT_STARTED"] * 43
    errors = status.check(_rows(states))
    assert any("skipped" in error for error in errors)


def test_duplicate_in_progress_is_rejected() -> None:
    states = ["IN_PROGRESS", "IN_PROGRESS"] + ["NOT_STARTED"] * 44
    errors = status.check(_rows(states))
    assert any("IN_PROGRESS" in error for error in errors)


def test_invalid_status_is_rejected() -> None:
    states = ["WIP"] + ["NOT_STARTED"] * 45
    errors = status.check(_rows(states))
    assert any("invalid status" in error for error in errors)
