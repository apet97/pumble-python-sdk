# FetchThreadRepliesRequest


## Fields

| Field                                      | Type                                       | Required                                   | Description                                | Example                                    |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------ | ------------------------------------------ | ------------------------------------------ |
| `root_message_id`                          | *str*                                      | :heavy_check_mark:                         | N/A                                        | cccccccccccccccccccc0001                   |
| `channel_id`                               | *Optional[str]*                            | :heavy_minus_sign:                         | N/A                                        | bbbbbbbbbbbbbbbbbbbb0001                   |
| `channel`                                  | *Optional[str]*                            | :heavy_minus_sign:                         | N/A                                        | bbbbbbbbbbbbbbbbbbbb0001                   |
| `cursor`                                   | *Optional[str]*                            | :heavy_minus_sign:                         | ID of the last reply on the previous page. | bbbbbbbbbbbbbbbbbbbb0001                   |
| `limit`                                    | *Optional[int]*                            | :heavy_minus_sign:                         | N/A                                        | 100                                        |