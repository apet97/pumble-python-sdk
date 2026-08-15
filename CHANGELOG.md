# Changelog

All notable changes to `pumble_keys_sdk` are recorded here. Versions
follow the stability contract in [docs/STABILITY.md](docs/STABILITY.md).

## 0.1.0 — 2026-08-15

First release.

- Speakeasy-generated raw SDK for all 26 Pumble API-Keys operations
  (sync + async), with typed error unions.
- Value-typed async façade: resolver-first inputs, no write retries,
  direct-read proof on every write, bounded pagination and search.
- CLI (`pumble-keys`) with human and `--json` output.
- MCP server (`pumble-keys-mcp`): `curated` (preview/confirm writes),
  `readonly`, and `readwrite` profiles (raw writes double-gated behind
  `--allow-raw-writes` + `--audit-log`), plus `--dry-run`; stdio and
  stateless Streamable HTTP transports (no SSE).
- Interactive MCP App (bootstrap, channel pages, threads, composer
  with preview and explicit confirmation).
- Typed webhooks with timing-safe signature verification, ASGI
  receiver, event router, `PumbleApp`, Pumble OAuth helpers, and an
  experimental Socket Mode client (see
  [docs/EXPERIMENTAL.md](docs/EXPERIMENTAL.md)).
- Packaged knowledge base and replay-verified TypeScript parity
  corpus ([PARITY_MATRIX.md](PARITY_MATRIX.md)).

### Known limitations

- `mcp[cli]` is pinned to `==2.0.0`. The MCP server depends on
  protocol specifics of that release; the pin will be relaxed once a
  wider range is verified.
- The stock `pumble-keys-mcp` CLI does not mount the
  `/webhooks/pumble` bridge; manual ASGI assembly is required (see
  [docs/MCP.md](docs/MCP.md)).
- The subscription bus is in-process and single-process (see
  [docs/STABILITY.md](docs/STABILITY.md)).
