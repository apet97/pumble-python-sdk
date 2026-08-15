"""P26: MCP CLI — parsing, defaults, secret-flag rejection, exit codes."""

from __future__ import annotations

import pytest

from pumble_keys.mcp_server.cli import main

KEY = "test-key-not-real"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.setenv("PUMBLE_API_KEY", KEY)
    monkeypatch.delenv("PUMBLE_MCP_TOKEN_VERIFIER", raising=False)
    monkeypatch.delenv("PUMBLE_MCP_PROFILE", raising=False)


class RunnerRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, server, **kwargs) -> None:
        self.calls.append((server, kwargs))


def test_default_is_stdio(capsys) -> None:
    runner = RunnerRecorder()
    assert main([], runner=runner) == 0
    _server, kwargs = runner.calls[0]
    assert kwargs == {"transport": "stdio"}


def test_streamable_http_defaults(capsys) -> None:
    runner = RunnerRecorder()
    assert main(["--transport", "streamable-http"], runner=runner) == 0
    _server, kwargs = runner.calls[0]
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 2718
    assert kwargs["streamable_http_path"] == "/mcp"
    assert kwargs["stateless_http"] is True


def test_sse_rejected_with_exit_1(capsys) -> None:
    runner = RunnerRecorder()
    assert main(["--transport", "sse"], runner=runner) == 1
    assert "SSE" in capsys.readouterr().err
    assert runner.calls == []


def test_nonloopback_without_auth_exit_1(capsys) -> None:
    runner = RunnerRecorder()
    code = main(["--transport", "streamable-http", "--host", "0.0.0.0"], runner=runner)
    assert code == 1
    assert "token verifier" in capsys.readouterr().err


def test_unsafe_no_auth_allows_but_warns(capsys) -> None:
    runner = RunnerRecorder()
    code = main(
        [
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--unsafe-no-auth",
        ],
        runner=runner,
    )
    assert code == 0
    assert "WARNING" in capsys.readouterr().err
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "flag", ["--api-key", "--api-key-auth=x", "--confirmation-secret"]
)
def test_secret_bearing_flags_rejected(flag, capsys) -> None:
    runner = RunnerRecorder()
    code = main([flag, "value"] if "=" not in flag else [flag], runner=runner)
    assert code == 2
    assert "never argv" in capsys.readouterr().err
    assert runner.calls == []


def test_profile_and_gates_flow_into_config(tmp_path, capsys) -> None:
    runner = RunnerRecorder()
    audit = tmp_path / "audit.jsonl"
    code = main(
        [
            "--profile",
            "readwrite",
            "--allow-raw-writes",
            "--audit-log",
            str(audit),
        ],
        runner=runner,
    )
    assert code == 0

    # readwrite without gates fails at config validation → exit 1.
    code = main(["--profile", "readwrite"], runner=RunnerRecorder())
    assert code == 1
    assert "allow_raw_writes" in capsys.readouterr().err


def test_missing_api_key_exit_1(monkeypatch, capsys) -> None:
    monkeypatch.delenv("PUMBLE_API_KEY", raising=False)
    code = main([], runner=RunnerRecorder())
    assert code == 1
    assert "api_key" in capsys.readouterr().err


def test_token_verifier_env_wiring(monkeypatch) -> None:
    monkeypatch.setenv(
        "PUMBLE_MCP_TOKEN_VERIFIER",
        "pumble_keys.mcp_server.auth:StaticTokenVerifier",
    )
    runner = RunnerRecorder()
    args = [
        "--transport",
        "streamable-http",
        "--host",
        "0.0.0.0",
        "--auth-issuer",
        "https://issuer.example.invalid",
        "--auth-resource-url",
        "https://mcp.example.invalid/mcp",
    ]
    assert main(args, runner=runner) == 0  # auth configured → allowed
    assert len(runner.calls) == 1

    # verifier without the metadata flags is a usage error
    assert main(["--transport", "streamable-http"], runner=RunnerRecorder()) == 2


def test_unknown_flag_is_usage_error(capsys) -> None:
    assert main(["--banana"], runner=RunnerRecorder()) == 2
