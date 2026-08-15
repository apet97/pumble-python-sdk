# API reference map

Three layers, strictly separated:

## 1. Generated raw SDK (`pumble_keys.*`)

Speakeasy-generated from `PumbleOpenApi.yaml` (pin recorded in
`.speakeasy/gen.yaml`). 26 operations — 11 reads, 15 writes — across
`channels`, `messages`, `scheduled_messages`, `users`. Exact inventory:
`contracts/generated_api.json`; endpoint docs: `docs/sdks/` and
`docs/RAW_API.md`. Generated files are never hand-edited
(`docs/GENERATOR_DEVIATIONS.md` records the two documented pyproject
patches).

```python
from pumble_keys import PumbleSDK  # generated entry point
```

## 2. Async façade (`pumble_keys.extensions`)

The supported surface for applications. `create_pumble_client(key)`
returns a `PumbleClient` with:

| Namespace | What it does |
|---|---|
| `client.identity.me()` | Compact identity |
| `client.channels.find/list/resolve` | Name/ID resolution with bounded, labeled ambiguity choices |
| `client.users.find/list/set_status/clear_status` | Same for users, plus custom status |
| `client.messages.send/dm/dm_group/get/list` | Sends return `WriteReceipt` with direct-read verification |
| `client.threads.reply/get_context` | Thread reply and compact context |
| `client.scheduled.create/list/get/edit/cancel` | Scheduled messages |
| `client.search.page/all` | Bounded search page / defensive full walk |
| `client.raw` | Escape hatch to layer 1 |

Contract highlights:

- Failures return `FacadeFailure` values (`reason`, `summary`,
  `choices`, `next_actions`) — the façade does not raise for normal
  not-found/ambiguity/API errors.
- **No write retries.** Only reads with proven-idempotent semantics
  retry on transient errors.
- **Direct-read proof.** Every write receipt embeds a
  `WriteVerification` produced by reading the object back BY ID (never
  by search); when the read-back fails, the receipt says
  `verification_failed` instead of pretending.
- Pagination and search walk defensively: ID dedupe, same-second
  boundary overlap handling, non-advancing-cursor stops, 10,000-page
  hard cap.

## 3. Integration surfaces

- CLI: `pumble-keys` (see [QUICKSTART.md](QUICKSTART.md)).
- MCP server: `pumble-keys-mcp` (see [MCP.md](MCP.md)).
- Pumble app helper + webhooks: [WEBHOOKS.md](WEBHOOKS.md).
- OAuth for user-scoped apps: [PUMBLE-OAUTH.md](PUMBLE-OAUTH.md).

Parity with the TypeScript reference is evidence-based:
[`PARITY_MATRIX.md`](../PARITY_MATRIX.md).
