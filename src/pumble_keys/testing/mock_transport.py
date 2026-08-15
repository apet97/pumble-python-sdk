"""In-memory mock HTTP transport for the generated SDK.

Ported from ``extensions/testing/mock-fetch.ts`` onto ``httpx``.
Requests are matched FIFO by method, normalized/sorted path+query, and
sanitized structural body hash. Misses raise instead of falling through
to the network, so SDK tests run without live credentials.

Usage with the generated client:

    transport = create_mock_pumble_transport([...])
    sdk = PumbleSDK(
        api_key_auth="test-key-not-real",
        client=httpx.Client(transport=transport),
        async_client=httpx.AsyncClient(transport=transport),
    )
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

import httpx

from pumble_keys.testing.fixtures import (
    create_fixture_body_hash,
    sanitize_pumble_fixture_value,
)


class MockPumbleFetchMissError(AssertionError):
    """A request arrived with no registered fixture."""


@dataclass
class MockFixture:
    """One request/response pair.

    ``path`` may include query parameters; pairs are sorted before
    matching. ``body`` is sanitized, canonicalized, and hashed unless a
    precomputed ``body_hash`` is given (replay entries).
    """

    path: str
    method: str = "GET"
    body: Any = None
    body_hash: str | None = None
    status: int = 200
    response: Any = None
    headers: dict[str, str] = field(default_factory=dict)


def _normalize_path(url: str) -> str:
    parts = urlsplit(url)
    params = sorted(parse_qsl(parts.query, keep_blank_values=True))
    query = f"?{urlencode(params)}" if params else ""
    sanitized = sanitize_pumble_fixture_value(f"{parts.path}{query}")
    return sanitized if isinstance(sanitized, str) else f"{parts.path}{query}"


def _body_of(content: bytes) -> Any:
    if not content:
        return None
    try:
        return json.loads(content)
    except ValueError:
        return content.decode("utf-8", errors="replace")


def _fixture_key(fixture: MockFixture) -> tuple[str, str, str]:
    body_hash = fixture.body_hash or create_fixture_body_hash(
        sanitize_pumble_fixture_value(fixture.body)
    )
    return (
        fixture.method.upper(),
        _normalize_path(fixture.path),
        body_hash,
    )


def create_mock_pumble_transport(
    fixtures: list[MockFixture],
) -> httpx.MockTransport:
    """Build an ``httpx.MockTransport`` over the fixture entries."""
    buckets: dict[tuple[str, str, str], list[MockFixture]] = {}
    for fixture in fixtures:
        buckets.setdefault(_fixture_key(fixture), []).append(fixture)

    def handler(request: httpx.Request) -> httpx.Response:
        body = sanitize_pumble_fixture_value(_body_of(request.content))
        key = (
            request.method.upper(),
            _normalize_path(str(request.url)),
            create_fixture_body_hash(body),
        )
        bucket = buckets.get(key)
        if not bucket:
            registered = ", ".join(f"{k[0]} {k[1]}" for k in sorted(buckets)) or "none"
            raise MockPumbleFetchMissError(
                f"Mock Pumble fetch miss for {key[0]} {key[1]} "
                f"bodyHash={key[2]}; registered={registered}"
            )
        fixture = bucket.pop(0)
        if not bucket:
            del buckets[key]

        headers = dict(fixture.headers)
        content: bytes | str
        if fixture.response is None:
            content = b""
        elif isinstance(fixture.response, (str, bytes)):
            content = fixture.response
        else:
            headers.setdefault("content-type", "application/json")
            content = json.dumps(fixture.response)
        return httpx.Response(fixture.status, headers=headers, content=content)

    return httpx.MockTransport(handler)
