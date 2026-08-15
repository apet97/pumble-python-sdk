# Quickstart

Unofficial project. Pumble and CAKE.com do not endorse or sponsor it.

## Install

```bash
pip install pumble_keys_sdk        # or: uv add pumble_keys_sdk
```

Python 3.11–3.14. One workspace per deployment: every credential is a
single workspace's API key, issued in the Pumble web app at
*Workspace settings → API keys*.

## Authenticate

Put the key in the environment — never in code, argv, or files:

```bash
export PUMBLE_API_KEY=...          # or PUMBLE_API_KEY_FILE=/run/secrets/key
```

## Call the SDK (async façade)

```python
import asyncio
import os

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.extensions.results import FacadeFailure


async def main() -> None:
    client = create_pumble_client(os.environ["PUMBLE_API_KEY"])
    try:
        me = await client.identity.me()
        if isinstance(me, FacadeFailure):
            print("failed:", me.summary)
            return
        print("authenticated as", me.name)

        found = await client.channels.find("general")
        if not isinstance(found, FacadeFailure):
            receipt = await client.messages.send(
                channel_id=found.channel.id, text="hello from Python"
            )
            if not isinstance(receipt, FacadeFailure):
                # Direct-read proof: the message was read back by ID.
                print(receipt.summary, receipt.verification.state)
    finally:
        await client.aclose()


asyncio.run(main())
```

Failures are values (`FacadeFailure`), not exceptions. Writes are never
retried and every write receipt carries a direct-read verification.

## CLI

```bash
pumble-keys doctor
pumble-keys channels list
pumble-keys send general "hello from the CLI"
```

## MCP server

```bash
pumble-keys-mcp                    # stdio, curated profile
```

See [MCP.md](MCP.md) for profiles, host configs, and the Streamable
HTTP deployment; [MCP-SAFETY.md](MCP-SAFETY.md) for the write-safety
model; [MCP-APP.md](MCP-APP.md) for the interactive app.

## Webhooks / Pumble app

See [WEBHOOKS.md](WEBHOOKS.md) and [PUMBLE-OAUTH.md](PUMBLE-OAUTH.md).
