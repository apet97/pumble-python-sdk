# StructuredError

Structured validation error from the framework layer.


## Fields

| Field                                                                 | Type                                                                  | Required                                                              | Description                                                           | Example                                                               |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `message`                                                             | *str*                                                                 | :heavy_check_mark:                                                    | Raw error message.                                                    | [Allowed values are PUBLIC\|PRIVATE]                                  |
| `localized_message`                                                   | *str*                                                                 | :heavy_check_mark:                                                    | Localized variant of `message` (often identical for English clients). | [Allowed values are PUBLIC\|PRIVATE]                                  |
| `code`                                                                | *int*                                                                 | :heavy_check_mark:                                                    | Internal error code.                                                  | 400000                                                                |