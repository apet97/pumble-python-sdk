# ScheduledMessageRecurrence


## Fields

| Field                                                | Type                                                 | Required                                             | Description                                          | Example                                              |
| ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `recurrence_type`                                    | [models.RecurrenceType](../models/recurrencetype.md) | :heavy_check_mark:                                   | N/A                                                  | WEEKLY                                               |
| `end_after_occurrences`                              | *Optional[int]*                                      | :heavy_minus_sign:                                   | N/A                                                  | 10                                                   |
| `end_date`                                           | *Optional[int]*                                      | :heavy_minus_sign:                                   | Epoch-ms after which the recurrence stops.           | 1893459600000                                        |