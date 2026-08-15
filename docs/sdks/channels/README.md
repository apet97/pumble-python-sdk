# Channels

## Overview

Channel discovery, creation, and membership management.

### Available Operations

* [list_channels](#list_channels) - List all channels
* [get_channel](#get_channel) - Get channel details by ID or name
* [create_channel](#create_channel) - Create a new channel
* [add_users_to_channel](#add_users_to_channel) - Add users to a channel
* [remove_user_from_channel](#remove_user_from_channel) - Remove a user from a channel

## list_channels

Returns every channel visible to the API key.

### Example Usage

<!-- UsageSnippet language="python" operationID="listChannels" method="get" path="/listChannels" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels()

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[List[models.ChannelListEntry]](../../models/.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## get_channel

Provide **either** `channelId` (preferred) **or** `channel` (by name).
The response wraps the channel in `{ channel: ... }` (mirroring
`listChannels`), without the `pinnedMessages` / `users` fields.


### Example Usage

<!-- UsageSnippet language="python" operationID="getChannel" method="get" path="/getChannel" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.get_channel(channel_id="bbbbbbbbbbbbbbbbbbbb0001", channel="general")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `channel`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | general                                                             |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[operations.GetChannelResponse](../../models/operations/getchannelresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## create_channel

Creates a new public or private channel. The caller becomes the
channel creator and is added as a member.


### Example Usage

<!-- UsageSnippet language="python" operationID="createChannel" method="post" path="/createChannel" -->
```python
from pumble_keys import PumbleSDK, models


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.create_channel(name="project-updates", type_=models.ChannelType.PUBLIC, description="integration testing channel - safe to delete")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                  | Type                                                                                       | Required                                                                                   | Description                                                                                | Example                                                                                    |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `name`                                                                                     | *str*                                                                                      | :heavy_check_mark:                                                                         | Channel name. Pumble normalizes this server-side<br/>(lower-cases, replaces spaces with `-`).<br/> | project-updates                                                                            |
| `type`                                                                                     | [models.ChannelType](../../models/channeltype.md)                                          | :heavy_check_mark:                                                                         | Visibility of a channel.                                                                   | PUBLIC                                                                                     |
| `description`                                                                              | *Optional[str]*                                                                            | :heavy_minus_sign:                                                                         | Optional channel description.                                                              |                                                                                            |
| `retries`                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                           | :heavy_minus_sign:                                                                         | Configuration to override the default retry behavior of the client.                        |                                                                                            |

### Response

**[models.ChannelRef](../../models/channelref.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## add_users_to_channel

Add users to a channel

### Example Usage

<!-- UsageSnippet language="python" operationID="addUsersToChannel" method="post" path="/addUsersToChannel" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    pumble_sdk.channels.add_users_to_channel(channel_id="bbbbbbbbbbbbbbbbbbbb0001", user_ids=[
        "aaaaaaaaaaaaaaaaaaaa0002",
    ])

    # Use the SDK ...

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `channel_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `user_ids`                                                          | List[*str*]                                                         | :heavy_check_mark:                                                  | N/A                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## remove_user_from_channel

Remove a user from a channel

### Example Usage

<!-- UsageSnippet language="python" operationID="removeUserFromChannel" method="post" path="/removeUserFromChannel" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    pumble_sdk.channels.remove_user_from_channel(channel_id="bbbbbbbbbbbbbbbbbbbb0001", user_id="aaaaaaaaaaaaaaaaaaaa0002")

    # Use the SDK ...

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `channel_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `user_id`                                                           | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |