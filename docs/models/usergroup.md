# UserGroup


## Fields

| Field                    | Type                     | Required                 | Description              | Example                  |
| ------------------------ | ------------------------ | ------------------------ | ------------------------ | ------------------------ |
| `id`                     | *str*                    | :heavy_check_mark:       | N/A                      | eeeeeeeeeeeeeeeeeeee0001 |
| `name`                   | *str*                    | :heavy_check_mark:       | N/A                      | engineering              |
| `handle`                 | *str*                    | :heavy_check_mark:       | N/A                      | eng                      |
| `description`            | *OptionalNullable[str]*  | :heavy_minus_sign:       | N/A                      |                          |
| `disabled`               | *Optional[bool]*         | :heavy_minus_sign:       | N/A                      |                          |
| `created_by`             | *Optional[str]*          | :heavy_minus_sign:       | N/A                      |                          |
| `workspace_id`           | *str*                    | :heavy_check_mark:       | N/A                      |                          |
| `workspace_user_ids`     | List[*str*]              | :heavy_minus_sign:       | N/A                      |                          |