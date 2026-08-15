# MCP server

`pumble-keys-mcp` serves one Pumble workspace over the Model Context
Protocol (2026-07-28 revision, with legacy-handshake compatibility).
Secrets come from the environment only: `PUMBLE_API_KEY` (or
`PUMBLE_API_KEY_FILE`), `PUMBLE_CONFIRMATION_SECRET`,
`PUMBLE_MCP_TOKEN_VERIFIER`.

## Profiles

| Profile | Surface |
|---|---|
| `curated` (default) | 7 read tools + preview/confirm writes + resources/prompts + the MCP App |
| `curated-interactive` | curated + MRTR in-call confirmation send/reply tools |
| `readonly` | exact raw adapters for the 11 read operations |
| `readwrite` | readonly + the 15 raw write adapters — requires BOTH `--allow-raw-writes` and `--audit-log`; `--dry-run` executes no writes |

Tool catalogs are deterministic per profile (frozen in
`fixtures/replay/mcp/manifests.json`).

## stdio host configuration (exact)

```json
{
  "mcpServers": {
    "pumble": {
      "command": "pumble-keys-mcp",
      "args": ["--profile", "curated"],
      "env": { "PUMBLE_API_KEY": "…" }
    }
  }
}
```

stdout carries only the MCP wire; diagnostics go to stderr.

## Streamable HTTP (exact behavior, no SSE)

```bash
export PUMBLE_API_KEY=…
export PUMBLE_CONFIRMATION_SECRET=…   # required for stateless preview/confirm
pumble-keys-mcp --transport streamable-http --host 127.0.0.1 --port 2718 \
  --path /mcp --allowed-host 127.0.0.1:2718 --allowed-origin http://127.0.0.1:2718
```

- Single endpoint `POST /mcp` (stateless by default). **The superseded
  SSE transport is not supported and `--transport sse` is rejected.**
- DNS-rebinding protection: unlisted `Host` → 421, unlisted `Origin` →
  403, body over the 4 MiB cap → 413.
- A non-loopback bind REFUSES to start without an OAuth token verifier
  (`--auth-issuer` + `--auth-resource-url` + `PUMBLE_MCP_TOKEN_VERIFIER`);
  `--unsafe-no-auth` exists for development only and warns loudly.
- Remote authorization is standard OAuth resource-server behavior:
  bearer token verified per request, 401 with `WWW-Authenticate`
  metadata when missing/invalid. A client-credentials broker extension
  is deliberately deferred (see [STABILITY.md](STABILITY.md)).
- Routing headers: the client mirrors the JSON-RPC method into
  `Mcp-Method` and tool/prompt/resource names into `Mcp-Name`, so a
  proxy can rate-limit or deny before parsing the body
  (`HeaderToolPolicy` is the in-process reference).
- Cache hints: catalogs/discover 60 s private; `resources/read` 5 s
  private.

## Subscriptions and webhooks

Pumble webhook events become URI-only `ResourceUpdated` refetch cues on
`subscriptions/listen`. Mount `POST /webhooks/pumble` beside `/mcp`
with `mount_pumble_webhooks(...)` (protected by the Pumble HMAC
signature, not MCP bearer auth). The in-process bus is single-process;
multi-replica deployments need a shared `SubscriptionBus` adapter. The
stock CLI does not yet mount the webhook route — assembling the ASGI
app manually is required for that deployment shape.

## Resources and prompts

`pumble://me`, `pumble://channels`, `pumble://channel/{channel_id}`,
`pumble://thread/{channel_id}/{message_id}`,
`pumble://knowledge/{+path}`, `pumble://events/{name}`; four prompts
with argument completions. The MCP App is documented in
[MCP-APP.md](MCP-APP.md); write safety in [MCP-SAFETY.md](MCP-SAFETY.md).
