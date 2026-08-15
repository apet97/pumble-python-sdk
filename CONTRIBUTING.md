# Contributing

This repository follows the execution plan in the project's implementation
documents. Read `SOURCE_BASELINE.md` and `IMPLEMENTATION_STATUS.md` first.

## Generated versus hand-written code

- The pinned Speakeasy generator owns the raw SDK. The exact owned paths
  are listed in `contracts/generated-ownership.json`.
- Never edit a generated file by hand. Fix the OpenAPI document, an
  approved overlay, the generator configuration, or a documented
  idempotent patch script, then regenerate.
- Hand-written code lives in `src/pumble_keys/extensions/`, `pumble_app/`,
  `mcp_server/`, `cli/`, `testing/`, and `knowledge/`. Hand-written code
  can import generated code. Generated code must never import hand-written
  modules.
- Post-generation patches must be recorded. Unrecorded patches are
  forbidden.

## Checks

Run before every commit:

```bash
uv run python tools/check_generated_boundaries.py
uv run python tools/check_status.py
```

`check_generated_boundaries.py` rejects manual edits under generated
ownership. Pass `--generator-run` only for an intentional regeneration
commit. `check_status.py` enforces the packet table rules: one packet
`IN_PROGRESS` at most, and no skipped packets.

## Safety rules

- Never add automatic retries to any write operation.
- Never place API keys, tokens, emails, full live IDs, or message content
  in code, fixtures, logs, or test snapshots.
- Structured failure values, not exceptions, represent normal not-found,
  ambiguity, API, and transport outcomes.
