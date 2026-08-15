"""``pumble-keys`` — one-shot CLI over the curated async façade.

Ported from the TypeScript ``pumble-keys-cli.mjs`` with the plan's
safety improvement: there is NO plaintext API-key command-line flag.
Credential precedence is key file, stdin, then the ``PUMBLE_API_KEY``
environment variable — process listings leak argv values.

Exit codes: 0 success, 1 operation failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from typing import Any

from pumble_keys.cli import formatting as fmt
from pumble_keys.extensions.client import PumbleClient, create_pumble_client
from pumble_keys.extensions.results import FacadeFailure

DEFAULT_BASE_URL = "https://pumble-api-keys.addons.marketplace.cake.com"
_ID_RE = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)


class UsageError(Exception):
    pass


class CliError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    """Argparse that raises ``UsageError`` instead of exiting."""

    def error(self, message: str) -> Any:
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="pumble-keys",
        description="One-shot CLI for the Pumble API-Keys SDK.",
        epilog=(
            "Credentials: pass --api-key-file, --api-key-stdin, or set "
            "PUMBLE_API_KEY. There is deliberately no plaintext key flag."
        ),
    )
    parser.add_argument("--api-key-file", help="read the API key from a file")
    parser.add_argument(
        "--api-key-stdin",
        action="store_true",
        help="read the API key from stdin",
    )
    parser.add_argument("--base-url", default=None, help="API base URL")
    parser.add_argument("--timeout-ms", type=int, default=None)
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress the one-line success message for write commands",
    )
    parser.add_argument(
        "--json", action="store_true", help="machine-readable JSON on stdout"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="show masked key and base URL")
    sub.add_parser("whoami", help="show the authenticated user")

    channels = sub.add_parser("channels").add_subparsers(dest="subcommand")
    channels.add_parser("list")
    find_channel = channels.add_parser("find")
    find_channel.add_argument("query")
    create_channel = channels.add_parser("create")
    create_channel.add_argument("name")
    create_channel.add_argument("--private", action="store_true")

    users = sub.add_parser("users").add_subparsers(dest="subcommand")
    find_user = users.add_parser("find")
    find_user.add_argument("query")

    send = sub.add_parser("send")
    send.add_argument("channel")
    send.add_argument("text", nargs="+")

    dm = sub.add_parser("dm")
    dm.add_argument("user")
    dm.add_argument("text", nargs="+")

    search = sub.add_parser("search")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int, default=10)

    messages = sub.add_parser("messages")
    messages.add_argument("channel")
    messages.add_argument("--limit", type=int, default=10)

    thread = sub.add_parser("thread")
    thread.add_argument("message_id")
    thread.add_argument("--channel", required=True)
    thread.add_argument("--limit", type=int, default=10)

    status = sub.add_parser("status").add_subparsers(dest="subcommand")
    set_status = status.add_parser("set")
    set_status.add_argument("code")
    set_status.add_argument("text", nargs="+")
    set_status.add_argument("--expires-at", type=int, default=0)
    status.add_parser("clear")

    schedule = sub.add_parser("schedule").add_subparsers(dest="subcommand")
    schedule_list = schedule.add_parser("list")
    schedule_list.add_argument("--channel")
    schedule_list.add_argument("--limit", type=int, default=100)
    schedule_create = schedule.add_parser("create")
    schedule_create.add_argument("channel")
    schedule_create.add_argument("send_at", type=int)
    schedule_create.add_argument("text", nargs="+")
    schedule_cancel = schedule.add_parser("cancel")
    schedule_cancel.add_argument("scheduled_message_id")

    return parser


def _resolve_api_key(args: argparse.Namespace) -> str:
    if args.api_key_file:
        with open(args.api_key_file, encoding="utf-8") as handle:
            return handle.read().strip()
    if args.api_key_stdin:
        return sys.stdin.read().strip()
    return os.environ.get("PUMBLE_API_KEY", "").strip()


def _base_url(args: argparse.Namespace) -> str:
    return args.base_url or os.environ.get("PUMBLE_BASE_URL") or DEFAULT_BASE_URL


def _positive(value: int, flag: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise UsageError(f"{flag} must be a positive integer")
    return value


def _require_ok(value: Any) -> Any:
    """Façade failures become CLI errors with the failure summary."""
    if isinstance(value, FacadeFailure):
        details = ""
        if value.choices:
            labels = ", ".join(
                str(choice.get("label", choice))
                if isinstance(choice, dict)
                else str(getattr(choice, "label", choice))
                for choice in value.choices
            )
            details = f" Choices: {labels}"
        raise CliError(f"{value.summary}{details}")
    return value


def _print_write(receipt: Any, args: argparse.Namespace) -> None:
    if args.json:
        fmt.print_json(receipt)
        return
    if not args.quiet:
        fmt.print_diagnostic(receipt.summary)


async def _resolve_channel_id(client: PumbleClient, value: str) -> str:
    bare = value.removeprefix("#")
    if _ID_RE.fullmatch(bare):
        return bare
    found = _require_ok(await client.channels.find(value))
    return found.channel.id


async def _run(args: argparse.Namespace, client: PumbleClient) -> None:
    command = args.command

    if command == "whoami":
        me = _require_ok(await client.identity.me())
        if args.json:
            fmt.print_json(me)
        else:
            fmt.print_line(f"{me.name} <{me.email}> ({me.id})")
        return

    if command == "channels":
        if args.subcommand == "list":
            entries = _require_ok(await client.channels.list())
            if args.json:
                fmt.print_json([entry.channel for entry in entries])
            else:
                for entry in entries:
                    fmt.print_line(fmt.format_channel(entry.channel))
            return
        if args.subcommand == "find":
            found = _require_ok(await client.channels.find(args.query))
            if args.json:
                fmt.print_json(found.channel)
            else:
                fmt.print_line(fmt.format_channel(found.channel))
            return
        if args.subcommand == "create":
            receipt = _require_ok(
                await client.channels.create(
                    name=args.name,
                    type="PRIVATE" if args.private else "PUBLIC",
                )
            )
            _print_write(receipt, args)
            return
        raise UsageError("usage: pumble-keys channels list|find|create ...")

    if command == "users":
        if args.subcommand == "find":
            found = _require_ok(await client.users.find(args.query))
            if args.json:
                fmt.print_json(found.user)
            else:
                fmt.print_line(fmt.format_user(found.user))
            return
        raise UsageError("usage: pumble-keys users find ...")

    if command == "send":
        channel_id = await _resolve_channel_id(client, args.channel)
        receipt = _require_ok(
            await client.messages.send(channel_id=channel_id, text=" ".join(args.text))
        )
        _print_write(receipt, args)
        return

    if command == "dm":
        target = args.user
        dm_kwargs: dict[str, Any] = (
            {"user_id": target} if _ID_RE.fullmatch(target) else {"user": target}
        )
        receipt = _require_ok(
            await client.messages.dm(text=" ".join(args.text), **dm_kwargs)
        )
        _print_write(receipt, args)
        return

    if command == "search":
        limit = _positive(args.limit, "--limit")
        page = _require_ok(
            await client.search.page(text=" ".join(args.query), limit=limit)
        )
        hits = list(page.content)[:limit]
        if args.json:
            fmt.print_json(hits)
        else:
            for hit in hits:
                fmt.print_line(fmt.format_message_like(hit))
        return

    if command == "messages":
        limit = _positive(args.limit, "--limit")
        channel_id = await _resolve_channel_id(client, args.channel)
        page = _require_ok(
            await client.messages.list(channel_id=channel_id, limit=limit)
        )
        for message in list(page.messages)[:limit]:
            if not args.json:
                fmt.print_line(fmt.format_message_like(message))
        if args.json:
            fmt.print_json(list(page.messages)[:limit])
        return

    if command == "thread":
        limit = _positive(args.limit, "--limit")
        channel_id = await _resolve_channel_id(client, args.channel)
        context = _require_ok(
            await client.threads.get_context(
                channel_id=channel_id,
                message_id=args.message_id,
                reply_limit=limit,
            )
        )
        if args.json:
            fmt.print_json(context)
        else:
            for message in (context.root, *context.replies):
                fmt.print_line(
                    f"{message.timestamp}\t{message.channel_id}\t"
                    f"{message.author}: {fmt.one_line(message.text)}"
                )
        return

    if command == "status":
        if args.subcommand == "set":
            receipt = _require_ok(
                await client.users.set_status(
                    code=fmt.normalise_emoji_code(args.code),
                    status=" ".join(args.text),
                    expires_at=args.expires_at,
                )
            )
            _print_write(receipt, args)
            return
        if args.subcommand == "clear":
            receipt = _require_ok(await client.users.clear_status())
            _print_write(receipt, args)
            return
        raise UsageError("usage: pumble-keys status set|clear ...")

    if command == "schedule":
        if args.subcommand == "list":
            limit = _positive(args.limit, "--limit")
            kwargs: dict[str, Any] = {"limit": limit}
            if args.channel:
                kwargs["channel_id"] = await _resolve_channel_id(client, args.channel)
            page = _require_ok(await client.scheduled.list(**kwargs))
            scheduled = list(page.scheduled_messages)[:limit]
            if args.json:
                fmt.print_json(scheduled)
            else:
                for message in scheduled:
                    fmt.print_line(fmt.format_scheduled(message))
            return
        if args.subcommand == "create":
            channel_id = await _resolve_channel_id(client, args.channel)
            receipt = _require_ok(
                await client.scheduled.create(
                    channel_id=channel_id,
                    text=" ".join(args.text),
                    send_at=args.send_at,
                )
            )
            _print_write(receipt, args)
            return
        if args.subcommand == "cancel":
            receipt = _require_ok(
                await client.scheduled.cancel(
                    scheduled_message_id=args.scheduled_message_id
                )
            )
            _print_write(receipt, args)
            return
        raise UsageError("usage: pumble-keys schedule list|create|cancel ...")

    raise UsageError(f"unknown command: {command}")


def main(argv: list[str] | None = None, *, client: PumbleClient | None = None) -> int:
    """Entry point. ``client`` injects a prebuilt façade for tests."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command is None:
            parser.print_help(sys.stderr)
            return 0

        if args.command == "doctor":
            key = _resolve_api_key(args)
            fmt.print_line(f"api key: {fmt.mask_key(key)}")
            fmt.print_line(f"base url: {_base_url(args)}")
            return 0

        active_client = client
        if active_client is None:
            key = _resolve_api_key(args)
            if not key:
                raise UsageError(
                    "missing API key; set PUMBLE_API_KEY or pass --api-key-file <path>"
                )
            active_client = create_pumble_client(
                key,
                server_url=_base_url(args),
                timeout_ms=args.timeout_ms,
            )
        asyncio.run(_run(args, active_client))
        return 0
    except UsageError as error:
        fmt.print_diagnostic(f"pumble-keys: {error}")
        fmt.print_diagnostic("Run `pumble-keys --help` for usage.")
        return 2
    except CliError as error:
        fmt.print_diagnostic(f"pumble-keys: {error}")
        return 1
    except Exception as error:  # noqa: BLE001 — CLI boundary
        fmt.print_diagnostic(f"pumble-keys: {error}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
