# Pumble Python SDK/MCP — Implementation Status

- Reference commit: `cc20de10a6f0ce1efa9a57eb9509ff8e2324fe1e`
- OpenAPI SHA-256: `a9c3af3cc5de074b7112b63203ec6e1b686afebfe8751bc75df630efd2906a43`
- Rule: exactly one packet may be `IN_PROGRESS`.

| Packet | Status | Commit | Targeted tests | Full/fast gate | Notes |
|---|---|---|---|---|---|
| P00 — Anchor sources and create the parity ledger | DONE | p00 | `tools/check_source_anchors.py` — PASS | fast gate n/a (no toolchain yet) | Blob+SHA-256 verified; 26 ops / 32 schemas / 15 writes. |
| P01 — Create the clean Python repository and toolchain | DONE | p01 | `uv run pytest tests/unit/test_import.py` — PASS (1); 3.11 + 3.12 import OK | `uv sync --all-extras --dev` — PASS | `mcp[cli]==2.0.0` pinned; console scripts declared. |
| P02 — Add repository rules, generated ownership, and status tracking | DONE | p02 | `pytest tests/unit/test_repo_rules.py` — PASS (6) | `check_status.py` + `check_generated_boundaries.py` — PASS | Boundary checker rejects synthetic generated-path edit. |
| P03 — Configure a pinned Speakeasy Python target | NOT_STARTED | — | — | — | — |
| P04 — Generate and inventory the raw Python SDK | NOT_STARTED | — | — | — | — |
| P05 — Burn down generator defects without contaminating generated code | NOT_STARTED | — | — | — | — |
| P06 — Lock OpenAPI and generated contract fidelity | NOT_STARTED | — | — | — | — |
| P07 — Implement identifiers, display helpers, and redaction | NOT_STARTED | — | — | — | — |
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

- Packet: `P02` (DONE)
- Objective: Add repository rules, generated ownership, and status tracking.
- Allowed files: `CONTRIBUTING.md`, `IMPLEMENTATION_STATUS.md`, `contracts/generated-ownership.json`, `tools/check_generated_boundaries.py`, `tools/check_status.py`
- Exit condition: The repository can mechanically distinguish generated and hand-written changes.
- Started from commit: `45aed34` (p01)
- Findings: Ownership manifest defines `src/pumble_keys/**` as generated with six hand-written exception subtrees. P04 refines the exact emitted paths after first generation.
- Commands/results: `uv run pytest tests/unit/test_repo_rules.py` → 6 passed. `check_status.py` → OK. `check_generated_boundaries.py --paths src/pumble_keys/sdk.py` → exit 1 (synthetic edit rejected).
- Deviations/blockers: Added `tests/unit/test_repo_rules.py` beyond allowed files (packet evidence requires executable tests). The `--require-clean-generation` full-gate mode arrives with the regeneration workflow (P06/P44). No other deviation.

## Release evidence pointers

- Full offline receipt: —
- Live receipt: —
- Package smoke receipt: —
- Final audit: —
