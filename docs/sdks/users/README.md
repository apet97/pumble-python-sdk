# Users

## Overview

User directory, user groups, and per-user state (status, identity).

### Available Operations

* [list_users](#list_users) - List all workspace users
* [list_user_groups](#list_user_groups) - List workspace user groups
* [my_info](#my_info) - Get info about the authenticated user
* [custom_status](#custom_status) - Update the custom status of the authenticated user

## list_users

Returns every user in the workspace as a flat array.

### Example Usage

<!-- UsageSnippet language="python" operationID="listUsers" method="get" path="/listUsers" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.users.list_users()

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[List[models.User]](../../models/.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## list_user_groups

List workspace user groups

### Example Usage

<!-- UsageSnippet language="python" operationID="listUserGroups" method="get" path="/listUserGroups" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.users.list_user_groups()

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[List[models.UserGroup]](../../models/.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## my_info

Returns the user record for whichever account owns the API key.

### Example Usage

<!-- UsageSnippet language="python" operationID="myInfo" method="get" path="/myInfo" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.users.my_info()

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.User](../../models/user.md)**

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |

## custom_status

Sets or clears the user's custom status. **Both** `code` and
`expiresAt` are required server-side. Pass an `expiresAt` far in the
future for a "don't auto-clear" effect; pass a past timestamp to
immediately clear.


### Example Usage

<!-- UsageSnippet language="python" operationID="customStatus" method="post" path="/customStatus" -->
```python
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    pumble_sdk.users.custom_status(code=":beach_with_umbrella:", expires_at=1893456000000, status="Time off")

    # Use the SDK ...

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `code`                                                              | *str*                                                               | :heavy_check_mark:                                                  | Emoji code in `:emoji_name:` form.                                  | :beach_with_umbrella:                                               |
| `expires_at`                                                        | *int*                                                               | :heavy_check_mark:                                                  | Epoch-ms moment to clear the status (0 = never).                    |                                                                     |
| `status`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | Free-form status text.                                              | Time off                                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Errors

| Error Type                    | Status Code                   | Content Type                  |
| ----------------------------- | ----------------------------- | ----------------------------- |
| models.errors.LegacyError     | 403                           | application/json              |
| models.errors.StructuredError | 403                           | application/json              |
| models.errors.PumbleSDKError  | 4XX, 5XX                      | \*/\*                         |