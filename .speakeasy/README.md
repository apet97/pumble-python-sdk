# Speakeasy generation

The pinned Speakeasy CLI generates the raw Python SDK from
`PumbleOpenApi.yaml`. Generated code is read-only. See `CONTRIBUTING.md`.

## Run

```bash
speakeasy run --pinned
```

`--pinned` forces the `speakeasyVersion` in `workflow.yaml` (`1.763.6`).
Never use `latest`: it upgrades mid-run and pollutes the regeneration diff.

## Fixed decisions

- Target is Python only. Speakeasy MCP output stays disabled. This project
  hand-writes the MCP server because profile, safety, and MCP App behavior
  cannot be inferred from an OpenAPI document.
- `moduleName: pumble_keys` sets the import name. `packageName:
  pumble_keys_sdk` sets the distribution name.
- `maintainOpenAPIOrder: true` keeps generated members in document order,
  which keeps catalogs deterministic.
- `additionalDependencies` carries the runtime and development
  dependencies into the generated `pyproject.toml`, because the generator
  owns that file.

## Known generator gaps

The pinned generator has no configuration key for these. They are applied
by the documented idempotent patch `tools/patch_generated.py` (run it
after every generation, then `uv lock`) and recorded in
`docs/GENERATOR_DEVIATIONS.md`:

1. `[project.scripts]` console entry points (`pumble-keys`,
   `pumble-keys-mcp`).
2. `requires-python`. The generator emits `>=3.10`; this project supports
   `>=3.11,<3.15`.

Development tools (build, twine, pip-audit) turned out to be expressible
in `additionalDependencies.dev`; they need no patch. The generator pins
its own mypy. The generator's `versioningStrategy: automatic` bumps the
version each run; restore the previous version after a regeneration with
no intended release (see `docs/GENERATOR_DEVIATIONS.md`).
