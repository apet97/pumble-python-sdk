# Contributing

Read `SOURCE_BASELINE.md` (anchored sources) and
`docs/GENERATOR_DEVIATIONS.md` (regeneration procedure) first.

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
uv run coverage run -m pytest -q && uv run coverage report
```

`check_generated_boundaries.py` rejects manual edits under generated
ownership. Pass `--generator-run` only for an intentional regeneration
commit. The coverage gate (`.coveragerc`) requires ≥95% combined
line+branch coverage over the hand-written packages.

## Safety rules

- Never add automatic retries to any write operation.
- Never place API keys, tokens, emails, full live IDs, or message content
  in code, fixtures, logs, or test snapshots.
- Structured failure values, not exceptions, represent normal not-found,
  ambiguity, API, and transport outcomes.
