"""P06: operation contract — 26 operations, tag grouping, generated mapping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent.parent

TAG_TO_NAMESPACE = {
    "Channels": "channels",
    "Messages": "messages",
    "Scheduled Messages": "scheduled_messages",
    "Users": "users",
}


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load((REPO / "PumbleOpenApi.yaml").read_text())


@pytest.fixture(scope="module")
def spec_ops(spec: dict) -> list[dict]:
    ops = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method in {"get", "post", "put", "delete", "patch"}:
                ops.append({"path": path, "method": method.upper(), **op})
    return ops


@pytest.fixture(scope="module")
def ledger() -> list[dict]:
    return json.loads((REPO / "contracts" / "operations.json").read_text())


@pytest.fixture(scope="module")
def generated() -> dict:
    return json.loads((REPO / "contracts" / "generated_api.json").read_text())


def test_spec_has_exactly_26_operations(spec_ops: list[dict]) -> None:
    assert len(spec_ops) == 26


def test_ledger_matches_spec_ids_and_paths(
    spec_ops: list[dict], ledger: list[dict]
) -> None:
    spec_by_id = {op["operationId"]: op for op in spec_ops}
    assert sorted(spec_by_id) == sorted(op["operationId"] for op in ledger)
    for entry in ledger:
        op = spec_by_id[entry["operationId"]]
        assert op["path"] == entry["path"], entry["operationId"]
        assert op["method"] == entry["method"], entry["operationId"]


def test_every_operation_has_exactly_one_known_tag(spec_ops: list[dict]) -> None:
    for op in spec_ops:
        assert len(op["tags"]) == 1, op["operationId"]
        assert op["tags"][0] in TAG_TO_NAMESPACE, op["operationId"]


def test_generated_namespace_follows_spec_tag(
    spec_ops: list[dict], generated: dict
) -> None:
    generated_by_id = {op["operationId"]: op for op in generated["operations"]}
    assert len(generated_by_id) == 26
    for op in spec_ops:
        entry = generated_by_id[op["operationId"]]
        assert entry["sdk_namespace"] == TAG_TO_NAMESPACE[op["tags"][0]], op[
            "operationId"
        ]


def test_generated_callables_resolve_at_runtime(generated: dict) -> None:
    from pumble_keys import PumbleSDK

    sdk = PumbleSDK(api_key_auth="test-key-not-real")
    for op in generated["operations"]:
        namespace = getattr(sdk, op["sdk_namespace"])
        assert callable(getattr(namespace, op["sync_method"])), op["operationId"]
        assert callable(getattr(namespace, op["async_method"])), op["operationId"]
