"""Routing-header edge policy and route-aware metrics.

The 2026 transport mirrors the JSON-RPC method into the ``Mcp-Method``
HTTP header and — for ``tools/call``/``prompts/get``/``resources/read``
— the tool name / prompt name / resource URI into ``Mcp-Name``. That
lets a reverse proxy (or the ASGI edge middleware here) apply
routing, rate limits, and denials BEFORE the JSON body is parsed.

``HeaderToolPolicy`` is the in-process reference implementation of that
edge rule; the same match logic translates directly to nginx/Envoy
header conditions. ``MethodMetricsMiddleware`` is the context-tier
example: route-aware counters keyed by ``ctx.method``.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

MCP_METHOD_HEADER = b"mcp-method"
MCP_NAME_HEADER = b"mcp-name"


class HeaderToolPolicy:
    """ASGI middleware denying named tools from the headers alone.

    The denial happens before ``receive`` is ever called, so the JSON
    body is never read, parsed, or buffered for a denied request.
    """

    def __init__(self, app: Any, *, denied_tools: frozenset[str]) -> None:
        self._app = app
        self._denied = denied_tools

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            method = headers.get(MCP_METHOD_HEADER, b"").decode("latin-1")
            name = headers.get(MCP_NAME_HEADER, b"").decode("latin-1")
            if method == "tools/call" and name in self._denied:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": (f"tool {name} is denied by edge policy".encode()),
                    }
                )
                return
        await self._app(scope, receive, send)


class MethodMetricsMiddleware:
    """Context-tier middleware: count requests per JSON-RPC method."""

    def __init__(self) -> None:
        self.method_counts: Counter[str] = Counter()

    async def __call__(self, ctx: Any, call_next: Any) -> Any:
        self.method_counts[ctx.method] += 1
        return await call_next(ctx)
