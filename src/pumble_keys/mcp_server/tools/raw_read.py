"""Raw readonly profile: exact adapters for all 11 read operations."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from pumble_keys.cli.formatting import to_jsonable
from pumble_keys.extensions.operations import operation_failure
from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.tools.raw_manifest import (
    RAW_READ_OPERATIONS,
    RawOperation,
)
from pumble_keys.mcp_server.tools.read import state_of, to_failure

READ_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)


def clean_arguments(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if key != "ctx" and value is not None
    }


async def call_raw_operation(
    state: Any, operation: RawOperation, arguments: dict[str, Any]
) -> Any:
    """One call through the raw escape hatch; failures become values."""
    namespace = getattr(state.client.raw, operation.namespace)
    method = getattr(namespace, operation.method)
    call_kwargs = {"request": arguments} if operation.request_wrapped else arguments
    try:
        result = await method(**call_kwargs)
    # CancelledError is a BaseException, so cancellation still propagates.
    except Exception as error:  # noqa: BLE001 — categorized into a value
        failure = to_failure(
            operation_failure(
                f"Pumble API operation {operation.operation_id} failed.",
                error,
            )
        )
        return failure.model_dump(mode="json")
    return {"ok": True, "result": to_jsonable(result)}


def make_read_adapter(operation: RawOperation):
    async def adapter(**kwargs: Any) -> Any:
        state = state_of(kwargs["ctx"])
        return await call_raw_operation(state, operation, clean_arguments(kwargs))

    adapter.__name__ = operation.tool_name
    signature = operation.signature(Context)
    adapter.__signature__ = signature  # type: ignore[attr-defined]
    adapter.__annotations__ = {
        parameter.name: parameter.annotation
        for parameter in signature.parameters.values()
    }
    adapter.__annotations__["return"] = dict[str, Any]
    return adapter


def register(server: MCPServer, _config: McpConfig) -> None:
    for operation in RAW_READ_OPERATIONS:
        server.tool(
            name=operation.tool_name,
            description=(
                f"Raw {operation.http} {operation.path} ({operation.operation_id})."
            ),
            annotations=READ_ANNOTATIONS,
        )(make_read_adapter(operation))
