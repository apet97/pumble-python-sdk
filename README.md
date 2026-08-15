# pumble-python-sdk

Unofficial Python SDK, MCP server, and MCP App for the Pumble API Keys
addon. This project is independent. Pumble and CAKE.com do not endorse or
sponsor it.

Three layers: a Speakeasy-generated raw SDK (26 operations), a
value-typed async façade (no write retries, direct-read proof on every
write), and integration surfaces — CLI (`pumble-keys`), MCP server
(`pumble-keys-mcp`, stdio or Streamable HTTP, no SSE), an interactive
MCP App, webhook/`PumbleApp` helpers, and Pumble OAuth. One workspace
per deployment; the API key lives in the environment only.

## Documentation

- [Quickstart](docs/QUICKSTART.md) — install, authenticate, first calls
- [API reference map](docs/API-REFERENCE.md) — raw SDK vs façade vs CLI
- [MCP server](docs/MCP.md) — profiles, exact stdio/HTTP host configs
- [MCP write safety](docs/MCP-SAFETY.md) — preview/confirm, MRTR, raw gates
- [MCP App](docs/MCP-APP.md) — the one interactive app
- [Webhooks](docs/WEBHOOKS.md) · [Pumble OAuth](docs/PUMBLE-OAUTH.md)
- [Stability](docs/STABILITY.md) · [Migrating from TS](docs/MIGRATING-FROM-TS.md)
- [Live testing](docs/LIVE-TESTING.md) · [Parity matrix](PARITY_MATRIX.md)

Status: in development. See `IMPLEMENTATION_STATUS.md` for progress and
`SOURCE_BASELINE.md` for the anchored sources.

<!-- Start Summary [summary] -->
## Summary

