# Pumble Python SDK/MCP — Implementation Status

- Reference commit: `cc20de10a6f0ce1efa9a57eb9509ff8e2324fe1e`
- OpenAPI SHA-256: `a9c3af3cc5de074b7112b63203ec6e1b686afebfe8751bc75df630efd2906a43`
- Rule: exactly one packet may be `IN_PROGRESS`.

| Packet | Status | Commit | Targeted tests | Full/fast gate | Notes |
|---|---|---|---|---|---|
| P00 — Anchor sources and create the parity ledger | DONE | p00 | `tools/check_source_anchors.py` — PASS | fast gate n/a (no toolchain yet) | Blob+SHA-256 verified; 26 ops / 32 schemas / 15 writes. |
| P01 — Create the clean Python repository and toolchain | DONE | p01 | `uv run pytest tests/unit/test_import.py` — PASS (1); 3.11 + 3.12 import OK | `uv sync --all-extras --dev` — PASS | `mcp[cli]==2.0.0` pinned; console scripts declared. |
| P02 — Add repository rules, generated ownership, and status tracking | DONE | p02 | `pytest tests/unit/test_repo_rules.py` — PASS (6) | `check_status.py` + `check_generated_boundaries.py` — PASS | Boundary checker rejects synthetic generated-path edit. |
| P03 — Configure a pinned Speakeasy Python target | DONE | p03 | scratch generation with this exact config — PASS | `check_generated_boundaries.py`, `check_status.py`, `pytest` (7) — PASS | Pin `1.763.6` works for Python. Two generator gaps recorded for P05. |
| P04 — Generate and inventory the raw Python SDK | DONE | p04 | `pytest tests/unit/test_generated_api_inventory.py` — PASS (5); `inventory_generated_api.py --check` — PASS | ruff + pytest (12) + boundaries (`--generator-run`) + status — PASS | 26 ops sync+async; reads spec backoff; writes no retry. |
| P05 — Burn down generator defects without contaminating generated code | DONE | p05 | `pytest tests/generated` — PASS (5); patch second run — no-op | ruff + pytest (17) + inventory `--check` + boundaries (`--generator-run`) — PASS | 2 patch items (requires-python, scripts); dev tools moved to gen.yaml config. |
| P06 — Lock OpenAPI and generated contract fidelity | DONE | p06 | `pytest tests/contract` — PASS (27, no network) | ruff + pytest (44) + boundaries + inventory `--check` — PASS | 26 ops, 32 schemas, ApiKey header, error union, retry policy locked. |
| P07 — Implement identifiers, display helpers, and redaction | DONE | p07 | `pytest tests/unit/test_ids.py test_display.py test_redaction.py` — PASS (84) | ruff + pytest (128) + boundaries + inventory `--check` — PASS | NewType IDs; TS-exact labels; two redaction families. |
| P08 — Implement structured results and error categorization | NOT_STARTED | — | — | — | — |
| P09 — Implement safe retry and in-process rate limiting primitives | NOT_STARTED | — | — | — | — |
| P10 — Implement deterministic user/channel resolution | NOT_STARTED | — | — | — | — |
| P11 — Implement optional resolver cache and preflight | NOT_STARTED | — | — | — | — |
| P12 — Port defensive exhaustive search and message pagination | NOT_STARTED | — | — | — | — |
| P13 — Port compact thread context and reply helper | NOT_STARTED | — | — | — | — |
| P14 — Build the async curated client façade and read namespaces | NOT_STARTED | — | — | — | — |
| P15 — Port safe message/channel write façades | NOT_STARTED | — | — | — | — |
| P16 — Port scheduled-message façade | NOT_STARTED | — | — | — | — |
| P17 — Add custom-status helpers and invalidate affected caches | NOT_STARTED | — | — | — | — |
| P18 — Port telemetry and reusable testing helpers | NOT_STARTED | — | — | — | — |
| P19 — Port typed Pumble webhook event models | NOT_STARTED | — | — | — | — |
| P20 — Port webhook signature verification and ASGI receiver | NOT_STARTED | — | — | — | — |
| P21 — Port event router and `PumbleApp` convenience class | NOT_STARTED | — | — | — | — |
| P22 — Port Pumble OAuth helpers and token store protocol | NOT_STARTED | — | — | — | — |
| P23 — Port experimental Pumble Socket Mode as an optional extra | NOT_STARTED | — | — | — | — |
| P24 — Port the one-shot SDK CLI | NOT_STARTED | — | — | — | — |
| P25 — Create MCP configuration, lifespan, and server factory | NOT_STARTED | — | — | — | — |
| P26 — Implement MCP entry point, transports, and remote authorization | NOT_STARTED | — | — | — | — |
| P27 — Register the seven curated read tools | NOT_STARTED | — | — | — | — |
| P28 — Implement signed preview/confirmed MCP writes | NOT_STARTED | — | — | — | — |
| P29 — Register MCP resources with bounded payloads and safe paths | NOT_STARTED | — | — | — | — |
| P30 — Port prompts and add argument completions | NOT_STARTED | — | — | — | — |
| P31 — Implement readonly, raw readwrite, and dry-run profiles | NOT_STARTED | — | — | — | — |
| P32 — Adopt stateless discovery, routing headers, cache hints, and deterministic catalogs | NOT_STARTED | — | — | — | — |
| P33 — Add optional MRTR interactive send/reply tools | NOT_STARTED | — | — | — | — |
| P34 — Bridge Pumble webhooks to modern MCP subscriptions | NOT_STARTED | — | — | — | — |
| P35 — Scaffold the single MCP App frontend | NOT_STARTED | — | — | — | — |
| P36 — Register the MCP App opening tool and UI resource | NOT_STARTED | — | — | — | — |
| P37 — Implement App read/browse/search/thread flows | NOT_STARTED | — | — | — | — |
| P38 — Implement App composer with preview and explicit confirmation | NOT_STARTED | — | — | — | — |
| P39 — Finish App accessibility, host integration, and packaging | NOT_STARTED | — | — | — | — |
| P40 — Create sanitized replay corpus and TypeScript/Python parity tests | NOT_STARTED | — | — | — | — |
| P41 — Build the live sacrificial-workspace verification suite | NOT_STARTED | — | — | — | — |
| P42 — Write user and maintainer documentation | NOT_STARTED | — | — | — | — |
| P43 — Harden packaging and fresh-environment smoke tests | NOT_STARTED | — | — | — | — |
| P44 — Implement CI, security gates, and release workflow | NOT_STARTED | — | — | — | — |
| P45 — Perform final adversarial parity and release audit | NOT_STARTED | — | — | — | — |

