"""P24: CLI — every command happy path and usage failure, exit codes, JSON."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from types import SimpleNamespace

from pumble_keys.cli.main import main
from pumble_keys.extensions.client import create_pumble_client

CHANNEL_ID = "0" * 20 + "0001"
USER_ID = "0" * 20 + "0002"
MESSAGE_ID = "0" * 20 + "0003"
SCHEDULED_ID = "0" * 20 + "0004"
KEY = "test-key-not-real-cdc8"


class Recorder:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.value


def fake_user():
    return SimpleNamespace(id=USER_ID, name="User 1", email="user-1@example.invalid")


def fake_channel():
    return SimpleNamespace(id=CHANNEL_ID, name="engineering", channel_type="PUBLIC")


def fake_message(mid=MESSAGE_ID):
    return SimpleNamespace(
        id=mid,
        channel_id=CHANNEL_ID,
        author=USER_ID,
        text="[redacted] text",
        timestamp=datetime(2026, 8, 15, tzinfo=UTC),
        timestamp_milli=1_786_752_000_000,
        thread_root_info=None,
    )


def fake_scheduled():
    return SimpleNamespace(
        id=SCHEDULED_ID,
        channel_id=CHANNEL_ID,
        send_at=1_786_752_000_000,
        text="[redacted] later",
    )


def make_raw(**overrides):
    r = {
        "my_info": Recorder(fake_user()),
        "list_users": Recorder([fake_user()]),
        "list_channels": Recorder([SimpleNamespace(channel=fake_channel())]),
        "create_channel": Recorder(SimpleNamespace(id=CHANNEL_ID, name="fresh")),
        "get_channel": Recorder(SimpleNamespace(channel=fake_channel())),
        "send_message": Recorder(SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)),
        "dm_user": Recorder(SimpleNamespace(id=MESSAGE_ID, channel_id=CHANNEL_ID)),
        "fetch_message": Recorder(fake_message()),
        "fetch_thread_replies": Recorder(SimpleNamespace(result=[fake_message("r1")])),
        "search_messages": Recorder(
            SimpleNamespace(
                result=SimpleNamespace(content=[fake_message()], has_more=False)
            )
        ),
        "list_messages": Recorder(
            SimpleNamespace(result=SimpleNamespace(messages=[fake_message()]))
        ),
        "custom_status": Recorder({"ok": True}),
        "create_scheduled": Recorder(fake_scheduled()),
        "fetch_scheduled_messages": Recorder(
            SimpleNamespace(
                result=SimpleNamespace(scheduled_messages=[fake_scheduled()])
            )
        ),
        "fetch_scheduled_message": Recorder(fake_scheduled()),
        "delete_scheduled": Recorder(None),
    }
    r.update(overrides)
    return SimpleNamespace(
        users=SimpleNamespace(
            my_info_async=r["my_info"],
            list_users_async=r["list_users"],
            list_user_groups_async=Recorder([]),
            custom_status_async=r["custom_status"],
        ),
        channels=SimpleNamespace(
            list_channels_async=r["list_channels"],
            get_channel_async=r["get_channel"],
            create_channel_async=r["create_channel"],
        ),
        messages=SimpleNamespace(
            send_message_async=r["send_message"],
            dm_user_async=r["dm_user"],
            dm_group_async=Recorder(None),
            send_reply_async=Recorder(None),
            fetch_message_async=r["fetch_message"],
            fetch_thread_replies_async=r["fetch_thread_replies"],
            search_messages_async=r["search_messages"],
            list_messages_async=r["list_messages"],
        ),
        scheduled_messages=SimpleNamespace(
            create_scheduled_message_async=r["create_scheduled"],
            fetch_scheduled_messages_async=r["fetch_scheduled_messages"],
            fetch_scheduled_message_async=r["fetch_scheduled_message"],
            edit_scheduled_message_async=Recorder(None),
            delete_scheduled_message_async=r["delete_scheduled"],
        ),
        _recorders=r,
    )


def run_cli(argv, capsys, **overrides):
    raw = make_raw(**overrides)
    client = create_pumble_client(raw=raw)
    code = main(argv, client=client)
    captured = capsys.readouterr()
    return code, captured.out, captured.err, raw._recorders


def test_no_command_prints_help_and_exits_zero(capsys) -> None:
    code, _out, err, _ = run_cli([], capsys)
    assert code == 0
    assert "pumble-keys" in err


def test_whoami_human_and_json(capsys) -> None:
    code, out, _err, _ = run_cli(["whoami"], capsys)
    assert code == 0
    assert out == f"User 1 <user-1@example.invalid> ({USER_ID})\n"

    code, out, _err, _ = run_cli(["--json", "whoami"], capsys)
    assert code == 0
    assert json.loads(out)["id"] == USER_ID


def test_channels_list_find_create(capsys) -> None:
    code, out, _err, _ = run_cli(["channels", "list"], capsys)
    assert code == 0
    assert out == f"#engineering\t{CHANNEL_ID}\tPUBLIC\n"

    code, out, _err, _ = run_cli(["channels", "find", "engineering"], capsys)
    assert code == 0
    assert CHANNEL_ID in out

    code, out, err, r = run_cli(["channels", "create", "fresh", "--private"], capsys)
    assert code == 0
    assert r["create_channel"].calls == [{"name": "fresh", "type_": "PRIVATE"}]
    assert "Created channel" in err  # success prose on stderr
    assert out == ""


def test_users_find(capsys) -> None:
    code, out, _err, _ = run_cli(["users", "find", "user-1@example.invalid"], capsys)
    assert code == 0
    assert out == f"User 1 <user-1@example.invalid>\t{USER_ID}\n"


def test_send_resolves_and_uses_facade(capsys) -> None:
    code, _out, err, r = run_cli(["send", "#engineering", "hello", "world"], capsys)
    assert code == 0
    assert r["send_message"].calls == [
        {"request": {"channel_id": CHANNEL_ID, "text": "hello world"}}
    ]
    # Direct-read verification ran (façade receipts, not duplicated logic).
    assert len(r["fetch_message"].calls) == 1
    assert "Sent message" in err


def test_send_with_explicit_id_skips_listing(capsys) -> None:
    code, _out, _err, r = run_cli(["send", CHANNEL_ID, "hi"], capsys)
    assert code == 0
    assert r["list_channels"].calls == []


def test_dm_by_email_and_by_id(capsys) -> None:
    code, _out, _err, r = run_cli(["dm", "user-1@example.invalid", "yo"], capsys)
    assert code == 0
    assert r["dm_user"].calls == [{"user_id": USER_ID, "text": "yo"}]

    code, _out, _err, r2 = run_cli(["dm", USER_ID, "yo"], capsys)
    assert code == 0
    assert r2["list_users"].calls == []


def test_search_and_messages_and_thread(capsys) -> None:
    code, out, _err, r = run_cli(["search", "alert", "--limit", "5"], capsys)
    assert code == 0
    assert r["search_messages"].calls == [{"text": "alert", "limit": 5}]
    assert "[redacted] text" in out

    code, out, _err, _ = run_cli(["messages", "#engineering"], capsys)
    assert code == 0
    assert MESSAGE_ID not in out  # compact line format, not raw dump
    assert "[redacted] text" in out

    code, out, _err, _ = run_cli(
        ["thread", MESSAGE_ID, "--channel", CHANNEL_ID], capsys
    )
    assert code == 0
    assert out.count("\n") == 2  # root + one reply


def test_status_set_normalizes_emoji_and_clear(capsys) -> None:
    code, _out, err, r = run_cli(
        ["status", "set", "palm_tree", "on", "holiday"], capsys
    )
    assert code == 0
    assert r["custom_status"].calls == [
        {"code": ":palm_tree:", "expires_at": 0, "status": "on holiday"}
    ]
    assert "Set custom status" in err

    code, _out, _err, r2 = run_cli(["status", "clear"], capsys)
    assert code == 0
    assert r2["custom_status"].calls[0]["code"] == ":speech_balloon:"


def test_schedule_list_create_cancel(capsys) -> None:
    code, out, _err, _ = run_cli(["schedule", "list"], capsys)
    assert code == 0
    assert SCHEDULED_ID in out

    future = 99_999_999_999_999
    code, _out, err, r = run_cli(
        ["schedule", "create", CHANNEL_ID, str(future), "later"], capsys
    )
    assert code == 0
    assert r["create_scheduled"].calls == [
        {"channel_id": CHANNEL_ID, "text": "later", "send_at": future}
    ]

    code, _out, err, r2 = run_cli(["schedule", "cancel", SCHEDULED_ID], capsys)
    assert code == 0
    assert r2["delete_scheduled"].calls == [{"scheduled_message_id": SCHEDULED_ID}]
    assert "Canceled scheduled message" in err


def test_usage_errors_exit_2(capsys) -> None:
    for argv in (
        ["send", "#engineering"],  # missing text
        ["channels", "banana"],
        ["unknown-command"],
        ["search", "x", "--limit", "0"],
        ["thread", MESSAGE_ID],  # missing --channel
    ):
        code, _out, err, _ = run_cli(argv, capsys)
        assert code == 2, argv
        assert "pumble-keys:" in err


def test_operation_failure_exits_1(capsys) -> None:
    code, _out, err, _ = run_cli(["channels", "find", "ghost-channel"], capsys)
    assert code == 1
    assert "not found" in err


def test_json_failure_still_writes_errors_to_stderr(capsys) -> None:
    code, out, err, _ = run_cli(["--json", "channels", "find", "ghost-channel"], capsys)
    assert code == 1
    assert out == ""
    assert "ghost-channel" in err


def test_doctor_masks_key_and_never_prints_it(capsys, monkeypatch) -> None:
    monkeypatch.setenv("PUMBLE_API_KEY", KEY)
    code = main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert KEY not in captured.out + captured.err
    assert "cdc8" in captured.out  # last four visible
    assert "base url:" in captured.out


def test_credential_precedence_file_stdin_env(capsys, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PUMBLE_API_KEY", "env-key-0000")
    key_file = tmp_path / "key"
    key_file.write_text("file-key-1111\n")

    code = main(["--api-key-file", str(key_file), "doctor"])
    assert "1111" in capsys.readouterr().out
    assert code == 0

    monkeypatch.setattr("sys.stdin", io.StringIO("stdin-key-2222\n"))
    code = main(["--api-key-stdin", "doctor"])
    assert "2222" in capsys.readouterr().out

    code = main(["doctor"])
    assert "0000" in capsys.readouterr().out


def test_missing_key_is_usage_error(capsys, monkeypatch) -> None:
    monkeypatch.delenv("PUMBLE_API_KEY", raising=False)
    code = main(["whoami"])
    captured = capsys.readouterr()
    assert code == 2
    assert "missing API key" in captured.err


def test_json_variants_of_read_commands(capsys) -> None:
    code, out, _err, _ = run_cli(["--json", "channels", "list"], capsys)
    assert code == 0
    parsed = json.loads(out)
    assert parsed[0]["id"] == CHANNEL_ID

    code, out, _err, _ = run_cli(["--json", "channels", "find", "engineering"], capsys)
    assert code == 0
    assert json.loads(out)["id"] == CHANNEL_ID

    code, out, _err, _ = run_cli(
        ["--json", "users", "find", "user-1@example.invalid"], capsys
    )
    assert code == 0
    assert json.loads(out)["id"] == USER_ID

    code, out, _err, _ = run_cli(["--json", "search", "alert"], capsys)
    assert code == 0
    parsed = json.loads(out)
    assert isinstance(parsed, list) and parsed[0]["channel_id"] == CHANNEL_ID

    code, out, _err, _ = run_cli(["--json", "messages", "#engineering"], capsys)
    assert code == 0
    parsed = json.loads(out)
    assert isinstance(parsed, list) and parsed[0]["channel_id"] == CHANNEL_ID

    code, out, _err, _ = run_cli(
        ["--json", "thread", MESSAGE_ID, "--channel", CHANNEL_ID], capsys
    )
    assert code == 0
    parsed = json.loads(out)
    assert parsed["root"]["channel_id"] == CHANNEL_ID
    assert len(parsed["replies"]) == 1

    code, out, _err, _ = run_cli(["--json", "schedule", "list"], capsys)
    assert code == 0
    parsed = json.loads(out)
    assert isinstance(parsed, list) and parsed[0]["id"] == SCHEDULED_ID


def test_json_write_command_prints_receipt(capsys) -> None:
    code, out, _err, _ = run_cli(["--json", "channels", "create", "fresh"], capsys)
    assert code == 0
    assert json.loads(out)  # machine-readable receipt on stdout


def test_schedule_list_channel_filter_resolves_id(capsys) -> None:
    code, _out, _err, r = run_cli(
        ["schedule", "list", "--channel", "#engineering"], capsys
    )
    assert code == 0
    assert r["fetch_scheduled_messages"].calls[0]["channel_id"] == CHANNEL_ID


def test_bare_subcommands_are_usage_errors(capsys) -> None:
    for argv in (["channels"], ["users"], ["status"], ["schedule"]):
        code, _out, err, _ = run_cli(argv, capsys)
        assert code == 2, argv
        assert "pumble-keys: usage:" in err


def test_unknown_command_in_run_is_usage_error() -> None:
    import asyncio

    import pytest

    from pumble_keys.cli.main import UsageError, _run

    with pytest.raises(UsageError, match="unknown command: bogus"):
        asyncio.run(_run(SimpleNamespace(command="bogus"), SimpleNamespace()))


def test_failure_choices_render_dict_and_object_shapes(capsys) -> None:
    from pumble_keys.extensions.results import FacadeFailure

    failure = FacadeFailure(
        reason="ambiguous",
        summary='Channel "eng" is ambiguous.',
        choices=(
            {"label": "#eng-a | PUBLIC | 1"},
            {"id": "2"},  # dict without label falls back to the dict itself
            SimpleNamespace(label="#eng-b | PUBLIC | 3"),
            "bare-string",  # object without label falls back to str()
        ),
    )

    async def find(_query):
        return failure

    client = SimpleNamespace(channels=SimpleNamespace(find=find))
    code = main(["channels", "find", "eng"], client=client)
    err = capsys.readouterr().err
    assert code == 1
    assert "Choices: #eng-a | PUBLIC | 1, " in err
    assert "#eng-b | PUBLIC | 3" in err
    assert "bare-string" in err


def test_unexpected_exception_exits_1(capsys) -> None:
    async def find(_query):
        raise RuntimeError("boom")

    client = SimpleNamespace(channels=SimpleNamespace(find=find))
    code = main(["channels", "find", "eng"], client=client)
    captured = capsys.readouterr()
    assert code == 1
    assert "pumble-keys: boom" in captured.err


def test_client_construction_with_env_key(capsys, monkeypatch) -> None:
    # No injected client: main builds the façade client from the env key.
    monkeypatch.setenv("PUMBLE_API_KEY", KEY)
    seen: dict = {}

    def fake_factory(key, *, server_url, timeout_ms):
        seen.update(key=key, server_url=server_url, timeout_ms=timeout_ms)
        return create_pumble_client(raw=make_raw())

    import sys

    cli_main = sys.modules["pumble_keys.cli.main"]
    monkeypatch.setattr(cli_main, "create_pumble_client", fake_factory)
    code = main(["--base-url", "https://example.invalid", "whoami"])
    captured = capsys.readouterr()
    assert code == 0
    assert seen == {
        "key": KEY,
        "server_url": "https://example.invalid",
        "timeout_ms": None,
    }
    assert USER_ID in captured.out
