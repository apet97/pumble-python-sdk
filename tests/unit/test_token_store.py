"""P22: token store — protocol conformance and in-memory behavior."""

from __future__ import annotations

import pytest

from pumble_keys.pumble_app.token_store import (
    InMemoryTokenStore,
    PumbleOAuthAccessTokenResponse,
    TokenStore,
)

WORKSPACE = "0" * 20 + "0001"
USER = "0" * 20 + "0002"
BOT = "0" * 20 + "0003"


def response(**overrides) -> PumbleOAuthAccessTokenResponse:
    payload = {
        "access_token": "token-user-not-real",
        "user_id": USER,
        "workspace_id": WORKSPACE,
        "bot_token": "token-bot-not-real",
        "bot_id": BOT,
    }
    payload.update(overrides)
    return PumbleOAuthAccessTokenResponse(**payload)


def test_in_memory_store_satisfies_protocol() -> None:
    assert isinstance(InMemoryTokenStore(), TokenStore)


@pytest.mark.asyncio
async def test_save_and_get_round_trip() -> None:
    store = InMemoryTokenStore()
    await store.initialize()
    await store.save_tokens(response())
    assert await store.get_user_token(WORKSPACE, USER) == "token-user-not-real"
    assert await store.get_bot_token(WORKSPACE) == "token-bot-not-real"
    assert await store.get_bot_user_id(WORKSPACE) == BOT

    assert await store.get_user_token(WORKSPACE, "unknown") is None
    assert await store.get_bot_token("unknown") is None
    assert await store.get_bot_user_id("unknown") is None


@pytest.mark.asyncio
async def test_save_without_bot_fields_keeps_existing() -> None:
    store = InMemoryTokenStore()
    await store.save_tokens(response())
    await store.save_tokens(
        response(access_token="token-user-2", user_id="u2", bot_token=None, bot_id=None)
    )
    assert await store.get_bot_token(WORKSPACE) == "token-bot-not-real"
    assert await store.get_user_token(WORKSPACE, "u2") == "token-user-2"
    assert await store.get_user_token(WORKSPACE, USER) == "token-user-not-real"


@pytest.mark.asyncio
async def test_delete_for_user_only_removes_that_user() -> None:
    store = InMemoryTokenStore()
    await store.save_tokens(response())
    await store.save_tokens(response(access_token="t2", user_id="u2"))
    await store.delete_for_user(USER, WORKSPACE)
    assert await store.get_user_token(WORKSPACE, USER) is None
    assert await store.get_user_token(WORKSPACE, "u2") == "t2"
    assert await store.get_bot_token(WORKSPACE) == "token-bot-not-real"


@pytest.mark.asyncio
async def test_delete_for_workspace_removes_everything() -> None:
    store = InMemoryTokenStore()
    await store.save_tokens(response())
    await store.delete_for_workspace(WORKSPACE)
    assert await store.get_user_token(WORKSPACE, USER) is None
    assert await store.get_bot_token(WORKSPACE) is None


@pytest.mark.asyncio
async def test_deletes_on_unknown_targets_are_noops() -> None:
    store = InMemoryTokenStore()
    await store.delete_for_workspace("unknown")
    await store.delete_for_user("unknown", "unknown")
