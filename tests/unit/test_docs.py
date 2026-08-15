"""P42: documentation checks — examples compile, links resolve.

Python code blocks in the hand-written docs must at least compile (the
async examples are not executed against the API); JSON blocks must
parse; every relative link must point at an existing file.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = [
    REPO / "README.md",
    REPO / "PARITY_MATRIX.md",
    REPO / "docs" / "QUICKSTART.md",
    REPO / "docs" / "API-REFERENCE.md",
    REPO / "docs" / "MCP.md",
    REPO / "docs" / "MCP-SAFETY.md",
    REPO / "docs" / "MCP-APP.md",
    REPO / "docs" / "WEBHOOKS.md",
    REPO / "docs" / "PUMBLE-OAUTH.md",
    REPO / "docs" / "STABILITY.md",
    REPO / "docs" / "MIGRATING-FROM-TS.md",
    REPO / "docs" / "LIVE-TESTING.md",
]

# README's python blocks are generator-emitted and are NOT checked:
# the pinned Speakeasy generator ships syntactically invalid usage
# snippets (recorded in docs/GENERATOR_DEVIATIONS.md). Hand-written
# docs must compile.
HAND_WRITTEN = [doc for doc in DOCS if doc.name != "README.md"]

FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
LINK = re.compile(r"\]\(([^)#]+?)(?:#[^)]*)?\)")


def blocks(language: str) -> list[tuple[str, str]]:
    found = []
    for doc in HAND_WRITTEN:
        for match in FENCE.finditer(doc.read_text()):
            if (match.group(1) or "") == language:
                found.append((doc.name, match.group(2)))
    return found


def test_documented_files_exist() -> None:
    for doc in DOCS:
        assert doc.exists(), doc


def test_python_examples_compile() -> None:
    examples = blocks("python")
    assert examples, "expected python examples in the docs"
    for name, code in examples:
        try:
            ast.parse(code)
        except SyntaxError as error:  # pragma: no cover - failure detail
            pytest.fail(f"{name}: example does not parse: {error}")


def test_python_examples_import_real_symbols() -> None:
    import importlib

    imports = set()
    for _, code in blocks("python"):
        for node in ast.walk(ast.parse(code)):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("pumble_keys")
            ):
                imports.add((node.module, tuple(a.name for a in node.names)))
    assert imports
    for module_name, names in imports:
        module = importlib.import_module(module_name)
        for name in names:
            assert hasattr(module, name), f"{module_name}.{name}"


def test_json_examples_parse() -> None:
    for name, code in blocks("json"):
        try:
            json.loads(code)
        except ValueError as error:  # pragma: no cover - failure detail
            pytest.fail(f"{name}: JSON example invalid: {error}")


def test_relative_links_resolve() -> None:
    for doc in DOCS:
        for match in LINK.finditer(doc.read_text()):
            target = match.group(1).strip()
            if "://" in target or target.startswith("mailto:"):
                continue
            resolved = (doc.parent / target).resolve()
            assert resolved.exists(), f"{doc.name} -> {target}"


def test_readme_keeps_the_unofficial_notice() -> None:
    text = (REPO / "README.md").read_text()
    assert "Unofficial" in text
    assert "do not endorse" in text
