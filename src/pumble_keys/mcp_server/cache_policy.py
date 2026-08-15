"""Cache hints for the cacheable MCP result classes (2026-07-28).

Policy (§11 of the plan):

- catalogs (``tools/list``, ``prompts/list``, ``resources/list``,
  ``resources/templates/list``) and ``server/discover`` — private with a
  conservative TTL: the surfaces are deterministic per profile but may
  change on redeploy;
- ``resources/read`` — private, 5-second TTL: the method serves both
  live Pumble data and static knowledge, so the method-level hint takes
  the live-data bound ("TTL 0 or at most 5 seconds"); the immutable App
  HTML (P36) opts out per-result by setting its own fields, which
  ``apply_cache_hint`` leaves untouched.
"""

from __future__ import annotations

from mcp.server import CacheHint
from mcp.server.caching import CacheableMethod

CATALOG_TTL_MS = 60_000
LIVE_READ_TTL_MS = 5_000

CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "server/discover": CacheHint(ttl_ms=CATALOG_TTL_MS, scope="private"),
    "tools/list": CacheHint(ttl_ms=CATALOG_TTL_MS, scope="private"),
    "prompts/list": CacheHint(ttl_ms=CATALOG_TTL_MS, scope="private"),
    "resources/list": CacheHint(ttl_ms=CATALOG_TTL_MS, scope="private"),
    "resources/templates/list": CacheHint(ttl_ms=CATALOG_TTL_MS, scope="private"),
    "resources/read": CacheHint(ttl_ms=LIVE_READ_TTL_MS, scope="private"),
}
