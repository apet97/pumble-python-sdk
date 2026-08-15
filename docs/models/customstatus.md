# CustomStatus

A user's custom status (the value, not the update payload).


## Fields

| Field                                                | Type                                                 | Required                                             | Description                                          | Example                                              |
| ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `code`                                               | *Optional[str]*                                      | :heavy_minus_sign:                                   | Emoji code in `:emoji_name:` form.                   | :beach_with_umbrella:                                |
| `status`                                             | *Optional[str]*                                      | :heavy_minus_sign:                                   | Free-form status text.                               | Time off                                             |
| `expiration`                                         | *Optional[str]*                                      | :heavy_minus_sign:                                   | Expiration mode (e.g. `custom`, `dont_clear`).       | custom                                               |
| `expires_at`                                         | *Optional[int]*                                      | :heavy_minus_sign:                                   | Epoch-ms moment the status auto-clears (0 if never). | 1893456000000                                        |
| `show_until`                                         | *Optional[bool]*                                     | :heavy_minus_sign:                                   | N/A                                                  | true                                                 |