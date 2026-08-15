# MessageList

Paginated message list. `hasMoreBefore` / `hasMoreAfter` are nullable —
the server returns `null` for the side that's irrelevant to the chosen
`strategy` (e.g. `strategy=AFTER` yields `hasMoreBefore=null`).



## Fields

| Field                                        | Type                                         | Required                                     | Description                                  |
| -------------------------------------------- | -------------------------------------------- | -------------------------------------------- | -------------------------------------------- |
| `messages`                                   | List[[models.Message](../models/message.md)] | :heavy_check_mark:                           | N/A                                          |
| `has_more_before`                            | *OptionalNullable[bool]*                     | :heavy_minus_sign:                           | N/A                                          |
| `has_more_after`                             | *OptionalNullable[bool]*                     | :heavy_minus_sign:                           | N/A                                          |