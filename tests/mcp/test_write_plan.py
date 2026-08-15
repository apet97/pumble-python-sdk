"""P28: write plans — canonical previews, signed expiring tokens, replay."""

from __future__ import annotations

import pytest

from pumble_keys.extensions.write_plan import (
    ReplayGuard,
    canonical_json,
    create_confirmation_token,
    create_write_preview,
    validate_confirmation,
    verify_confirmation_token,
)

SECRET = b"confirmation-secret-not-real"
NOW = 1_786_752_000_000
WORKSPACE = "fp-0123456789abcdef"


def preview(**overrides):
    payload = {
        "action_type": "send_message",
        "target_kind": "channel",
        "target_id": "0" * 20 + "0001",
        "target_name": "engineering",
        "text": "hello secret world",
        "workspace_id": WORKSPACE,
        "request": {"action": "send_message", "channel_id": "c", "text": "t"},
        "now_ms": NOW,
    }
    payload.update(overrides)
    return create_write_preview(**payload)


def test_canonical_json_sorted_and_none_dropped() -> None:
    assert canonical_json({"b": 1, "a": None, "c": [2, {"y": 1, "x": None}]}) == (
        '{"b":1,"c":[2,{"y":1}]}'
    )


def test_preview_fields_and_expiry() -> None:
    plan = preview()
    assert plan.risk_level == "medium"  # inferred from "send"
    assert plan.issued_at_ms == NOW
    assert plan.expires_at_ms == NOW + 5 * 60 * 1000
    assert plan.text_excerpt == "hello secret world"
    assert len(plan.text_sha256) == 64
    assert len(plan.request_sha256) == 64
    assert plan.workspace_id == WORKSPACE


def test_excerpt_redacts_and_truncates() -> None:
    plan = preview(text="api-key: sekret123 " + "long words " * 40)
    assert "sekret123" not in plan.text_excerpt
    assert len(plan.text_excerpt) <= 160
    assert plan.text_excerpt.endswith("...")


def test_risk_inference() -> None:
    assert preview(action_type="delete_message").risk_level == "high"
    assert preview(action_type="send_message").risk_level == "medium"
    assert preview(action_type="observe_things").risk_level == "low"


def test_validation_rejects_blank_inputs() -> None:
    with pytest.raises(ValueError, match="action type"):
        preview(action_type="  ")
    with pytest.raises(ValueError, match="target kind"):
        preview(target_kind=" ")
    with pytest.raises(ValueError, match="target id or target name"):
        preview(target_id=None, target_name=None)


def test_token_roundtrip_and_tamper_rejection() -> None:
    plan = preview()
    token = create_confirmation_token(plan, SECRET)
    assert token.startswith("pumble-write-plan-v1.")
    assert verify_confirmation_token(plan, token, SECRET) is True

    tampered = plan.model_copy(update={"target_id": "0" * 20 + "0002"})
    assert verify_confirmation_token(tampered, token, SECRET) is False
    assert verify_confirmation_token(plan, token, b"other-secret") is False
    assert verify_confirmation_token(plan, "garbage", SECRET) is False
    assert verify_confirmation_token(plan, token + "x", SECRET) is False


def test_empty_secret_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        create_confirmation_token(preview(), b"")


def test_validate_confirmation_full_matrix() -> None:
    request = {"action": "send_message", "channel_id": "c", "text": "t"}
    plan = preview(request=request, text="body")
    token = create_confirmation_token(plan, SECRET)

    def check(**overrides):
        kwargs = {
            "preview": plan,
            "token": token,
            "secret": SECRET,
            "now_ms": NOW + 1000,
            "workspace_id": WORKSPACE,
            "request": request,
            "text": "body",
        }
        kwargs.update(overrides)
        return validate_confirmation(**kwargs)

    assert check() is None
    assert check(token="pumble-write-plan-v1.bogus") == "invalid_token"
    assert check(secret=b"wrong") == "invalid_token"
    assert check(now_ms=plan.expires_at_ms + 1) == "expired"
    assert check(workspace_id="fp-other") == "workspace_mismatch"
    assert check(request={**request, "text": "changed"}) == "request_mismatch"
    assert check(text="changed") == "text_mismatch"


def test_replay_guard_bounded() -> None:
    guard = ReplayGuard(max_entries=2)
    assert guard.consume("a") is True
    assert guard.consume("a") is False
    assert guard.consume("b") is True
    assert guard.consume("c") is True  # evicts "a"
    assert guard.consume("a") is True  # bounded store forgot it
    with pytest.raises(ValueError):
        ReplayGuard(max_entries=0)
