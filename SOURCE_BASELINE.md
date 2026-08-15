# Source baseline

This repository ports the Pumble TypeScript SDK/MCP to Python. The anchors
below are fixed. Change them only through a dedicated, reviewed packet.

## Anchors

| Anchor | Value |
|---|---|
| Reference repository | `apet97/psdk` |
| Reference commit | `cc20de10a6f0ce1efa9a57eb9509ff8e2324fe1e` |
| Reference TypeScript package | `0.4.0` |
| OpenAPI document version | `1.1.0` (OpenAPI `3.0.0`) |
| OpenAPI SHA-256 | `a9c3af3cc5de074b7112b63203ec6e1b686afebfe8751bc75df630efd2906a43` |
| OpenAPI Git blob SHA | `aacb7f2500026854452795224b34afb1ba43f654` |
| Operations | 26 (11 reads with spec backoff, 15 writes with `x-sdk-no-write-retries: true`) |
| Schemas | 32 |
| MCP baseline | official Python SDK `mcp==2.0.0`, protocol revision `2026-07-28` |
| Generator | Speakeasy CLI, pinned in `.speakeasy/workflow.yaml` |

## Rules

- The reference TypeScript repository is read-only evidence. Never modify it
  from this repository. Never import it at runtime.
- `PumbleOpenApi.yaml` in this repository is a byte-for-byte copy of the
  reference blob. Do not normalize or reformat it.
- Run `python tools/check_source_anchors.py` to verify the hashes and the
  parity manifests. The script fails on any drift.
- The manifests in `contracts/` are the machine-readable parity ledger:
  - `operations.json` — all 26 operations with read/write class.
  - `schemas.json` — all 32 schema names in document order.
  - `source_modules.json` — TypeScript extension module to Python module map.

## Source facts that must not drift

- Authentication uses the `ApiKey` request header.
- Production base URL: `https://pumble-api-keys.addons.marketplace.cake.com`.
- Read retry backoff: 500 ms initial, 30,000 ms max interval, 60,000 ms max
  elapsed, exponent 1.5, on HTTP 429/5xx and connection errors.
- Every write carries `x-sdk-no-write-retries: true` and must never be
  retried automatically.
- Error bodies are a union of legacy `{"error"}` and structured
  `{"message", "localizedMessage", "code"}` forms.
