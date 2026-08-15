"""P08: structured results — uniform failure contract, opt-in exceptions."""

from __future__ import annotations

import json

import pytest

from pumble_keys.extensions.operations import (
    OPERATION_FAILURE_NEXT_ACTION,
    is_facade_operation_failure,
    operation_failure,
    operation_failure_reason,
)
from pumble_keys.extensions.results import (
    FacadeError,
    assert_facade_ok,
    create_facade_failure,
    create_facade_invalid_request,
    create_facade_operation_failure,
    is_facade_failure,
)

CHANNEL_ID = "0" * 20 + "0001"


def test_ambiguous_channel_failure_matches_contract() -> None:
    failure = create_facade_failure(
        "Channel",
        "eng",
        reason="ambiguous",
        candidates=[
            {"id": CHANNEL_ID, "name": "engineering", "channel_type": "PUBLIC"}
        ],
    )
    assert failure.ok is False
    assert failure.reason == "ambiguous"
    assert failure.summary == 'Channel "eng" is ambiguous.'
    assert failure.choices[0]["label"] == (f"#engineering | PUBLIC | {CHANNEL_ID}")
    assert failure.next_actions == (
        "Use a more exact Channel value or pass one returned channel id.",
    )


def test_not_found_user_failure_text() -> None:
    failure = create_facade_failure("User", "ghost", reason="not_found", candidates=[])
    assert failure.summary == 'User "ghost" is not found.'
    assert failure.next_actions == ("Check the user name, email, or id and try again.",)
    assert failure.choices == ()


def test_user_candidate_gets_label() -> None:
    failure = create_facade_failure(
        "User",
        "ex",
        reason="ambiguous",
        candidates=[
            {"id": CHANNEL_ID, "email": "user-1@example.invalid", "name": "Ex A"}
        ],
    )
    assert failure.choices[0]["label"] == (
        f"Ex A user-1@example.invalid | {CHANNEL_ID}"
    )


def test_existing_label_is_preserved() -> None:
    failure = create_facade_failure(
        "Channel",
        "x",
        reason="ambiguous",
        candidates=[{"id": CHANNEL_ID, "name": "x", "label": "custom"}],
    )
    assert failure.choices[0]["label"] == "custom"


def test_invalid_request_failure() -> None:
    failure = create_facade_invalid_request("Text is blank.", "Provide text.")
    assert failure.reason == "invalid_request"
    assert failure.next_actions == ("Provide text.",)


def test_cause_never_serializes() -> None:
    error = RuntimeError("secret-cause pmb_abc")
    failure = create_facade_operation_failure(
        "transport_error", "Request failed.", "Retry later.", error
    )
    assert failure.cause is error
    dumped = failure.model_dump(mode="json")
    assert "cause" not in dumped
    assert "secret-cause" not in json.dumps(dumped)
    assert "cause" not in repr(failure)


def test_failure_json_shape_matches_plan_example() -> None:
    failure = create_facade_failure(
        "Channel",
        "eng",
        reason="ambiguous",
        candidates=[
            {"id": CHANNEL_ID, "name": "engineering", "channel_type": "PUBLIC"}
        ],
    )
    dumped = failure.model_dump(mode="json")
    assert set(dumped) == {"ok", "reason", "summary", "choices", "next_actions"}


def test_is_facade_failure_guard() -> None:
    failure = create_facade_invalid_request("s", "n")
    assert is_facade_failure(failure) is True
    assert is_facade_failure(failure.model_dump()) is True
    assert is_facade_failure({"ok": False, "reason": "weird"}) is False
    assert is_facade_failure({"ok": True}) is False
    assert is_facade_failure(None) is False
    assert is_facade_failure("nope") is False


def test_assert_facade_ok_passes_through_success() -> None:
    receipt = {"ok": True, "summary": "sent"}
    assert assert_facade_ok(receipt) is receipt


def test_assert_facade_ok_raises_with_next_actions() -> None:
    failure = create_facade_invalid_request("Text is blank.", "Provide text.")
    with pytest.raises(FacadeError, match="Text is blank. Next actions: Provide text."):
        assert_facade_ok(failure)
    try:
        assert_facade_ok(failure)
    except FacadeError as raised:
        assert raised.failure is failure


def test_assert_facade_ok_without_next_actions() -> None:
    with pytest.raises(FacadeError, match="^Facade operation failed.$"):
        assert_facade_ok({"ok": False})


def test_operation_failure_reason_classification() -> None:
    class WithStatus(Exception):
        status_code = 500

    assert operation_failure_reason(WithStatus()) == "api_error"
    assert operation_failure_reason(ConnectionError("boom")) == "transport_error"
    assert operation_failure_reason(None) == "transport_error"


def test_operation_failure_builds_standard_value() -> None:
    error = ConnectionError("boom")
    failure = operation_failure("Send failed.", error)
    assert failure.reason == "transport_error"
    assert failure.summary == "Send failed."
    assert failure.next_actions == (OPERATION_FAILURE_NEXT_ACTION,)
    assert failure.cause is error


def test_is_facade_operation_failure() -> None:
    assert is_facade_operation_failure(create_facade_invalid_request("s", "n")) is True
    assert is_facade_operation_failure({"ok": False}) is True
    assert is_facade_operation_failure({"ok": True}) is False
    assert is_facade_operation_failure("x") is False
