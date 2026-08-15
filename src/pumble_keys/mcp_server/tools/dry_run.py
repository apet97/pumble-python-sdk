"""Dry-run interception for the readwrite profile.

A dry-run write validates and resolves inputs, then returns the planned
HTTP operation and a redacted argument summary. It NEVER calls a write
endpoint. Dry-run tools are read-only from Pumble's perspective but are
clearly titled as simulation.
"""

from __future__ import annotations

from typing import Any

from pumble_keys.extensions.redaction import redact_debug_value
from pumble_keys.mcp_server.tools.raw_manifest import RawOperation


def plan_dry_run(operation: RawOperation, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "dry_run": True,
        "summary": (
            f"DRY RUN: {operation.http} {operation.path} was validated but "
            "NOT executed."
        ),
        "planned": {
            "operation_id": operation.operation_id,
            "http_method": operation.http,
            "path": operation.path,
            "destructive": operation.destructive,
            "arguments": redact_debug_value(arguments),
        },
    }
