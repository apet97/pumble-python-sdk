"""P24: quiet mode — suppresses success prose, never JSON or errors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cli import CHANNEL_ID, run_cli


def test_quiet_suppresses_write_success_prose(capsys) -> None:
    code, out, err, _ = run_cli(["--quiet", "send", CHANNEL_ID, "hi"], capsys)
    assert code == 0
    assert out == ""
    assert err == ""


def test_quiet_does_not_suppress_json(capsys) -> None:
    code, out, _err, _ = run_cli(
        ["--quiet", "--json", "send", CHANNEL_ID, "hi"], capsys
    )
    assert code == 0
    receipt = json.loads(out)
    assert receipt["ok"] is True
    assert receipt["ids"]["channel_id"] == CHANNEL_ID


def test_quiet_does_not_suppress_errors(capsys) -> None:
    code, _out, err, _ = run_cli(
        ["--quiet", "channels", "find", "ghost-channel"], capsys
    )
    assert code == 1
    assert "not found" in err


def test_quiet_does_not_suppress_read_output(capsys) -> None:
    code, out, _err, _ = run_cli(["--quiet", "whoami"], capsys)
    assert code == 0
    assert out != ""
