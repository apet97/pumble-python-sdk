"""P12: defensive exhaustive search — golden replay of server quirks."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from pumble_keys.extensions.search import (
    PageCapExceededError,
    search_all_messages,
)


def hit(hit_id: str, ts: int | None):
    return SimpleNamespace(id=hit_id, timestamp_milli=ts)


def page(hits, has_more: bool):
    return SimpleNamespace(
        result=SimpleNamespace(
            content=list(hits), total_elements=len(hits), has_more=has_more
        )
    )


class FakeSearch:
    """Replays scripted pages keyed by requested before_ts cursor."""

    def __init__(self, script) -> None:
        # script: list of (expected_before_ts, page) in call order.
        self.script = list(script)
        self.requests: list[dict] = []

    async def __call__(self, request: dict):
        self.requests.append(request)
        if not self.script:
            return page([], has_more=False)
        expected, result = self.script.pop(0)
        assert request.get("before_ts") == expected, (
            f"cursor mismatch: expected {expected}, got {request.get('before_ts')}"
        )
        return result


async def collect(gen):
    return [item async for item in gen]


@pytest.mark.asyncio
async def test_simple_two_page_walk_advances_by_min_ts_minus_one() -> None:
    fake = FakeSearch(
        [
            (None, page([hit("a", 5000), hit("b", 4000)], has_more=True)),
            (3999, page([hit("c", 3000)], has_more=False)),
        ]
    )
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 2}))
    assert [h.id for h in hits] == ["a", "b", "c"]
    assert len(fake.requests) == 2


@pytest.mark.asyncio
async def test_same_second_boundary_overlap_recovers_straddled_hit() -> None:
    # Page 1 ends with two hits at min ts 4000 → overlap with beforeTs 5000.
    fake = FakeSearch(
        [
            (None, page([hit("a", 5000), hit("b", 4000), hit("c", 4000)], True)),
            (5000, page([hit("b", 4000), hit("c", 4000), hit("d", 4000)], True)),
            (5000, page([hit("b", 4000), hit("c", 4000), hit("d", 4000)], True)),
            (3999, page([hit("e", 3000)], False)),
        ]
    )
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 3}))
    assert [h.id for h in hits] == ["a", "b", "c", "d", "e"]


@pytest.mark.asyncio
async def test_overlap_attempts_are_capped_at_three() -> None:
    boundary = page([hit("a", 4000), hit("b", 4000)], True)

    def fresh(i):
        return page([hit(f"new{i}", 4000), hit("a", 4000)], True)

    fake = FakeSearch(
        [
            (None, boundary),
            (5000, fresh(1)),
            (5000, fresh(2)),
            (5000, fresh(3)),
            # After 3 overlap attempts the walk advances to min_ts - 1.
            (3999, page([], False)),
        ]
    )
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 2}))
    assert [h.id for h in hits] == ["a", "b", "new1", "new2", "new3"]
    assert len(fake.requests) == 5


@pytest.mark.asyncio
async def test_duplicate_page_same_first_id_stops() -> None:
    same = page([hit("a", 4000)], True)
    fake = FakeSearch([(None, same), (3999, same)])
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 1}))
    assert [h.id for h in hits] == ["a"]
    assert len(fake.requests) == 2


@pytest.mark.asyncio
async def test_page_with_zero_new_ids_stops() -> None:
    fake = FakeSearch(
        [
            (None, page([hit("a", 5000), hit("b", 4000)], True)),
            (3999, page([hit("b", 3000), hit("a", 2500)], True)),
        ]
    )
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 2}))
    assert [h.id for h in hits] == ["a", "b"]


@pytest.mark.asyncio
async def test_missing_timestamps_stop_the_cursor() -> None:
    fake = FakeSearch([(None, page([hit("a", None), hit("b", None)], True))])
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 2}))
    assert [h.id for h in hits] == ["a", "b"]
    assert len(fake.requests) == 1  # cursor cannot advance → stop


@pytest.mark.asyncio
async def test_contradictory_has_more_false_with_short_page_stops() -> None:
    fake = FakeSearch([(None, page([hit("a", 5000)], has_more=False))])
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 10}))
    assert [h.id for h in hits] == ["a"]
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_has_more_false_with_full_page_still_walks_on() -> None:
    fake = FakeSearch(
        [
            (None, page([hit("a", 5000), hit("b", 4000)], has_more=False)),
            (3999, page([], has_more=False)),
        ]
    )
    hits = await collect(search_all_messages(fake, {"text": "x", "limit": 2}))
    assert [h.id for h in hits] == ["a", "b"]
    assert len(fake.requests) == 2


@pytest.mark.asyncio
async def test_max_results_stops_mid_page() -> None:
    fake = FakeSearch(
        [(None, page([hit("a", 5000), hit("b", 4000), hit("c", 3000)], True))]
    )
    hits = await collect(
        search_all_messages(fake, {"text": "x", "limit": 3}, max_results=2)
    )
    assert [h.id for h in hits] == ["a", "b"]
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_early_break_stops_fetching() -> None:
    fake = FakeSearch(
        [
            (None, page([hit("a", 5000), hit("b", 4000)], True)),
        ]
    )
    gen = search_all_messages(fake, {"text": "x", "limit": 2})
    async for item in gen:
        assert item.id == "a"
        break
    await gen.aclose()
    assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_page_cap_guard_raises() -> None:
    class EndlessSearch:
        def __init__(self) -> None:
            self.ts = 10_000_000

        async def __call__(self, request: dict):
            self.ts -= 2000
            return page([hit(f"id{self.ts}", self.ts)], True)

    with pytest.raises(PageCapExceededError, match="exceeded 5 pages"):
        await collect(
            search_all_messages(EndlessSearch(), {"text": "x", "limit": 1}, max_pages=5)
        )


@pytest.mark.asyncio
async def test_cancellation_propagates() -> None:
    started = asyncio.Event()

    async def hanging_search(request: dict):
        started.set()
        await asyncio.sleep(3600)

    async def run():
        return await collect(search_all_messages(hanging_search, {"text": "x"}))

    task = asyncio.ensure_future(run())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_on_page_observer_counts_and_abort() -> None:
    events = []
    fake = FakeSearch(
        [
            (None, page([hit("a", 5000), hit("b", 4000)], True)),
            (3999, page([hit("b", 3000), hit("c", 3000), hit("d", 2500)], False)),
        ]
    )

    def on_page(_page, info):
        events.append(info)

    hits = await collect(
        search_all_messages(fake, {"text": "x", "limit": 2}, on_page=on_page)
    )
    assert [h.id for h in hits] == ["a", "b", "c", "d"]
    assert events[0] == {"page_index": 1, "new_in_page": 2, "yielded": 0}
    assert events[1] == {"page_index": 2, "new_in_page": 2, "yielded": 2}

    class Abort(Exception):
        pass

    def aborting(_page, _info):
        raise Abort

    fake2 = FakeSearch([(None, page([hit("a", 5000)], True))])
    with pytest.raises(Abort):
        await collect(
            search_all_messages(fake2, {"text": "x", "limit": 1}, on_page=aborting)
        )
