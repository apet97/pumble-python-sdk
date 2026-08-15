# Migrating from the TypeScript SDK

The Python port follows the TS extensions contract (pinned reference
commit `cc20de1`); parity is evidence-based via the replay corpus —
see [`PARITY_MATRIX.md`](../PARITY_MATRIX.md) for the full difference
table.

## Name mapping

| TypeScript | Python |
|---|---|
| `createPumbleClient(key)` | `create_pumble_client(key)` |
| `client.channels.find(...)` | `client.channels.find(...)` (snake_case options) |
| camelCase fields (`channelId`, `hasMoreBefore`) | snake_case (`channel_id`, `has_more_before`) |
| `AbortSignal` | asyncio cancellation (no signal parameter) |
| thrown `TypeError` on bad IDs | raised `ValueError`, same message text |
| Facade failure objects | `FacadeFailure` pydantic values, same reasons/summaries |

## Behavioural equivalents

- Resolver semantics (exact → case-insensitive → bounded labeled
  ambiguity), error categorization (the exact 8-step table), defensive
  search/pagination, webhook signature verification, and write-plan
  canonicalization are ports with fixture-frozen behavior.
- Write receipts keep the TS summary texts (`Sent message X to
  #chan.`) and ADD a `verification` block (direct read-by-ID proof) —
  the one enrichment.
- The CLI is an argparse port of `pumble-keys-cli.mjs` plus
  `schedule create` (absent in TS).

## New in Python only

The MCP server (profiles, preview/confirm signed writes, MRTR,
subscriptions bridge, MCP App) and the packaged knowledge base have no
TS equivalent. The TS SDK's Node-specific helpers (Express adapters)
map to ASGI (`asgi_app()`, `starlette_route`).
