# Messages

## Overview

Send, edit, delete, react to, search, and list messages.

### Available Operations

* [send_message](#send_message) - Send a message to a channel
* [send_reply](#send_reply) - Reply to a message in a channel (thread)
* [dm_user](#dm_user) - Send a direct message to a user
* [dm_group](#dm_group) - Send a direct message to a group of users
* [fetch_message](#fetch_message) - Fetch a single message by ID
* [fetch_thread_replies](#fetch_thread_replies) - Fetch the replies of a thread
* [search_messages](#search_messages) - Search messages
* [delete_message](#delete_message) - Delete a message by ID
* [list_messages](#list_messages) - List messages in a channel
* [add_reaction](#add_reaction) - Add a reaction (emoji) to a message
* [remove_reaction](#remove_reaction) - Remove a reaction from a message
* [edit_message](#edit_message) - Edit a message

## send_message

Sends a text (or rich-text) message. Provide **either** `channelId`
(preferred) **or** `channel` (by name). If `threadRootId` is set, the
message is posted as a reply in that thread (equivalent to
`sendReply`).


### Example Usage

<!-- UsageSnippet language="python" operationID="sendMessage" method="post" path="/sendMessage" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.send_message(request={
        "channel_id": "bbbbbbbbbbbbbbbbbbbb0002",
        "text": "Hello world",
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                      | Type                                                                           | Required                                                                       | Description                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `request`                                                                      | [operations.SendMessageRequest](../../models/operations/sendmessagerequest.md) | :heavy_check_mark:                                                             | The request object to use for the request.                                     |
| `retries`                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)               | :heavy_minus_sign:                                                             | Configuration to override the default retry behavior of the client.            |

### Response

**[models.MessageRef](../../models/messageref.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## send_reply

Posts `text` as a reply in the thread rooted at `messageId`. Provide
**either** `channelId` (preferred) **or** `channel` (by name).


### Example Usage

<!-- UsageSnippet language="python" operationID="sendReply" method="post" path="/sendReply" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.send_reply(request={
        "channel_id": "bbbbbbbbbbbbbbbbbbbb0002",
        "message_id": "cccccccccccccccccccc0001",
        "text": "thread reply 1",
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                  | Type                                                                       | Required                                                                   | Description                                                                |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `request`                                                                  | [operations.SendReplyRequest](../../models/operations/sendreplyrequest.md) | :heavy_check_mark:                                                         | The request object to use for the request.                                 |
| `retries`                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)           | :heavy_minus_sign:                                                         | Configuration to override the default retry behavior of the client.        |

### Response

**[models.MessageRef](../../models/messageref.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## dm_user

Opens (or reuses) a 1-to-1 DM channel and posts a message. The
response's `channelId` is the DM channel — useful for follow-up
operations.


### Example Usage

<!-- UsageSnippet language="python" operationID="dmUser" method="post" path="/dmUser" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.dm_user(user_id="aaaaaaaaaaaaaaaaaaaa0002", text="Hi")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `user_id`                                                           | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `text`                                                              | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `as_bot`                                                            | *Optional[bool]*                                                    | :heavy_minus_sign:                                                  | N/A                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.MessageRef](../../models/messageref.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## dm_group

Opens (or reuses) a multi-party DM channel and posts a message.

### Example Usage

<!-- UsageSnippet language="python" operationID="dmGroup" method="post" path="/dmGroup" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.dm_group(user_ids=[
        "aaaaaaaaaaaaaaaaaaaa0002",
        "aaaaaaaaaaaaaaaaaaaa0003",
    ], text="Hi team")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `user_ids`                                                          | List[*str*]                                                         | :heavy_check_mark:                                                  | N/A                                                                 |
| `text`                                                              | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `as_bot`                                                            | *Optional[bool]*                                                    | :heavy_minus_sign:                                                  | N/A                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.MessageRef](../../models/messageref.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## fetch_message

Fetch a single message by ID

### Example Usage

<!-- UsageSnippet language="python" operationID="fetchMessage" method="get" path="/fetchMessage" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.fetch_message(message_id="cccccccccccccccccccc0001", channel_id="bbbbbbbbbbbbbbbbbbbb0001", channel="bbbbbbbbbbbbbbbbbbbb0001")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `message_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 | cccccccccccccccccccc0001                                            |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `channel`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.Message](../../models/message.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## fetch_thread_replies

Returns the replies posted in the thread rooted at `rootMessageId`,
as a flat array. Supports cursor pagination via the last reply's `id`.


### Example Usage

<!-- UsageSnippet language="python" operationID="fetchThreadReplies" method="get" path="/fetchThreadReplies" -->
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

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `root_message_id`                                                   | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 | cccccccccccccccccccc0001                                            |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `channel`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `cursor`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | ID of the last reply on the previous page.                          | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `limit`                                                             | *Optional[int]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 100                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[operations.FetchThreadRepliesResponse](../../models/operations/fetchthreadrepliesresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## search_messages

Searches messages by free text, sender, channel, and/or time window.
At least one of `text`, `from`, or `in` is required.

## Pagination
Cursor input is `beforeTs` (epoch ms); the next cursor is the
`timestampMilli` of the oldest hit in the current page. **Edge case**:
Pumble returns timestamps truncated to seconds, so messages sharing
the same `timestampMilli` that straddle a page boundary can be
skipped. For low-volume channels or `limit >= 10`, this is rarely
observed; for high-volume bursts use a smaller search window via
`afterTs` to bound the result set.


### Example Usage

<!-- UsageSnippet language="python" operationID="searchMessages" method="post" path="/searchMessages" -->
```python
from pumble_keys import PumbleSDK, models


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.search_messages(text="project update", limit=10, strategy=models.SearchStrategy.MOST_RECENT)

    while res is not None:
        # Handle items

        res = res.next()

```

### Parameters

| Parameter                                                                                              | Type                                                                                                   | Required                                                                                               | Description                                                                                            | Example                                                                                                |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `text`                                                                                                 | *Optional[str]*                                                                                        | :heavy_minus_sign:                                                                                     | N/A                                                                                                    |                                                                                                        |
| `from_`                                                                                                | List[*str*]                                                                                            | :heavy_minus_sign:                                                                                     | Filter by sender user IDs.                                                                             |                                                                                                        |
| `in_`                                                                                                  | List[*str*]                                                                                            | :heavy_minus_sign:                                                                                     | Filter by channel IDs or names.                                                                        |                                                                                                        |
| `limit`                                                                                                | *Optional[int]*                                                                                        | :heavy_minus_sign:                                                                                     | N/A                                                                                                    |                                                                                                        |
| `strategy`                                                                                             | [Optional[models.SearchStrategy]](../../models/searchstrategy.md)                                      | :heavy_minus_sign:                                                                                     | N/A                                                                                                    | MOST_RECENT                                                                                            |
| `before_ts`                                                                                            | *Optional[int]*                                                                                        | :heavy_minus_sign:                                                                                     | Restrict to messages with `timestampMilli` strictly less than this value (also the pagination cursor). |                                                                                                        |
| `after_ts`                                                                                             | *Optional[int]*                                                                                        | :heavy_minus_sign:                                                                                     | Restrict to messages with `timestampMilli` strictly greater than this value.                           |                                                                                                        |
| `retries`                                                                                              | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                       | :heavy_minus_sign:                                                                                     | Configuration to override the default retry behavior of the client.                                    |                                                                                                        |

### Response

**[operations.SearchMessagesResponse](../../models/operations/searchmessagesresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## delete_message

Delete a message by ID

### Example Usage

<!-- UsageSnippet language="python" operationID="deleteMessage" method="delete" path="/deleteMessage" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    pumble_sdk.messages.delete_message(message_id="bbbbbbbbbbbbbbbbbbbb0001", channel_id="bbbbbbbbbbbbbbbbbbbb0001", channel="bbbbbbbbbbbbbbbbbbbb0001")

    # Use the SDK ...

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `message_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `channel`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## list_messages

Retrieves a paginated list of messages from a channel. Pagination is
cursor-based: pass the `id` of the last returned message as the next
`cursor`. `hasMoreBefore` / `hasMoreAfter` indicate which direction
still has messages relative to the cursor.


### Example Usage

<!-- UsageSnippet language="python" operationID="listMessages" method="get" path="/listMessages" -->
```python
from pumble_keys import PumbleSDK, models


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.list_messages(channel_id="bbbbbbbbbbbbbbbbbbbb0001", channel="bbbbbbbbbbbbbbbbbbbb0001", cursor="bbbbbbbbbbbbbbbbbbbb0001", limit=100, strategy=models.ListMessagesStrategy.BEFORE)

    while res is not None:
        # Handle items

        res = res.next()

```

### Parameters

| Parameter                                                                                                                              | Type                                                                                                                                   | Required                                                                                                                               | Description                                                                                                                            | Example                                                                                                                                |
| -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `channel_id`                                                                                                                           | *Optional[str]*                                                                                                                        | :heavy_minus_sign:                                                                                                                     | N/A                                                                                                                                    | bbbbbbbbbbbbbbbbbbbb0001                                                                                                               |
| `channel`                                                                                                                              | *Optional[str]*                                                                                                                        | :heavy_minus_sign:                                                                                                                     | N/A                                                                                                                                    | bbbbbbbbbbbbbbbbbbbb0001                                                                                                               |
| `cursor`                                                                                                                               | *Optional[str]*                                                                                                                        | :heavy_minus_sign:                                                                                                                     | ID of the last message on the previous page.                                                                                           | bbbbbbbbbbbbbbbbbbbb0001                                                                                                               |
| `limit`                                                                                                                                | *Optional[int]*                                                                                                                        | :heavy_minus_sign:                                                                                                                     | N/A                                                                                                                                    | 100                                                                                                                                    |
| `strategy`                                                                                                                             | [Optional[models.ListMessagesStrategy]](../../models/listmessagesstrategy.md)                                                          | :heavy_minus_sign:                                                                                                                     | Pagination direction relative to `cursor`. When `cursor` is omitted the<br/>server returns the most-recent page regardless of `strategy`.<br/> | BEFORE                                                                                                                                 |
| `retries`                                                                                                                              | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                       | :heavy_minus_sign:                                                                                                                     | Configuration to override the default retry behavior of the client.                                                                    |                                                                                                                                        |

### Response

**[operations.ListMessagesResponse](../../models/operations/listmessagesresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## add_reaction

Adds a reaction code in `:emoji_name:` form. Pumble enforces the
colon-wrapped form server-side; bare names (e.g. `+1`) return 403.


### Example Usage

<!-- UsageSnippet language="python" operationID="addReaction" method="post" path="/addReaction" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.add_reaction(message_id="cccccccccccccccccccc0001", reaction=":+1:", channel_id="bbbbbbbbbbbbbbbbbbbb0002")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `message_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `reaction`                                                          | *str*                                                               | :heavy_check_mark:                                                  | Emoji code in `:emoji_name:` form (e.g. `:+1:`).                    |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 |
| `skin_tone`                                                         | *Optional[int]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[operations.AddReactionResponse](../../models/operations/addreactionresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## remove_reaction

Remove a reaction from a message

### Example Usage

<!-- UsageSnippet language="python" operationID="removeReaction" method="delete" path="/removeReaction" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.messages.remove_reaction(message_id="bbbbbbbbbbbbbbbbbbbb0001", reaction=":+1:", channel_id="bbbbbbbbbbbbbbbbbbbb0001")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `message_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `reaction`                                                          | *str*                                                               | :heavy_check_mark:                                                  | Emoji code in `:emoji_name:` form to remove.                        | :+1:                                                                |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[operations.RemoveReactionResponse](../../models/operations/removereactionresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## edit_message

Edit a message

### Example Usage

<!-- UsageSnippet language="python" operationID="editMessage" method="post" path="/editMessage" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    pumble_sdk.messages.edit_message(message_id="cccccccccccccccccccc0001", channel_id="bbbbbbbbbbbbbbbbbbbb0002", text="edited text", blocks=[
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "text",
                            "text": "Hello world",
                        },
                    ],
                },
            ],
        },
    ])

    # Use the SDK ...

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `message_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `channel_id`                                                        | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `text`                                                              | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 |
| `blocks`                                                            | List[[models.MessageBlock](../../models/messageblock.md)]           | :heavy_minus_sign:                                                  | N/A                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |