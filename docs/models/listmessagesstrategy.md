# ListMessagesStrategy

Pagination direction relative to `cursor`. When `cursor` is omitted the
server returns the most-recent page regardless of `strategy`.


## Example Usage

```python
from pumble_keys.models import ListMessagesStrategy

value = ListMessagesStrategy.BEFORE
```


## Values

| Name     | Value    |
| -------- | -------- |
| `BEFORE` | BEFORE   |
| `AFTER`  | AFTER    |
| `AROUND` | AROUND   |