## Current packet detail

- Packet: `P07` (DONE)
- Objective: Implement identifiers, display helpers, and redaction.
- Allowed files: `src/pumble_keys/extensions/ids.py`, `display.py`, `redaction.py`, `tests/unit/test_ids.py`, `test_display.py`, `test_redaction.py`
- Exit condition: Shared pure helpers are stable before network-facing façade work starts.
- Started from commit: `c04f474` (p06)
- Commands/results:
  - `uv run pytest tests/unit/test_ids.py tests/unit/test_display.py tests/unit/test_redaction.py -q` → 84 passed.
  - `ids.py`: `NewType` aliases for the six ID kinds (no runtime class proliferation), `is_pumble_id_like`, `as_*` shape validators, `unbrand`. Language difference vs TS: raises `ValueError` (Python convention) where TS throws `TypeError`; message format preserved.
  - `display.py`: `display_channel` (leading `#`), `display_user` (email fallback for blank name), plus the resolve.ts candidate-label formatters (`<name> <email> | <id>`, `#<name> | <type> | <id>`) so P10 reuses them without duplication.
  - `redaction.py`: `redact_sensitive_text` (pmb_ tokens, Bearer/Basic, key/value assignments — from write-plan.ts) and `redact_debug_value`/`redact_debug_headers` (secret-named keys, body-text keys `text/tx/message/description`, emails, 24-hex IDs, configurable `sensitive_keys` — from debug-redaction.ts). Deterministic; false-positive test keeps ordinary prose intact.
  - Added `extensions/__init__.py` exporting the P07 surface (infrastructure for the named modules).
  - Fast gate: ruff format/check on `src/pumble_keys/extensions tools tests` — PASS; `pytest tests` → 128 passed; boundaries — PASS (extensions/** is a hand-written exception); inventory `--check` — PASS; `git diff --check` clean.
- Deviations: candidate-label formatters live in `display.py` instead of waiting for `resolve.py` (P10) — they are display code and the packet requires "IDs in ambiguity choices".

- Packet: `P06` (DONE)
- Objective: Lock OpenAPI and generated contract fidelity.
- Allowed files: `tests/contract/test_operations.py`, `test_models.py`, `test_auth.py`, `test_retry_policy.py`, `test_error_union.py`
- Exit condition: The raw SDK is proven against the supplied OpenAPI rather than assumed correct.
- Started from commit: `041f6c1` (p05)
- Commands/results:
  - `uv run pytest tests/contract -q` → 27 passed, fully offline (respx mocks the one HTTP-level test).
  - Coverage: 26 spec operations == ledger == generated callables (runtime resolution); one known tag per operation and tag→namespace mapping enforced; all 32 ledger schemas resolve to generated symbols (renames recorded in the test's mapping table: `CustomStatusObject`→`CustomStatus`; `ThreadReplyInfo`/`ThreadRootInfo` inlined per parent as `Message*`/`SearchHit*`); `ApiKey` header serialization proven via `utils.get_security` (no `Authorization`); server URL constant + override; reads carry exact spec backoff (500/30000/1.5/60000, 429/5XX, connection errors) in both spec and generated source; writes carry `x-sdk-no-write-retries` and zero `BackoffStrategy` literals in any write method body; both error shapes parse through `ErrorUnion` without collapsing to a string; a mocked 403 raises typed `errors.Error` with `LegacyErrorData`.
  - Fixtures are sanitized inline (24-zero-padded IDs, synthetic text), matching the reference sanitizer's placeholder alphabet.
  - Fast gate: ruff format/check on hand-written paths — PASS; `pytest tests` → 44 passed; boundaries (no generated changes this packet) — PASS; inventory `--check` — PASS; `git diff --check` clean.
- Deviations: none.

- Packet: `P05` (DONE)
- Objective: Burn down generator defects without contaminating generated code.
- Allowed files: `openapi/python-overlay.yaml` (not needed), `tools/patch_generated.py`, `docs/GENERATOR_DEVIATIONS.md`, tests under `tests/generated/`
- Exit condition: Generated output passes contract tests with every deviation documented.
- Started from commit: `ded28e3` (p04)
- Commands/results:
  - Red first: `tests/generated/test_pyproject_contract.py` failed 5/5 on unpatched output.
  - Config route beats patch route for dev tools: added `build`, `pip-audit`, `twine` to `.speakeasy/gen.yaml` `additionalDependencies.dev` and regenerated (`speakeasy run --pinned`) — all three landed in `[dependency-groups].dev`. The P03 note claiming they needed a patch was wrong; corrected in `docs/GENERATOR_DEVIATIONS.md` and `.speakeasy/README.md`.
  - `tools/patch_generated.py` covers the two true gaps: `requires-python >=3.11,<3.15` and `[project.scripts]` (`pumble-keys`, `pumble-keys-mcp`). First run patched; second run printed "already patched (no-op)". `uv lock` + `uv sync` clean.
  - `uv run pytest tests -q` → 17 passed. Inventory `--check` PASS. Boundaries `--generator-run` PASS. `git diff --check` clean. No overlay needed (no OpenAPI-expressible defect found).
- Deviations (narrow, documented):
  - Touched `.speakeasy/gen.yaml` (P03 file) because plan §4 rule 1 prefers a generator-configuration fix over a patch; the dev-tools defect was expressible in config.
  - Touched `.speakeasy/README.md` (P03 file) to keep its gap list truthful after the config fix.
  - Regeneration auto-bumped the version again (0.1.0→0.1.1); restored 0.1.0 as documented in `docs/GENERATOR_DEVIATIONS.md` ("Resolved without a patch"). Because of this version counter, "fresh generation + patch equals committed tree" holds for all content except the five version-metadata strings; the reset procedure is documented.

- Packet: `P04` (DONE)
- Objective: Generate and inventory the raw Python SDK.
- Allowed files: generator output under `src/pumble_keys/`, `contracts/generated_api.json`, `docs/RAW_API.md`
- Exit condition: Raw generated surface is complete and machine-audited.
- Started from commit: `fbcbd46` (p03)
- Commands/results:
  - `speakeasy run --pinned` (first run) → "SDK for python generated successfully". Emitted 26 operations across `channels.py`, `messages.py`, `scheduled_messages.py`, `users.py`, each with sync and `_async` methods.
  - `speakeasy run --pinned` (second run, idempotency proof) → identical content except the generator's automatic version counter (`versioningStrategy: automatic`) bumped `0.1.0` → `0.1.1` in `gen.yaml`/`pyproject.toml`/`_version.py`/`uv.lock`/`gen.lock`. No generated code drift. Restored the first-run `0.1.0` state; release versioning is an explicit decision, not a regeneration side effect.
  - `uv run python tools/inventory_generated_api.py` → wrote `contracts/generated_api.json` (26 operations) from AST inspection; `--check` verifies staleness.
  - `uv run pytest tests/unit -q` → 12 passed (5 new P04 evidence tests: all 26 IDs map to sync+async callables on `PumbleSDK`; 11 reads carry backoff 500/30000/1.5/60000 on 429/5XX; 15 writes have no default retry config and keep `x-sdk-no-write-retries`; `ApiKey` header + server URL confirmed at runtime).
  - Fast gate: `ruff format --check`/`ruff check` on hand-written `tools tests` — PASS; `check_generated_boundaries.py --generator-run` — PASS; `check_status.py` — PASS; `git diff --check` — clean; secret grep for the live API key — no hits.
- Findings:
  - Writes fall back to `sdk_configuration.retry_config` if a user sets one globally; only the per-operation default is absent. The façade (P09/P15) must never install a global retry config that wraps writes; recorded in `docs/RAW_API.md`.
  - The generator also emits root-level files: `pyproject.toml`, `uv.lock`, `USAGE.md`, `py.typed`, `pylintrc`, `.gitattributes`, `.vscode/`, `scripts/publish.sh`, `docs/models/`, `docs/sdks/`, `.speakeasy/gen.lock`, `.speakeasy/workflow.lock`, and it normalizes `gen.yaml`/`workflow.yaml`/`.gitignore` and appends SDK docs to `README.md`.
  - As predicted in P03: generated `requires-python` is `>=3.10` and console scripts are absent → P05 patch items. `generateTests: false` was written by the normalizer (generated tests stay off).
- Deviations (narrow, documented):
  - Updated `contracts/generated-ownership.json` with the exact emitted generator-owned paths. The P02 manifest carried an explicit note delegating this recording to P04.
  - Added `tools/inventory_generated_api.py` and `tests/unit/test_generated_api_inventory.py` as the machine-audit evidence carriers required by the packet ("populate from runtime introspection or AST inspection" and the two required test items). Precedent: P00's anchor-check script.
  - The generator's own writes to root files listed above are committed as generator output even though the allowed-files line names only `src/pumble_keys/`; excluding them would leave the tree permanently dirty and break regeneration diffs.
  - `chmod +x tools/*.py` for ruff EXE001 under the generator-supplied ruff config.

## Release evidence pointers

- Full offline receipt: —
- Live receipt: —
- Package smoke receipt: —
- Final audit: —
