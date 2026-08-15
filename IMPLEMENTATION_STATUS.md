# Pumble Python SDK/MCP — Implementation Status

- Reference commit: `cc20de10a6f0ce1efa9a57eb9509ff8e2324fe1e`
- OpenAPI SHA-256: `a9c3af3cc5de074b7112b63203ec6e1b686afebfe8751bc75df630efd2906a43`
- Rule: exactly one packet may be `IN_PROGRESS`.

| Packet | Status | Commit | Targeted tests | Full/fast gate | Notes |
|---|---|---|---|---|---|
| P00 — Anchor sources and create the parity ledger | DONE | p00 | `tools/check_source_anchors.py` — PASS | fast gate n/a (no toolchain yet) | Blob+SHA-256 verified; 26 ops / 32 schemas / 15 writes. |
| P01 — Create the clean Python repository and toolchain | DONE | p01 | `uv run pytest tests/unit/test_import.py` — PASS (1); 3.11 + 3.12 import OK | `uv sync --all-extras --dev` — PASS | `mcp[cli]==2.0.0` pinned; console scripts declared. |
| P02 — Add repository rules, generated ownership, and status tracking | NOT_STARTED | — | — | — | — |
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

- Packet: `P01` (DONE)
- Objective: Create the clean Python repository and toolchain.
- Allowed files: `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `README.md`, `LICENSE`
- Exit condition: Empty package builds and imports with a locked dependency graph.
- Started from commit: `93c637a` (p00)
- Findings: `uv` resolves `mcp[cli]==2.0.0` on Python 3.11. Placeholder `src/pumble_keys/__init__.py` imports cleanly; the generator replaces it at P04.
- Commands/results: `uv sync --all-extras --dev` → PASS. `uv run pytest tests/unit/test_import.py` → 1 passed (Python 3.11.11). Isolated 3.12 wheel-install import → PASS.
- Deviations/blockers: Added `src/pumble_keys/__init__.py` and `tests/unit/test_import.py` beyond allowed files (required by the packet's own evidence). No other deviation.

## Release evidence pointers

- Full offline receipt: —
- Live receipt: —
- Package smoke receipt: —
- Final audit: —
