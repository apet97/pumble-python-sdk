"""Deterministic clocks for tests."""

from __future__ import annotations


class FakeClock:
    """Manual monotonic clock: call it for the time, ``advance`` to move it.

    Works everywhere the SDK injects ``now``/``now_ms`` — the resolver
    cache, rate limiter, retry helper, and scheduled façade.
    """

    def __init__(self, start: float = 0.0) -> None:
        self.time = start

    def __call__(self) -> float:
        return self.time

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("FakeClock.advance: seconds must be >= 0")
        self.time += seconds

    def now_ms(self) -> int:
        return int(self.time * 1000)
