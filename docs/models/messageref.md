# MessageRef

Lightweight reference returned by write operations.


## Fields

| Field                                             | Type                                              | Required                                          | Description                                       | Example                                           |
| ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------- |
| `id`                                              | *str*                                             | :heavy_check_mark:                                | Server-assigned message identifier (24-char hex). | cccccccccccccccccccc0001                          |
| `channel_id`                                      | *str*                                             | :heavy_check_mark:                                | ID of the channel that contains the message.      | bbbbbbbbbbbbbbbbbbbb0002                          |