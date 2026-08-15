# Generator deviations

Every post-generation change to generator-owned output is recorded here.
The only sanctioned mechanism is the documented idempotent patch
`tools/patch_generated.py`. An entry that loses its reason must be
deleted together with its patch code.

Pinned generator: Speakeasy `1.763.6` (generation `2.928.0`).

## Regeneration procedure

```bash
speakeasy run --pinned
uv run python tools/patch_generated.py
uv lock
uv run pytest tests/generated -q
```

`tools/patch_generated.py` is a no-op on already-patched output;
`tests/generated/test_pyproject_contract.py` fails on unpatched output,
so a regeneration that skips the patch cannot land silently.

## Active deviations

### 1. `requires-python` bound

- Defect: the generator hardcodes `requires-python = ">=3.10"` in
  `pyproject.toml`. The project contract is `>=3.11,<3.15` (plan §3).
  No `gen.yaml` key controls this field in the pinned version.
- Failing test: `test_requires_python_matches_project_contract`.
- Upstream: no public issue filed; the field is template-fixed in the
  pinned Python template (`templateVersion: v2`).
- Delete when: the pinned generator gains a supported-Python
  configuration key, or a pinned upgrade emits the correct bound.

### 2. `[project.scripts]` console entry points

- Defect: the Python generator has no console-script configuration key
  and drops the P01 `[project.scripts]` table when it overwrites
  `pyproject.toml`. The project ships `pumble-keys` and
  `pumble-keys-mcp`.
- Failing test: `test_console_scripts_are_declared`.
- Upstream: no public issue filed; scripts are outside the generator's
  Python feature set at the pinned version.
- Delete when: the pinned generator supports script entries, or the
  CLIs move to a separate distribution.

## Resolved without a patch

- Development tools `build`, `twine`, `pip-audit`: expressed in
  `.speakeasy/gen.yaml` `additionalDependencies.dev` (P05). The P03
  note that these needed a patch was wrong; the config key carries
  them. `mypy` is already a generator-pinned dev dependency.
- The generator's `versioningStrategy: automatic` bumps the patch
  version on every regeneration run. Release versioning is an explicit
  decision in this project: after a regeneration with no intended
  release, restore the previous version string in `gen.yaml`,
  `pyproject.toml`, `src/pumble_keys/_version.py`, and `releaseVersion`
  in `.speakeasy/gen.lock`, then regenerate `uv.lock` with `uv lock`
  (never text-edit the lock file). This is a version-metadata reset,
  not a code patch.
- The `[socket]` optional extra (`websockets`) is expressed in
  `.speakeasy/gen.yaml` `optionalDependencies` (P23) — config, not a
  patch.
- The generator's "Compile SDK" step runs pylint, mypy, AND pyright
  over ALL of `src/pumble_keys`, including the hand-written
  subpackages, and fails generation on any finding. Hand-written code
  must stay pylint-10.00/mypy-clean/pyright-clean; deliberate patterns
  (lazy optional imports, `except CancelledError: raise`) carry inline
  `# pylint: disable=...` pragmas.
- NEVER run `ruff --fix`/`ruff format` over `src` wholesale: ruff would
  rewrite generator-owned files (a forbidden manual edit). Lint only
  the hand-written paths: `src/pumble_keys/extensions`, `pumble_app`,
  `testing`, `cli`, `mcp_server`.

## Generator README usage snippets are invalid Python

The pinned generator (1.763.6) emits README usage examples that do not
parse (`list_channels(,` and `with` blocks with no body). They are
generator-owned and left as emitted; the docs test suite checks only
hand-written docs. Delete this entry when a generator upgrade produces
valid snippets.

## Patch entry 3: package-data for knowledge + App assets (P43)

The generator emits `[tool.setuptools.package-data]` with only
`py.typed`, so wheels shipped without the packaged knowledge base and
the built MCP App asset. `tools/patch_generated.py` extends the block
with `pumble_keys.knowledge` (`*.md`, `guides/*.md`) and
`pumble_keys.mcp_server.app_assets` (`*.html`, `*.json`). Failing
check: `tools/pack_smoke.py` required-file inspection. Delete when the
generator grows a package-data key.