Pumble API Addon documentation: Strongly-typed OpenAPI contract for the Pumble API-Keys add-on
(https://pumble.com/api). All response and request schemas in this
document were validated against the live API on 2026-05-21 against a
sacrificial workspace; field names, casing, and nullability reflect actual
server behavior.

## Authentication
All endpoints expect the workspace API key in the `ApiKey` request header.
Keys are issued from the Pumble web app at *Workspace settings → API keys*.

## Errors
The Pumble service emits **two** distinct error body shapes, depending on
which validation layer rejects the request:

1. `{ "error": "<string>" }` — legacy/free-form messages from path
   handlers (most common).
2. `{ "message": "<string>", "localizedMessage": "<string>", "code": <int> }`
   — structured validation errors from the framework layer.

Both are documented under the `Error` schema (a `oneOf` union). Generated
SDKs receive a single union type for typed error handling.
<!-- End Summary [summary] -->

<!-- Start Table of Contents [toc] -->
## Table of Contents
<!-- $toc-max-depth=2 -->
* [pumble-python-sdk](#pumble-python-sdk)
  * [Authentication](#authentication)
  * [Errors](#errors)
  * [SDK Installation](#sdk-installation)
  * [IDE Support](#ide-support)
  * [SDK Example Usage](#sdk-example-usage)
  * [Authentication](#authentication-1)
  * [Available Resources and Operations](#available-resources-and-operations)
  * [Pagination](#pagination)
  * [Retries](#retries)
  * [Error Handling](#error-handling)
  * [Server Selection](#server-selection)
  * [Custom HTTP Client](#custom-http-client)
  * [Resource Management](#resource-management)
  * [Debugging](#debugging)

<!-- End Table of Contents [toc] -->

<!-- Start SDK Installation [installation] -->
## SDK Installation

> [!TIP]
> To finish publishing your SDK to PyPI you must [run your first generation action](https://www.speakeasy.com/docs/github-setup#step-by-step-guide).


> [!NOTE]
> **Python version upgrade policy**
>
> Once a Python version reaches its [official end of life date](https://devguide.python.org/versions/), a 3-month grace period is provided for users to upgrade. Following this grace period, the minimum python version supported in the SDK will be updated.

The SDK can be installed with *uv*, *pip*, or *poetry* package managers.

### uv

*uv* is a fast Python package installer and resolver, designed as a drop-in replacement for pip and pip-tools. It's recommended for its speed and modern Python tooling capabilities.

```bash
uv add git+<UNSET>.git
```

### PIP

*PIP* is the default package installer for Python, enabling easy installation and management of packages from PyPI via the command line.

```bash
pip install git+<UNSET>.git
```

### Poetry

*Poetry* is a modern tool that simplifies dependency management and package publishing by using a single `pyproject.toml` file to handle project metadata and dependencies.

```bash
poetry add git+<UNSET>.git
```

### Shell and script usage with `uv`

You can use this SDK in a Python shell with [uv](https://docs.astral.sh/uv/) and the `uvx` command that comes with it like so:

```shell
uvx --from pumble_keys_sdk python
```

It's also possible to write a standalone Python script without needing to set up a whole project like so:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pumble_keys_sdk",
# ]
# ///

from pumble_keys import PumbleSDK

sdk = PumbleSDK(
  # SDK arguments
)

# Rest of script here...
```

Once that is saved to a file, you can run it with `uv run script.py` where
`script.py` can be replaced with the actual file name.
<!-- End SDK Installation [installation] -->

<!-- Start IDE Support [idesupport] -->
## IDE Support

### PyCharm

Generally, the SDK will work well with most IDEs out of the box. However, when using PyCharm, you can enjoy much better integration with Pydantic by installing an additional plugin.

- [PyCharm Pydantic Plugin](https://docs.pydantic.dev/latest/integrations/pycharm/)
<!-- End IDE Support [idesupport] -->

<!-- Start SDK Example Usage [usage] -->
## SDK Example Usage

### Example

```python
# Synchronous Example
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels()

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from pumble_keys import PumbleSDK

async def main():

    async with PumbleSDK(
        api_key_auth="<YOUR_API_KEY_HERE>",
    ) as pumble_sdk:

        res = await pumble_sdk.channels.list_channels_async()

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->

<!-- Start Authentication [security] -->
## Authentication

### Per-Client Security Schemes

This SDK supports the following security scheme globally:

| Name           | Type   | Scheme  |
| -------------- | ------ | ------- |
| `api_key_auth` | apiKey | API key |

To authenticate with the API the `api_key_auth` parameter must be set when initializing the SDK client instance. For example:
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels()

    # Handle response
    print(res)

```
<!-- End Authentication [security] -->

<!-- Start Available Resources and Operations [operations] -->
## Available Resources and Operations

<details open>
<summary>Available methods</summary>

### [Channels](docs/sdks/channels/README.md)

* [list_channels](docs/sdks/channels/README.md#list_channels) - List all channels
* [get_channel](docs/sdks/channels/README.md#get_channel) - Get channel details by ID or name
* [create_channel](docs/sdks/channels/README.md#create_channel) - Create a new channel
* [add_users_to_channel](docs/sdks/channels/README.md#add_users_to_channel) - Add users to a channel
* [remove_user_from_channel](docs/sdks/channels/README.md#remove_user_from_channel) - Remove a user from a channel

### [Messages](docs/sdks/messages/README.md)

* [send_message](docs/sdks/messages/README.md#send_message) - Send a message to a channel
* [send_reply](docs/sdks/messages/README.md#send_reply) - Reply to a message in a channel (thread)
* [dm_user](docs/sdks/messages/README.md#dm_user) - Send a direct message to a user
* [dm_group](docs/sdks/messages/README.md#dm_group) - Send a direct message to a group of users
* [fetch_message](docs/sdks/messages/README.md#fetch_message) - Fetch a single message by ID
* [fetch_thread_replies](docs/sdks/messages/README.md#fetch_thread_replies) - Fetch the replies of a thread
* [search_messages](docs/sdks/messages/README.md#search_messages) - Search messages
* [delete_message](docs/sdks/messages/README.md#delete_message) - Delete a message by ID
* [list_messages](docs/sdks/messages/README.md#list_messages) - List messages in a channel
* [add_reaction](docs/sdks/messages/README.md#add_reaction) - Add a reaction (emoji) to a message
* [remove_reaction](docs/sdks/messages/README.md#remove_reaction) - Remove a reaction from a message
* [edit_message](docs/sdks/messages/README.md#edit_message) - Edit a message

### [ScheduledMessages](docs/sdks/scheduledmessages/README.md)

* [create_scheduled_message](docs/sdks/scheduledmessages/README.md#create_scheduled_message) - Create a scheduled (future) message
* [fetch_scheduled_messages](docs/sdks/scheduledmessages/README.md#fetch_scheduled_messages) - Fetch a list of scheduled messages
* [fetch_scheduled_message](docs/sdks/scheduledmessages/README.md#fetch_scheduled_message) - Fetch a single scheduled message by ID
* [edit_scheduled_message](docs/sdks/scheduledmessages/README.md#edit_scheduled_message) - Edit a scheduled message
* [delete_scheduled_message](docs/sdks/scheduledmessages/README.md#delete_scheduled_message) - Delete a scheduled message

### [Users](docs/sdks/users/README.md)

* [list_users](docs/sdks/users/README.md#list_users) - List all workspace users
* [list_user_groups](docs/sdks/users/README.md#list_user_groups) - List workspace user groups
* [my_info](docs/sdks/users/README.md#my_info) - Get info about the authenticated user
* [custom_status](docs/sdks/users/README.md#custom_status) - Update the custom status of the authenticated user

</details>
<!-- End Available Resources and Operations [operations] -->

<!-- Start Pagination [pagination] -->
## Pagination

Some of the endpoints in this SDK support pagination. To use pagination, you make your SDK calls as usual, but the
returned response object will have a `Next` method that can be called to pull down the next group of results. If the
return value of `Next` is `None`, then there are no more pages to be fetched.

Here's an example of one such pagination call:
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.fetch_thread_replies(root_message_id="cccccccccccccccccccc0001", channel_id="bbbbbbbbbbbbbbbbbbbb0001", channel="bbbbbbbbbbbbbbbbbbbb0001", cursor="bbbbbbbbbbbbbbbbbbbb0001", limit=100)

    while res is not None:
        # Handle items

        res = res.next()

```
<!-- End Pagination [pagination] -->

<!-- Start Retries [retries] -->
## Retries

Some of the endpoints in this SDK support retries. If you use the SDK without any configuration, it will fall back to the default retry strategy provided by the API. However, the default retry strategy can be overridden on a per-operation basis, or across the entire SDK.

To change the default retry strategy for a single API call, simply provide a `RetryConfig` object to the call:
```python
from pumble_keys import PumbleSDK
from pumble_keys.utils import BackoffStrategy, RetryConfig


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels(,
        RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False))

    # Handle response
    print(res)

```

If you'd like to override the default retry strategy for all operations that support retries, you can use the `retry_config` optional parameter when initializing the SDK:
```python
from pumble_keys import PumbleSDK
from pumble_keys.utils import BackoffStrategy, RetryConfig


with PumbleSDK(
    retry_config=RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False),
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels()

    # Handle response
    print(res)

```
<!-- End Retries [retries] -->

<!-- Start Error Handling [errors] -->
## Error Handling

[`PumbleSDKBaseError`](./src/pumble_keys/models/errors/pumblesdkbaseerror.py) is the base class for all HTTP error responses. It has the following properties:

| Property           | Type             | Description                                                                             |
| ------------------ | ---------------- | --------------------------------------------------------------------------------------- |
| `err.message`      | `str`            | Error message                                                                           |
| `err.status_code`  | `int`            | HTTP response status code eg `404`                                                      |
| `err.headers`      | `httpx.Headers`  | HTTP response headers                                                                   |
| `err.body`         | `str`            | HTTP body. Can be empty string if no body is returned.                                  |
| `err.raw_response` | `httpx.Response` | Raw HTTP response                                                                       |
| `err.data`         |                  | Optional. Some errors may contain structured data. [See Error Classes](#error-classes). |

### Example
```python
from pumble_keys import PumbleSDK, models


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:
    res = None
    try:

        res = pumble_sdk.channels.list_channels()

        # Handle response
        print(res)


    except models.errors.PumbleSDKBaseError as e:
        # The base class for HTTP error responses
        print(e.message)
        print(e.status_code)
        print(e.body)
        print(e.headers)
        print(e.raw_response)

        # Depending on the method different errors may be thrown
        if isinstance(e, models.errors.LegacyError):
            print(e.data.error)  # str
```

### Error Classes
**Primary errors:**
* [`PumbleSDKBaseError`](./src/pumble_keys/models/errors/pumblesdkbaseerror.py): The base class for HTTP error responses.
  * [`LegacyError`](./src/pumble_keys/models/errors/legacyerror.py): Free-form error message from the request handler layer. Status code `403`.
  * [`StructuredError`](./src/pumble_keys/models/errors/structurederror.py): Structured validation error from the framework layer. Status code `403`.

<details><summary>Less common errors (5)</summary>

<br />

**Network errors:**
* [`httpx.RequestError`](https://www.python-httpx.org/exceptions/#httpx.RequestError): Base class for request errors.
    * [`httpx.ConnectError`](https://www.python-httpx.org/exceptions/#httpx.ConnectError): HTTP client was unable to make a request to a server.
    * [`httpx.TimeoutException`](https://www.python-httpx.org/exceptions/#httpx.TimeoutException): HTTP request timed out.


**Inherit from [`PumbleSDKBaseError`](./src/pumble_keys/models/errors/pumblesdkbaseerror.py)**:
* [`ResponseValidationError`](./src/pumble_keys/models/errors/responsevalidationerror.py): Type mismatch between the response data and the expected Pydantic model. Provides access to the Pydantic validation error via the `cause` attribute.

</details>
<!-- End Error Handling [errors] -->

<!-- Start Server Selection [server] -->
## Server Selection

### Override Server URL Per-Client

The default server can be overridden globally by passing a URL to the `server_url: str` optional parameter when initializing the SDK client instance. For example:
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    server_url="https://pumble-api-keys.addons.marketplace.cake.com",
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels()

    # Handle response
    print(res)

```
<!-- End Server Selection [server] -->

<!-- Start Custom HTTP Client [http-client] -->
## Custom HTTP Client

The Python SDK makes API calls using the [httpx](https://www.python-httpx.org/) HTTP library.  In order to provide a convenient way to configure timeouts, cookies, proxies, custom headers, and other low-level configuration, you can initialize the SDK client with your own HTTP client instance.
Depending on whether you are using the sync or async version of the SDK, you can pass an instance of `HttpClient` or `AsyncHttpClient` respectively, which are Protocol's ensuring that the client has the necessary methods to make API calls.
This allows you to wrap the client with your own custom logic, such as adding custom headers, logging, or error handling, or you can just pass an instance of `httpx.Client` or `httpx.AsyncClient` directly.

For example, you could specify a header for every request that this sdk makes as follows:
```python
from pumble_keys import PumbleSDK
import httpx

http_client = httpx.Client(headers={"x-custom-header": "someValue"})
s = PumbleSDK(client=http_client)
```

or you could wrap the client with your own custom logic:
```python
from pumble_keys import PumbleSDK
from pumble_keys.httpclient import AsyncHttpClient
import httpx

class CustomClient(AsyncHttpClient):
    client: AsyncHttpClient

    def __init__(self, client: AsyncHttpClient):
        self.client = client

    async def send(
        self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: Union[
            httpx._types.AuthTypes, httpx._client.UseClientDefault, None
        ] = httpx.USE_CLIENT_DEFAULT,
        follow_redirects: Union[
            bool, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        request.headers["Client-Level-Header"] = "added by client"

        return await self.client.send(
            request, stream=stream, auth=auth, follow_redirects=follow_redirects
        )

    def build_request(
        self,
        method: str,
        url: httpx._types.URLTypes,
        *,
        content: Optional[httpx._types.RequestContent] = None,
        data: Optional[httpx._types.RequestData] = None,
        files: Optional[httpx._types.RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[httpx._types.QueryParamTypes] = None,
        headers: Optional[httpx._types.HeaderTypes] = None,
        cookies: Optional[httpx._types.CookieTypes] = None,
        timeout: Union[
            httpx._types.TimeoutTypes, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
        extensions: Optional[httpx._types.RequestExtensions] = None,
    ) -> httpx.Request:
        return self.client.build_request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )

s = PumbleSDK(async_client=CustomClient(httpx.AsyncClient()))
```
<!-- End Custom HTTP Client [http-client] -->

<!-- Start Resource Management [resource-management] -->
## Resource Management

The `PumbleSDK` class implements the context manager protocol and registers a finalizer function to close the underlying sync and async HTTPX clients it uses under the hood. This will close HTTP connections, release memory and free up other resources held by the SDK. In short-lived Python programs and notebooks that make a few SDK method calls, resource management may not be a concern. However, in longer-lived programs, it is beneficial to create a single SDK instance via a [context manager][context-manager] and reuse it across the application.

[context-manager]: https://docs.python.org/3/reference/datamodel.html#context-managers

```python
from pumble_keys import PumbleSDK
def main():

    with PumbleSDK(
        api_key_auth="<YOUR_API_KEY_HERE>",
    ) as pumble_sdk:
        # Rest of application here...


# Or when using async:
async def amain():

    async with PumbleSDK(
        api_key_auth="<YOUR_API_KEY_HERE>",
    ) as pumble_sdk:
        # Rest of application here...
```
<!-- End Resource Management [resource-management] -->

<!-- Start Debugging [debug] -->
## Debugging

You can setup your SDK to emit debug logs for SDK requests and responses.

You can pass your own logger class directly into your SDK.
```python
from pumble_keys import PumbleSDK
import logging

logging.basicConfig(level=logging.DEBUG)
s = PumbleSDK(debug_logger=logging.getLogger("pumble_keys"))
```
<!-- End Debugging [debug] -->

<!-- Placeholder for Future Speakeasy SDK Sections -->
