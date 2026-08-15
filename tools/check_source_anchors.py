#!/usr/bin/env python3
"""Verify the anchored OpenAPI source and the parity manifests.

Default mode verifies. `--write` rebuilds the manifests from the OpenAPI
document and the pinned reference checkout. Requires PyYAML.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
OPENAPI = REPO / "PumbleOpenApi.yaml"
CONTRACTS = REPO / "contracts"

EXPECTED_SHA256 = "a9c3af3cc5de074b7112b63203ec6e1b686afebfe8751bc75df630efd2906a43"
EXPECTED_BLOB_SHA = "aacb7f2500026854452795224b34afb1ba43f654"
EXPECTED_OPERATIONS = 26
EXPECTED_SCHEMAS = 32
EXPECTED_WRITES = 15

HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def compute_hashes(data: bytes) -> tuple[str, str]:
    sha256 = hashlib.sha256(data).hexdigest()
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    return sha256, blob


def build_operations(spec: dict) -> list[dict]:
    operations = []
    for path, item in spec["paths"].items():
        for method in HTTP_METHODS:
            op = item.get(method)
            if op is None:
                continue
            is_write = op.get("x-sdk-no-write-retries") is True
            operations.append(
                {
                    "operationId": op["operationId"],
                    "method": method.upper(),
                    "path": path,
                    "tag": op["tags"][0],
                    "class": "write" if is_write else "read",
                    "noWriteRetries": is_write,
                    "specBackoff": not is_write and "x-speakeasy-retries" in op,
                }
            )
    return operations


def build_schemas(spec: dict) -> list[str]:
    return list(spec["components"]["schemas"].keys())


def load_json(name: str) -> object:
    return json.loads((CONTRACTS / name).read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rebuild manifests")
    args = parser.parse_args()

    data = OPENAPI.read_bytes()
    sha256, blob = compute_hashes(data)
    errors = []
    if sha256 != EXPECTED_SHA256:
        errors.append(f"OpenAPI SHA-256 drift: {sha256}")
    if blob != EXPECTED_BLOB_SHA:
        errors.append(f"OpenAPI Git blob SHA drift: {blob}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    spec = yaml.safe_load(data)
    operations = build_operations(spec)
    schemas = build_schemas(spec)

    if args.write:
        CONTRACTS.mkdir(exist_ok=True)
        (CONTRACTS / "operations.json").write_text(
            json.dumps(operations, indent=2) + "\n"
        )
        (CONTRACTS / "schemas.json").write_text(json.dumps(schemas, indent=2) + "\n")
        print(f"wrote {len(operations)} operations, {len(schemas)} schemas")

    stored_ops = load_json("operations.json")
    stored_schemas = load_json("schemas.json")
    writes = [op for op in operations if op["class"] == "write"]
    reads = [op for op in operations if op["class"] == "read"]

    checks = [
        (len(operations) == EXPECTED_OPERATIONS, "operation count"),
        (len(schemas) == EXPECTED_SCHEMAS, "schema count"),
        (len(writes) == EXPECTED_WRITES, "write count"),
        (all(op["specBackoff"] for op in reads), "read backoff markers"),
        (stored_ops == operations, "operations.json drift"),
        (stored_schemas == schemas, "schemas.json drift"),
        ((CONTRACTS / "source_modules.json").exists(), "source_modules.json missing"),
    ]
    failed = [name for ok, name in checks if not ok]
    if failed:
        print("FAIL: " + ", ".join(failed), file=sys.stderr)
        return 1
    print(
        f"anchors OK: sha256/blob match, {len(operations)} operations "
        f"({len(writes)} writes), {len(schemas)} schemas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
