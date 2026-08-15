# ScheduledMessages

## Overview

Manage messages queued for future delivery, with optional recurrence.

### Available Operations

* [create_scheduled_message](#create_scheduled_message) - Create a scheduled (future) message
* [fetch_scheduled_messages](#fetch_scheduled_messages) - Fetch a list of scheduled messages
* [fetch_scheduled_message](#fetch_scheduled_message) - Fetch a single scheduled message by ID
* [edit_scheduled_message](#edit_scheduled_message) - Edit a scheduled message
* [delete_scheduled_message](#delete_scheduled_message) - Delete a scheduled message

## create_scheduled_message

Create a scheduled (future) message

### Example Usage

<!-- UsageSnippet language="python" operationID="createScheduledMessage" method="post" path="/createScheduledMessage" -->
```python
from pumble_keys import PumbleSDK, models


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.scheduled_messages.create_scheduled_message(channel_id="bbbbbbbbbbbbbbbbbbbb0002", text="Daily standup reminder", send_at=1893459600000, blocks=[
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
    ], recurrence={
        "recurrence_type": models.RecurrenceType.BUSINESSDAYS,
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                           | Type                                                                                | Required                                                                            | Description                                                                         | Example                                                                             |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `channel_id`                                                                        | *str*                                                                               | :heavy_check_mark:                                                                  | N/A                                                                                 |                                                                                     |
| `text`                                                                              | *str*                                                                               | :heavy_check_mark:                                                                  | N/A                                                                                 |                                                                                     |
| `send_at`                                                                           | *int*                                                                               | :heavy_check_mark:                                                                  | Delivery moment (epoch ms). Must be in the future.                                  |                                                                                     |
| `blocks`                                                                            | List[[models.MessageBlock](../../models/messageblock.md)]                           | :heavy_minus_sign:                                                                  | N/A                                                                                 |                                                                                     |
| `thread_root_id`                                                                    | *Optional[str]*                                                                     | :heavy_minus_sign:                                                                  | If set, the scheduled message will be sent as a thread reply.                       |                                                                                     |
| `also_send_to_channel`                                                              | *Optional[bool]*                                                                    | :heavy_minus_sign:                                                                  | N/A                                                                                 |                                                                                     |
| `recurrence`                                                                        | [Optional[models.Recurrence]](../../models/recurrence.md)                           | :heavy_minus_sign:                                                                  | N/A                                                                                 | {<br/>"recurrenceType": "WEEKLY",<br/>"endAfterOccurrences": 10,<br/>"endDate": 1893459600000<br/>} |
| `retries`                                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                    | :heavy_minus_sign:                                                                  | Configuration to override the default retry behavior of the client.                 |                                                                                     |

### Response

**[models.ScheduledMessageRef](../../models/scheduledmessageref.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## fetch_scheduled_messages

Returns scheduled messages for the workspace (optionally filtered to
a single channel). Cursor pagination uses the last scheduled
message's `id`.


### Example Usage

<!-- UsageSnippet language="python" operationID="fetchScheduledMessages" method="get" path="/fetchScheduledMessages" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.scheduled_messages.fetch_scheduled_messages(channel_id="bbbbbbbbbbbbbbbbbbbb0001", cursor="bbbbbbbbbbbbbbbbbbbb0001", limit=100)

    while res is not None:
        # Handle items

        res = res.next()

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `channel_id`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `cursor`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `limit`                                                             | *Optional[int]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 100                                                                 |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[operations.FetchScheduledMessagesResponse](../../models/operations/fetchscheduledmessagesresponse.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## fetch_scheduled_message

Fetch a single scheduled message by ID

### Example Usage

<!-- UsageSnippet language="python" operationID="fetchScheduledMessage" method="get" path="/fetchScheduledMessage" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.scheduled_messages.fetch_scheduled_message(scheduled_message_id="bbbbbbbbbbbbbbbbbbbb0001")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `scheduled_message_id`                                              | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ScheduledMessage](../../models/scheduledmessage.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## edit_scheduled_message

Updates a queued scheduled message. **All of** `scheduledMessageId`,
`channelId`, `text`, and `sendAt` are required server-side — omitting
any of them returns 403 with `[must not be null]`. Pass the existing
`sendAt` value verbatim if you don't want to reschedule.


### Example Usage

<!-- UsageSnippet language="python" operationID="editScheduledMessage" method="post" path="/editScheduledMessage" -->
```python
from pumble_keys import PumbleSDK, models


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.scheduled_messages.edit_scheduled_message(scheduled_message_id="dddddddddddddddddddd0001", channel_id="bbbbbbbbbbbbbbbbbbbb0002", text="edited reminder", send_at=1893459600000, blocks=[
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
    ], recurrence={
        "recurrence_type": models.RecurrenceType.WEEKLY,
        "end_after_occurrences": 10,
        "end_date": 1893459600000,
    })

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                           | Type                                                                                | Required                                                                            | Description                                                                         | Example                                                                             |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `scheduled_message_id`                                                              | *str*                                                                               | :heavy_check_mark:                                                                  | N/A                                                                                 |                                                                                     |
| `channel_id`                                                                        | *str*                                                                               | :heavy_check_mark:                                                                  | N/A                                                                                 |                                                                                     |
| `text`                                                                              | *str*                                                                               | :heavy_check_mark:                                                                  | N/A                                                                                 |                                                                                     |
| `send_at`                                                                           | *int*                                                                               | :heavy_check_mark:                                                                  | Delivery moment (epoch ms). Required even if unchanged.                             |                                                                                     |
| `blocks`                                                                            | List[[models.MessageBlock](../../models/messageblock.md)]                           | :heavy_minus_sign:                                                                  | N/A                                                                                 |                                                                                     |
| `recurrence`                                                                        | [Optional[models.Recurrence]](../../models/recurrence.md)                           | :heavy_minus_sign:                                                                  | N/A                                                                                 | {<br/>"recurrenceType": "WEEKLY",<br/>"endAfterOccurrences": 10,<br/>"endDate": 1893459600000<br/>} |
| `retries`                                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                    | :heavy_minus_sign:                                                                  | Configuration to override the default retry behavior of the client.                 |                                                                                     |

### Response

**[models.ScheduledMessage](../../models/scheduledmessage.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## delete_scheduled_message

Delete a scheduled message

### Example Usage

<!-- UsageSnippet language="python" operationID="deleteScheduledMessage" method="delete" path="/deleteScheduledMessage" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    pumble_sdk.scheduled_messages.delete_scheduled_message(scheduled_message_id="bbbbbbbbbbbbbbbbbbbb0001")

    # Use the SDK ...

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `scheduled_message_id`                                              | *str*                                                               | :heavy_check_mark:                                                  | N/A                                                                 | bbbbbbbbbbbbbbbbbbbb0001                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |