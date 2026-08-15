"""Raw readwrite profile: exact adapters for all 15 write operations.

Registration is double-gated: the config validator already required
``allow_raw_writes`` plus an audit path for the readwrite profile, and
this registrar re-checks both before registering anything. Every write
attempt/outcome lands in the redacted audit sink. Writes are one
attempt, never retried. With ``dry_run`` every write tool validates and
reports the planned call without touching Pumble.
"""

from __future__ import annotations

import time
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.tools.dry_run import plan_dry_run
from pumble_keys.mcp_server.tools.raw_manifest import (
    RAW_WRITE_OPERATIONS,
    RawOperation,
)
from pumble_keys.mcp_server.tools.raw_read import (
    call_raw_operation,
    clean_arguments,
)
from pumble_keys.mcp_server.tools.read import state_of

WRITE_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
DESTRUCTIVE_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)
DRY_RUN_ANNOTATIONS = ToolAnnotations(
    title="dry-run simulation",
    read_only_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)


class RawWriteGateError(RuntimeError):
    pass


def _audit(state: Any, operation: RawOperation, arguments: dict, outcome: str):
    if state.audit_writer is not None:
        state.audit_writer.write(
            {
                "ts": time.time(),
                "kind": "raw_write",
                "operation_id": operation.operation_id,
                "path": operation.path,
                "outcome": outcome,
                "arguments": arguments,
            }
        )


def make_write_adapter(operation: RawOperation, *, dry_run: bool):
    async def adapter(**kwargs: Any) -> Any:
        state = state_of(kwargs["ctx"])
        arguments = clean_arguments(kwargs)
        if dry_run:
            _audit(state, operation, arguments, "dry_run")
            return plan_dry_run(operation, arguments)
        _audit(state, operation, arguments, "attempt")
        result = await call_raw_operation(state, operation, arguments)
        ok = isinstance(result, dict) and result.get("ok") is True
        _audit(state, operation, arguments, "success" if ok else "failure")
        return result

    adapter.__name__ = operation.tool_name
    signature = operation.signature(Context)
    adapter.__signature__ = signature  # type: ignore[attr-defined]
    adapter.__annotations__ = {
        parameter.name: parameter.annotation
        for parameter in signature.parameters.values()
    }
    adapter.__annotations__["return"] = dict[str, Any]
    return adapter


def register(server: MCPServer, config: McpConfig) -> None:
    # Second startup gate (the first is config validation).
    if not config.allow_raw_writes:
        raise RawWriteGateError("raw write registration requires allow_raw_writes")
    if not config.audit_log_path:
        raise RawWriteGateError(
            "raw write registration requires an audit log destination"
        )

    for operation in RAW_WRITE_OPERATIONS:
        if config.dry_run:
            annotations = DRY_RUN_ANNOTATIONS
            description = (
                f"DRY-RUN SIMULATION of {operation.http} {operation.path} "
                f"({operation.operation_id}); never calls Pumble."
            )
        elif operation.destructive:
            annotations = DESTRUCTIVE_ANNOTATIONS
            description = (
                f"Raw DESTRUCTIVE {operation.http} {operation.path} "
                f"({operation.operation_id}). One attempt, never retried."
            )
        else:
            annotations = WRITE_ANNOTATIONS
            description = (
                f"Raw {operation.http} {operation.path} "
                f"({operation.operation_id}). One attempt, never retried."
            )
        server.tool(
            name=operation.tool_name,
            description=description,
            annotations=annotations,
        )(make_write_adapter(operation, dry_run=config.dry_run))
