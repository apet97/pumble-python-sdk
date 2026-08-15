"""P04 evidence: the generated raw SDK surface is complete and machine-audited.

The inventory tool verifies the generated source with AST inspection.
These tests verify the committed inventory against the runtime package,
so a stale or hand-edited `generated_api.json` fails.
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
GENERATED_API = REPO / "contracts" / "generated_api.json"
OPERATIONS = REPO / "contracts" / "operations.json"


@pytest.fixture(scope="module")
def generated_api() -> dict:
    return json.loads(GENERATED_API.read_text())


@pytest.fixture(scope="module")
def ledger() -> list[dict]:
    return json.loads(OPERATIONS.read_text())


def test_inventory_tool_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "inventory_generated_api.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_all_26_operations_have_generated_callables(
    generated_api: dict, ledger: list[dict]
) -> None:
    from pumble_keys import PumbleSDK

    assert len(generated_api["operations"]) == 26
    assert [op["operationId"] for op in generated_api["operations"]] == [
        op["operationId"] for op in ledger
    ]

    sdk = PumbleSDK(api_key_auth="test-key-not-real")
    for op in generated_api["operations"]:
        namespace = getattr(sdk, op["sdk_namespace"])
        sync_fn = getattr(namespace, op["sync_method"])
        async_fn = getattr(namespace, op["async_method"])
        assert callable(sync_fn), op["operationId"]
        assert inspect.iscoroutinefunction(async_fn), op["operationId"]


def test_every_read_has_spec_backoff_and_async_access(generated_api: dict) -> None:
    reads = [op for op in generated_api["operations"] if op["class"] == "read"]
    assert len(reads) == 11
    for op in reads:
        assert op["default_spec_backoff"], op["operationId"]
        assert op["async_method"].endswith("_async"), op["operationId"]


def test_every_write_has_no_automatic_retry_configuration(
    generated_api: dict,
) -> None:
    writes = [op for op in generated_api["operations"] if op["class"] == "write"]
    assert len(writes) == 15
    for op in writes:
        assert not op["default_spec_backoff"], op["operationId"]
        assert op["no_write_retries_extension"], op["operationId"]


def test_auth_and_server_facts(generated_api: dict) -> None:
    from pumble_keys import PumbleSDK

    assert generated_api["auth"] == {
        "constructor_param": "api_key_auth",
        "header": "ApiKey",
    }
    assert generated_api["servers"] == [
        "https://pumble-api-keys.addons.marketplace.cake.com"
    ]
    assert "api_key_auth" in inspect.signature(PumbleSDK.__init__).parameters

    from pumble_keys.models import Security

    field = Security.model_fields["api_key_auth"]
    header_names = {
        getattr(getattr(meta, "security", None), "field_name", None)
        for meta in field.metadata
    }
    assert "ApiKey" in header_names
