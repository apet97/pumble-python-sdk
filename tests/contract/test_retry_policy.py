"""P06: retry contract — reads keep spec backoff, writes never auto-retry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent.parent

SPEC_BACKOFF = {
    "initialInterval": 500,
    "maxInterval": 30000,
    "maxElapsedTime": 60000,
    "exponent": 1.5,
}


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load((REPO / "PumbleOpenApi.yaml").read_text())


@pytest.fixture(scope="module")
def spec_ops(spec: dict) -> dict[str, dict]:
    ops = {}
    for methods in spec["paths"].values():
        for method, op in methods.items():
            if method in {"get", "post", "put", "delete", "patch"}:
                ops[op["operationId"]] = op
    return ops


@pytest.fixture(scope="module")
def ledger() -> list[dict]:
    return json.loads((REPO / "contracts" / "operations.json").read_text())


@pytest.fixture(scope="module")
def generated() -> dict[str, dict]:
    data = json.loads((REPO / "contracts" / "generated_api.json").read_text())
    return {op["operationId"]: op for op in data["operations"]}


def test_spec_reads_carry_exact_backoff(
    spec_ops: dict[str, dict], ledger: list[dict]
) -> None:
    reads = [op for op in ledger if op["class"] == "read"]
    assert len(reads) == 11
    for op in reads:
        retries = spec_ops[op["operationId"]].get("x-speakeasy-retries")
        assert retries is not None, op["operationId"]
        assert retries["strategy"] == "backoff", op["operationId"]
        assert retries["backoff"] == SPEC_BACKOFF, op["operationId"]
        # YAML parses the unquoted 429 as an integer.
        assert retries["statusCodes"] == [429, "5XX"], op["operationId"]
        assert retries["retryConnectionErrors"] is True, op["operationId"]


def test_spec_writes_have_no_retry_and_carry_marker(
    spec_ops: dict[str, dict], ledger: list[dict]
) -> None:
    writes = [op for op in ledger if op["class"] == "write"]
    assert len(writes) == 15
    for op in writes:
        spec_op = spec_ops[op["operationId"]]
        assert "x-speakeasy-retries" not in spec_op, op["operationId"]
        assert spec_op.get("x-sdk-no-write-retries") is True, op["operationId"]


def test_generated_reads_default_to_spec_backoff(
    generated: dict[str, dict], ledger: list[dict]
) -> None:
    for op in ledger:
        entry = generated[op["operationId"]]
        if op["class"] == "read":
            assert entry["default_spec_backoff"], op["operationId"]
        else:
            assert not entry["default_spec_backoff"], op["operationId"]
            assert entry["no_write_retries_extension"], op["operationId"]


def test_generated_write_source_has_no_backoff_constant(
    ledger: list[dict], generated: dict[str, dict]
) -> None:
    """Belt and braces: no BackoffStrategy literal in any write method body."""
    import ast

    modules = {generated[op["operationId"]]["module"] for op in ledger}
    write_methods = {
        generated[op["operationId"]]["sync_method"]
        for op in ledger
        if op["class"] == "write"
    } | {
        generated[op["operationId"]]["async_method"]
        for op in ledger
        if op["class"] == "write"
    }

    seen = set()
    for module in modules:
        tree = ast.parse((REPO / "src" / "pumble_keys" / module).read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in write_methods
            ):
                seen.add(node.name)
                body_src = ast.unparse(node)
                assert "BackoffStrategy(" not in body_src, node.name

    assert seen == write_methods
