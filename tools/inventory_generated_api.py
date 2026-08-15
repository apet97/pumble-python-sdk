#!/usr/bin/env python3
"""Inventory the generated raw SDK surface into `contracts/generated_api.json`.

The inventory comes from AST inspection of the generator-owned modules.
Nothing is typed by hand: operation IDs, HTTP methods, paths, retry
defaults, and the write-safety extension are read from the generated
source. The tool then cross-checks the inventory against the parity
ledger in `contracts/operations.json` and fails on any mismatch:

- every one of the 26 operations maps to a generated sync and async callable;
- every read carries the exact spec backoff default (500/30000/1.5/60000);
- every write has no default retry configuration and carries the
  `x-sdk-no-write-retries` extension.

Run with `--check` to verify the committed file instead of rewriting it.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKAGE = REPO / "src" / "pumble_keys"
OPERATIONS = REPO / "contracts" / "operations.json"
OUTPUT = REPO / "contracts" / "generated_api.json"

# Generated tag modules and the lazy SDK attribute that exposes them.
TAG_MODULES = {
    "channels.py": "channels",
    "messages.py": "messages",
    "scheduled_messages.py": "scheduled_messages",
    "users.py": "users",
}

SPEC_BACKOFF = [500, 30000, 1.5, 60000]


def _const(node: ast.AST | None):
    return node.value if isinstance(node, ast.Constant) else None


def _find_calls(body: list[ast.stmt], name: str) -> list[ast.Call]:
    calls = []
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Name)
                and func.id == name
                or isinstance(func, ast.Attribute)
                and func.attr == name
            ):
                calls.append(node)
    return calls


def _method_info(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict | None:
    hooks = _find_calls(fn.body, "HookContext")
    builds = _find_calls(fn.body, "_build_request")
    builds += _find_calls(fn.body, "_build_request_async")
    if not hooks or not builds:
        return None

    info: dict = {"method_name": fn.name}
    for kw in builds[0].keywords:
        if kw.arg == "method":
            info["http_method"] = _const(kw.value)
        elif kw.arg == "path":
            info["path"] = _const(kw.value)

    for kw in hooks[0].keywords:
        if kw.arg == "operation_id":
            info["operation_id"] = _const(kw.value)
        elif kw.arg == "extensions":
            info["no_write_retries_extension"] = False
            if isinstance(kw.value, ast.Dict):
                for key, value in zip(kw.value.keys, kw.value.values):
                    if _const(key) == "x-sdk-no-write-retries":
                        info["no_write_retries_extension"] = bool(_const(value))

    info.setdefault("no_write_retries_extension", False)

    info["default_spec_backoff"] = False
    for call in _find_calls(fn.body, "BackoffStrategy"):
        args = [_const(arg) for arg in call.args]
        info["default_spec_backoff"] = args == SPEC_BACKOFF

    info["paginated"] = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"next_func", "empty_result"}
        for node in ast.walk(ast.Module(body=fn.body, type_ignores=[]))
    )

    params = [a.arg for a in fn.args.kwonlyargs]
    info["server_url_override"] = "server_url" in params
    info["timeout_param"] = "timeout_ms" if "timeout_ms" in params else None
    info["retries_param"] = "retries" in params

    returns = fn.returns
    info["return_type"] = ast.unparse(returns) if returns is not None else None
    return info


def inventory() -> dict:
    operations: dict[str, dict] = {}
    for filename, namespace in TAG_MODULES.items():
        tree = ast.parse((PACKAGE / filename).read_text())
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                info = _method_info(fn)
                if info is None or "operation_id" not in info:
                    continue
                op_id = info.pop("operation_id")
                entry = operations.setdefault(
                    op_id,
                    {
                        "operationId": op_id,
                        "module": filename,
                        "sdk_namespace": namespace,
                        "sdk_class": cls.name,
                        "http_method": info["http_method"],
                        "path": info["path"],
                    },
                )
                key = (
                    "async_method"
                    if isinstance(fn, ast.AsyncFunctionDef)
                    else "sync_method"
                )
                entry[key] = info["method_name"]
                entry["no_write_retries_extension"] = info["no_write_retries_extension"]
                entry["default_spec_backoff"] = info["default_spec_backoff"]
                entry["paginated"] = info["paginated"]
                entry["server_url_override"] = info["server_url_override"]
                entry["timeout_param"] = info["timeout_param"]
                entry["retries_param"] = info["retries_param"]
                entry.setdefault("return_types", {})[
                    "async" if isinstance(fn, ast.AsyncFunctionDef) else "sync"
                ] = info["return_type"]

    ledger = json.loads(OPERATIONS.read_text())
    ordered = []
    for op in ledger:
        entry = operations.get(op["operationId"])
        if entry is not None:
            entry["class"] = op["class"]
            ordered.append(entry)

    version = {}
    version_tree = ast.parse((PACKAGE / "_version.py").read_text())
    for node in version_tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = _const(node.value)
            if node.target.id in {
                "__version__",
                "__gen_version__",
                "__openapi_doc_version__",
            }:
                version[node.target.id.strip("_")] = value

    servers = []
    config_tree = ast.parse((PACKAGE / "sdkconfiguration.py").read_text())
    for node in config_tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "SERVERS"
            and isinstance(node.value, ast.List)
        ):
            servers = [_const(e) for e in node.value.elts]

    return {
        "comment": (
            "Machine-generated by tools/inventory_generated_api.py from AST "
            "inspection of the generator-owned modules. Do not edit by hand. "
            "The raw generated surface is unstable across generator upgrades."
        ),
        "generator": {
            "speakeasy_pinned": "1.763.6",
            **version,
        },
        "sdk_class": "PumbleSDK",
        "auth": {"constructor_param": "api_key_auth", "header": "ApiKey"},
        "servers": servers,
        "spec_backoff": {
            "initial_ms": 500,
            "max_interval_ms": 30000,
            "exponent": 1.5,
            "max_elapsed_ms": 60000,
            "retry_connection_errors": True,
        },
        "operations": ordered,
    }


def verify(data: dict) -> list[str]:
    problems = []
    ledger = json.loads(OPERATIONS.read_text())
    by_id = {op["operationId"]: op for op in data["operations"]}

    if len(data["operations"]) != len(ledger):
        problems.append(
            f"expected {len(ledger)} operations, found {len(data['operations'])}"
        )

    for op in ledger:
        entry = by_id.get(op["operationId"])
        if entry is None:
            problems.append(f"{op['operationId']}: no generated callable found")
            continue
        for key in ("sync_method", "async_method"):
            if not entry.get(key):
                problems.append(f"{op['operationId']}: missing {key}")
        if entry["http_method"] != op["method"] or entry["path"] != op["path"]:
            problems.append(f"{op['operationId']}: method/path mismatch")
        if op["class"] == "read":
            if not entry["default_spec_backoff"]:
                problems.append(
                    f"{op['operationId']}: read is missing the spec backoff default"
                )
        else:
            if entry["default_spec_backoff"]:
                problems.append(
                    f"{op['operationId']}: write has a default retry configuration"
                )
            if not entry["no_write_retries_extension"]:
                problems.append(
                    f"{op['operationId']}: write lost x-sdk-no-write-retries"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed inventory instead of rewriting it",
    )
    args = parser.parse_args()

    data = inventory()
    problems = verify(data)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1

    rendered = json.dumps(data, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            print(
                "FAIL: contracts/generated_api.json is stale; rerun "
                "tools/inventory_generated_api.py",
                file=sys.stderr,
            )
            return 1
        print("OK: generated API inventory matches the generated source.")
        return 0

    OUTPUT.write_text(rendered)
    print(
        f"OK: wrote {OUTPUT.relative_to(REPO)} with "
        f"{len(data['operations'])} operations."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
