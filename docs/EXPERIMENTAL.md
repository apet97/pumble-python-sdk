# Experimental features

## Pumble Socket Mode (`pumble_keys.pumble_app.socket_mode`)

Status: **experimental**. The API can change in any release without a
deprecation cycle.

### What it is

A Socket Mode receiver that dispatches Pumble events from an injected
WebSocket transport through the same typed event model and router as the
webhook path. Protocol behavior is anchored to the official source (see
`PUMBLE_SOCKET_MODE_PROTOCOL_EVIDENCE` in the module):

- the client sends `ping` every 25 seconds by default and ignores
  `pong` replies;
- frames are JSON objects shaped `{"payload": {...},
  "correlation_id": "..."}`;
- payloads with `messageType` `PUMBLE_EVENT` or `APP_EVENT` carry an
  `eventType` and a `body` (dict or JSON string).

### What it deliberately does not do

- **No bundled WebSocket transport.** `connect()` without a
  `create_socket` factory raises `PumbleSocketModeUnsupportedError`.
- **No reconnect or backoff policy.** A dropped connection stays
  dropped until the caller reconnects. Pretending this is solved would
  hide a production reliability decision.
- Unsupported message/event types raise
  `PumbleSocketModeUnsupportedError`; malformed frames raise
  `ValueError`.

### Injecting a transport

Install the optional extra:

```bash
pip install "pumble_keys_sdk[socket]"
```

Then adapt the `websockets` client to the small socket protocol
(`on(event, listener)`, `send(data)`, `close()`):

```python
import asyncio
import websockets

from pumble_keys.pumble_app.router import PumbleEventRouter
from pumble_keys.pumble_app.socket_mode import PumbleSocketModeReceiver


class WebsocketsAdapter:
    """Minimal adapter; reconnect policy stays YOUR decision."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._listeners: dict[str, list] = {}
        self._task = asyncio.ensure_future(self._run())

    def on(self, event, listener):
        self._listeners.setdefault(event, []).append(listener)

    def send(self, data):
        if getattr(self, "_ws", None) is not None:
            asyncio.ensure_future(self._ws.send(data))

    def close(self):
        self._task.cancel()

    async def _run(self):
        async with websockets.connect(self._url) as ws:
            self._ws = ws
            for listener in self._listeners.get("open", []):
                listener()
            async for message in ws:
                for listener in self._listeners.get("message", []):
                    outcome = listener(message)
                    if asyncio.iscoroutine(outcome):
                        await outcome


router = PumbleEventRouter()
receiver = PumbleSocketModeReceiver(
    get_websocket_url=fetch_socket_url,  # your API call
    router=router,
    create_socket=WebsocketsAdapter,
)
```

The example is illustrative, not production-ready: it has no
reconnects, no error backoff, and no frame-size guard.
