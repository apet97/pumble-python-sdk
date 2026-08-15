# CustomStatusRequest


## Fields

| Field                                            | Type                                             | Required                                         | Description                                      | Example                                          |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| `code`                                           | *str*                                            | :heavy_check_mark:                               | Emoji code in `:emoji_name:` form.               | :beach_with_umbrella:                            |
| `status`                                         | *Optional[str]*                                  | :heavy_minus_sign:                               | Free-form status text.                           | Time off                                         |
| `expires_at`                                     | *int*                                            | :heavy_check_mark:                               | Epoch-ms moment to clear the status (0 = never). |                                                  |