"""P12: channel-history pagination — opaque cursors, loop protection."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pumble_keys.extensions.pagination import list_all_messages
from pumble_keys.extensions.search import PageCapExceededError


def msg(message_id: str):
    return SimpleNamespace(id=message_id)


def page(messages, *, before=None, after=None):
    return SimpleNamespace(
        result=SimpleNamespace(
            messages=list(messages),
            has_more_before=before,
            has_more_after=after,
        )
    )


class FakeList:
    def __init__(self, script) -> None:
        self.script = list(script)
        self.requests: list[dict] = []

    async def __call__(self, request: dict):
        self.requests.append(request)
        expected_cursor, result = self.script.pop(0)
        assert request.get("cursor") == expected_cursor
        return result


async def collect(gen):
    return [item async for item in gen]


@pytest.mark.asyncio
async def test_backward_walk_uses_last_id_cursor_and_stops_on_flag() -> None:
    fake = FakeList(
        [
            (None, page([msg("c"), msg("b")], before=True)),
            ("b", page([msg("a")], before=False)),
        ]
    )
    out = await collect(list_all_messages(fake, {"channel_id": "x"}))
    assert [m.id for m in out] == ["c", "b", "a"]
    assert fake.requests[0]["strategy"] == "BEFORE"
    assert fake.requests[1]["cursor"] == "b"


@pytest.mark.asyncio
async def test_after_strategy_uses_has_more_after() -> None:
    fake = FakeList(
        [
            (None, page([msg("a"), msg("b")], after=True)),
            ("b", page([msg("c")], after=None)),
        ]
    )
    out = await collect(
        list_all_messages(fake, {"channel_id": "x", "strategy": "AFTER"})
    )
    assert [m.id for m in out] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_null_has_more_treated_as_stop() -> None:
    fake = FakeList([(None, page([msg("a")], before=None))])
    out = await collect(list_all_messages(fake, {"channel_id": "x"}))
    assert [m.id for m in out] == ["a"]
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_empty_page_stops() -> None:
    fake = FakeList([(None, page([], before=True))])
    assert await collect(list_all_messages(fake, {"channel_id": "x"})) == []


@pytest.mark.asyncio
async def test_duplicate_page_zero_new_ids_stops() -> None:
    fake = FakeList(
        [
            (None, page([msg("a"), msg("b")], before=True)),
            ("b", page([msg("a"), msg("b")], before=True)),
        ]
    )
    out = await collect(list_all_messages(fake, {"channel_id": "x"}))
    assert [m.id for m in out] == ["a", "b"]
    assert len(fake.requests) == 2


@pytest.mark.asyncio
async def test_nonadvancing_repeated_cursor_stops() -> None:
    fake = FakeList(
        [
            (None, page([msg("a"), msg("b")], before=True)),
            ("b", page([msg("c"), msg("b")], before=True)),
        ]
    )
    out = await collect(list_all_messages(fake, {"channel_id": "x"}))
    # Second page ends with "b" again → repeated cursor → stop.
    assert [m.id for m in out] == ["a", "b", "c"]
    assert len(fake.requests) == 2


@pytest.mark.asyncio
async def test_max_results_and_lazy_fetch() -> None:
    fake = FakeList([(None, page([msg("a"), msg("b"), msg("c")], before=True))])
    out = await collect(list_all_messages(fake, {"channel_id": "x"}, max_results=2))
    assert [m.id for m in out] == ["a", "b"]
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_page_cap_guard() -> None:
    class Endless:
        def __init__(self) -> None:
            self.n = 0

        async def __call__(self, request: dict):
            self.n += 1
            return page([msg(f"m{self.n}")], before=True)

    with pytest.raises(PageCapExceededError, match="list_all_messages"):
        await collect(list_all_messages(Endless(), {"channel_id": "x"}, max_pages=4))


@pytest.mark.asyncio
async def test_explicit_start_cursor_is_used() -> None:
    fake = FakeList([("start", page([msg("a")], before=False))])
    out = await collect(list_all_messages(fake, {"channel_id": "x", "cursor": "start"}))
    assert [m.id for m in out] == ["a"]
