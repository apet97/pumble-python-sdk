"""P17: custom status — set, clear, read-proof, cache invalidation, no retry."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from pumble_keys.extensions.results import FacadeFailure
from pumble_keys.extensions.status import StatusFacade
from pumble_keys.models.errors import PumbleSDKError

USER_ID = "0" * 20 + "0001"


def sdk_error(status: int) -> PumbleSDKError:
    return PumbleSDKError(
        "API error occurred",
        httpx.Response(
            status,
            text="",
            request=httpx.Request("POST", "https://sanitized.example.invalid"),
        ),
    )


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


class FakeCache:
    def __init__(self) -> None:
        self.cleared: list = []

    def clear(self, kind=None) -> None:
        self.cleared.append(kind)


def make_facade(**overrides):
    r = {
        "custom_status": Recorder({"ok": True}),
        "my_info": Recorder(SimpleNamespace(id=USER_ID)),
    }
    r.update(overrides)
    raw = SimpleNamespace(
        users=SimpleNamespace(
            custom_status_async=r["custom_status"],
            my_info_async=r["my_info"],
        )
    )
    cache = FakeCache()
    return StatusFacade(raw=raw, resolver_cache=cache), r, cache


@pytest.mark.asyncio
async def test_set_status_exact_payload_and_read_proof() -> None:
    facade, r, cache = make_facade()
    receipt = await facade.set_status(
        code=":palm_tree:", expires_at=0, status="on holiday"
    )
    assert receipt.ok is True
    assert receipt.summary == "Set custom status :palm_tree:."
    assert receipt.verification.state == "verified"
    # Exact OpenAPI payload; no silent emoji normalization.
    assert r["custom_status"].calls == [
        {"code": ":palm_tree:", "expires_at": 0, "status": "on holiday"}
    ]
    assert len(r["my_info"].calls) == 1  # exactly one read-proof
    assert cache.cleared == ["users"]


@pytest.mark.asyncio
async def test_set_status_without_text_omits_status_field() -> None:
    facade, r, _cache = make_facade()
    await facade.set_status(code=":zap:", expires_at=0)
    assert r["custom_status"].calls == [{"code": ":zap:", "expires_at": 0}]


@pytest.mark.asyncio
async def test_set_status_validation_before_any_call() -> None:
    facade, r, cache = make_facade()
    for kwargs in (
        {"code": "  ", "expires_at": 0},
        {"code": ":zap:", "expires_at": 1.5},
        {"code": ":zap:", "expires_at": True},
        {"code": ":zap:", "expires_at": "never"},
    ):
        failure = await facade.set_status(**kwargs)
        assert isinstance(failure, FacadeFailure)
        assert failure.reason == "invalid_request"
    assert r["custom_status"].calls == []
    assert cache.cleared == []


@pytest.mark.asyncio
async def test_write_failure_single_attempt_no_cache_touch() -> None:
    facade, r, cache = make_facade(custom_status=Recorder(error=sdk_error(503)))
    failure = await facade.set_status(code=":zap:", expires_at=0)
    assert isinstance(failure, FacadeFailure)
    assert len(r["custom_status"].calls) == 1  # transient, still one attempt
    assert r["my_info"].calls == []
    assert cache.cleared == []


@pytest.mark.asyncio
async def test_read_proof_failure_is_honest_and_skips_invalidation() -> None:
    facade, r, cache = make_facade(my_info=Recorder(error=sdk_error(500)))
    receipt = await facade.set_status(code=":zap:", expires_at=0)
    assert receipt.ok is True  # write succeeded
    assert receipt.verification.state == "verification_failed"
    assert "NOT retried" in receipt.verification.detail
    assert len(r["custom_status"].calls) == 1
    assert len(r["my_info"].calls) == 1
    assert cache.cleared == []  # unverified → do not invalidate


@pytest.mark.asyncio
async def test_clear_status_uses_expired_write_and_invalidates() -> None:
    facade, r, cache = make_facade()
    receipt = await facade.clear_status()
    assert receipt.ok is True
    assert receipt.summary == "Cleared custom status."
    assert r["custom_status"].calls == [{"code": ":speech_balloon:", "expires_at": 1}]
    assert len(r["my_info"].calls) == 1
    assert cache.cleared == ["users"]


@pytest.mark.asyncio
async def test_clear_status_failure_value() -> None:
    facade, _r, cache = make_facade(custom_status=Recorder(error=sdk_error(401)))
    failure = await facade.clear_status()
    assert isinstance(failure, FacadeFailure)
    assert failure.summary == "Pumble API rejected users.clear_status."
    assert cache.cleared == []
