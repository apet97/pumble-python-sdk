# SendReplyRequestBody1


## Fields

| Field                                                    | Type                                                     | Required                                                 | Description                                              |
| -------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| `channel_id`                                             | *str*                                                    | :heavy_check_mark:                                       | N/A                                                      |
| `channel`                                                | *Optional[str]*                                          | :heavy_minus_sign:                                       | N/A                                                      |
| `message_id`                                             | *str*                                                    | :heavy_check_mark:                                       | ID of the message to reply to (the thread root).         |
| `text`                                                   | *str*                                                    | :heavy_check_mark:                                       | N/A                                                      |
| `also_send_to_channel`                                   | *Optional[bool]*                                         | :heavy_minus_sign:                                       | If true, also broadcast the reply to the parent channel. |
| `as_bot`                                                 | *Optional[bool]*                                         | :heavy_minus_sign:                                       | N/A                                                      |