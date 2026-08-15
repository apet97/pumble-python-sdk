# Webhooks and the PumbleApp helper

## Security model

Every receiver in this package verifies the Pumble HMAC signature
before parsing anything:

- signature = HMAC-SHA256(signing secret, `<timestamp>:<raw-body>`),
  compared timing-safely against `x-pumble-request-signature`;
- `x-pumble-request-timestamp` must be within ±300 s;
- bodies over 1 MiB are rejected (413) before verification;
- bad signature → 401, malformed JSON → 400, handler failure → 500 —
  and a failed request publishes/dispatches nothing.

## Event types

Seven typed events, with the compact wire fields preserved
(`aId`, `cId`, `tx`, `mId`, `trId`, `eph`, …): `NEW_MESSAGE`,
`UPDATED_MESSAGE`, `REACTION_ADDED`, `CHANNEL_CREATED`,
`WORKSPACE_USER_JOINED`, `APP_UNINSTALLED`, `APP_UNAUTHORIZED`.
Both the envelope form (`eventType` + `body`) and the compact form
(`ty` + flat fields) normalize to the same `PumbleWebhookEvent`.

## PumbleApp

```python
import os

from pumble_keys.pumble_app.app import PumbleApp

app = PumbleApp(signing_secret=os.environ["PUMBLE_SIGNING_SECRET"])


@app.event("NEW_MESSAGE")
async def on_message(event, context):
    body = event.body
    print("message", body.m_id, "in channel", body.c_id)


asgi = app.asgi_app()  # serve with uvicorn/hypercorn; POST only
```

Routing: handlers run in registration order; the first failure stops
dispatch and the receiver answers 500 (Pumble retries). Events need no
acknowledgment call.

For Socket Mode (no public ingress), `pumble_keys.pumble_app.socket_mode`
consumes the same events over an injected transport. For bridging
webhooks into MCP subscriptions, see [MCP.md](MCP.md).
