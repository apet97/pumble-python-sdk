import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import check_generated_boundaries as boundaries

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
