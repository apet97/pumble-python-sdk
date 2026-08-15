# Raw generated SDK — the escape hatch

The pinned Speakeasy generator (`1.763.6`) emits the raw Python SDK from
`PumbleOpenApi.yaml`. This is the complete, low-level API surface. The
curated façade in `pumble_keys.extensions` is the supported high-level
API; use the raw SDK when you need an operation the façade does not
cover.

> **Stability warning.** The raw surface (method names, request/response
> model names, module layout) is owned by the generator. A generator
> upgrade can rename any of it without a deprecation cycle. Only the
> hand-written packages (`extensions`, `pumble_app`, `mcp_server`, `cli`,
> `testing`) follow this project's own compatibility policy.

## Entry point

```python
from pumble_keys import PumbleSDK

with PumbleSDK(api_key_auth="...") as sdk:
    channels = sdk.channels.list_channels()
```

- `api_key_auth` installs the workspace API key into the `ApiKey` request
  header. Never hardcode it; read it from the environment or a secret
  store.
- Default server: `https://pumble-api-keys.addons.marketplace.cake.com`.
  Override per client (`server_url=`) or per call.
- Async: every operation has an `_async` twin
  (`await sdk.channels.list_channels_async()`); use
  `async with PumbleSDK(...)` for cleanup.

## Namespaces

| SDK attribute | Module | Operations |
|---|---|---:|
| `sdk.channels` | `channels.py` | 5 |
| `sdk.messages` | `messages.py` | 12 |
| `sdk.scheduled_messages` | `scheduled_messages.py` | 5 |
| `sdk.users` | `users.py` | 4 |

The exact operation-to-method map lives in
`contracts/generated_api.json`, produced by
`tools/inventory_generated_api.py` through AST inspection of the
generated source. Regenerate it after every generator run; `--check`
verifies it without rewriting.

## Retry behavior

- All 11 reads default to the OpenAPI backoff: initial 500 ms, max
  interval 30,000 ms, exponent 1.5, max elapsed 60,000 ms, on HTTP
  429/5xx and connection errors.
- All 15 writes have **no** default retry configuration and carry the
  `x-sdk-no-write-retries` extension. Do not pass a `retries=` value or a
  client-wide `retry_config` that wraps writes: a retried write can
  duplicate a message. The façade never does this.

## Pagination

`listMessages`, `fetchThreadReplies`, `searchMessages`, and
`fetchScheduledMessages` return generated pager wrappers (`next()`
helpers). The defensive exhaustive helpers with loop protection live in
the façade (`extensions`), not here.

## Errors

Failures raise generated exceptions:

- `models.errors.Error` — a typed union of the two documented body
  shapes: legacy `{"error"}` and structured
  `{"message", "localizedMessage", "code"}`.
- `models.errors.PumbleSDKError` — any other non-2xx response.

The façade converts these into structured result values; raw SDK callers
handle exceptions themselves.
