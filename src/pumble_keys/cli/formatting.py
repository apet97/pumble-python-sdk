"""Output helpers for the ``pumble-keys`` CLI.

JSON goes to stdout for machines; human-readable listings go to stdout;
success prose and diagnostics go to stderr. Formats are ported from the
TypeScript CLI so scripted consumers see familiar shapes.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from typing import Any

import pydantic


def to_jsonable(value: Any) -> Any:
    if isinstance(value, pydantic.BaseModel):
        try:
            return value.model_dump(by_alias=True, mode="json", exclude_none=True)
        except (ValueError, TypeError):
            # Receipts may carry non-pydantic objects in Any fields.
            return {
                key: to_jsonable(item)
                for key, item in dict(value).items()
                if item is not None
            }
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: to_jsonable(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if type(value).__module__ == "types" and hasattr(value, "__dict__"):
        return {key: to_jsonable(item) for key, item in vars(value).items()}
    return value


def print_json(value: Any) -> None:
    sys.stdout.write(json.dumps(to_jsonable(value), indent=2, default=str) + "\n")


def print_line(line: str) -> None:
    sys.stdout.write(line + "\n")


def print_diagnostic(line: str) -> None:
    sys.stderr.write(line + "\n")


def one_line(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text if text is not None else "")).strip()


def mask_key(key: str) -> str:
    if len(key) >= 4:
        return "*" * max(0, len(key) - 4) + key[-4:]
    return "(none)"


def format_channel(channel: Any) -> str:
    channel_type = str(getattr(channel, "channel_type", "") or "")
    return f"#{channel.name}\t{channel.id}\t{channel_type}"


def format_user(user: Any) -> str:
    return f"{user.name} <{user.email}>\t{user.id}"


def _iso(timestamp_milli: Any) -> str:
    if isinstance(timestamp_milli, int):
        return (
            datetime.fromtimestamp(timestamp_milli / 1000, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
    return ""


def format_timestamp(message: Any) -> str:
    timestamp = getattr(message, "timestamp", None)
    if isinstance(timestamp, datetime):
        return timestamp.isoformat().replace("+00:00", "Z")
    if isinstance(timestamp, str):
        return timestamp
    return _iso(getattr(message, "timestamp_milli", None))


def format_message_like(message: Any) -> str:
    ts = format_timestamp(message)
    return f"{ts}\t{message.channel_id}\t{message.author}: {one_line(message.text)}"


def format_scheduled(message: Any) -> str:
    send_at = getattr(message, "send_at", None)
    when = _iso(send_at) or str(send_at)
    return f"{message.id}\t{message.channel_id}\t{when}\t{one_line(message.text)}"


def normalise_emoji_code(code: str) -> str:
    """CLI convenience only: wrap a bare emoji name in colons."""
    if code.startswith(":") and code.endswith(":") and len(code) >= 2:
        return code
    return f":{code.strip(':')}:"
