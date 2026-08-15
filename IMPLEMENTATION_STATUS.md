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
| P08 — Implement structured results and error categorization | DONE | p08 | `pytest tests/unit/test_results.py test_errors.py` — PASS (33) | ruff + pytest (161) + boundaries — PASS | 5 failure reasons, 6 error categories; cause/raw excluded from serialization. |
| P09 — Implement safe retry and in-process rate limiting primitives | DONE | p09 | `pytest tests/unit/test_retries.py test_rate_limit.py` — PASS (27) | ruff + pytest (188) + boundaries — PASS | Write callables rejected without explicit override; fake-clock bucket. |
| P10 — Implement deterministic user/channel resolution | DONE | p10 | `pytest tests/unit/test_resolve.py test_find.py` — PASS (16) | ruff + pytest (204) + boundaries — PASS | Exact TS precedence; ≤5 candidates in API order; values not exceptions. |
| P11 — Implement optional resolver cache and preflight | DONE | p11 | `pytest tests/unit/test_resolver_cache.py test_preflight.py` — PASS (15) | ruff + pytest (219) + boundaries — PASS | Fake-clock TTL; foreground-only refresh; concurrent preflight. |
| P12 — Port defensive exhaustive search and message pagination | DONE | p12 | `pytest tests/unit/test_search_all.py test_list_all_messages.py` — PASS (22) | ruff + pytest (241) + boundaries — PASS | Golden replay of same-second overlap, dupes, cap, abort. |
| P13 — Port compact thread context and reply helper | DONE | p13 | `pytest tests/unit/test_threads.py` — PASS (10) | ruff + pytest (251) + boundaries — PASS | Concurrent root/replies; first-seen participants; blank inputs rejected. |
| P14 — Build the async curated client façade and read namespaces | DONE | p14 | `pytest tests/unit/test_client_reads.py` — PASS (13) | ruff + pytest (264) + boundaries — PASS | 11 reads mapped; no global retry_config (regression test). |
| P15 — Port safe message/channel write façades | DONE | p15 | `pytest tests/unit/test_facade_writes.py` — PASS (14) | ruff + pytest (278) + boundaries — PASS | One attempt, direct-read proof, honest verification_failed. |
| P16 — Port scheduled-message façade | DONE | p16 | `pytest tests/unit/test_scheduled.py` — PASS (15) | ruff + pytest (293) + boundaries — PASS | Future-only integer send_at; verified create/edit; safe cancel. |
| P17 — Add custom-status helpers and invalidate affected caches | DONE | p17 | `pytest tests/unit/test_status.py` — PASS (7) | ruff + pytest (300) + boundaries — PASS | myInfo read-proof once; users cache invalidated only when verified. |
| P18 — Port telemetry and reusable testing helpers | DONE | p18 | `pytest tests/unit/test_telemetry.py test_testing_helpers.py` — PASS (24) | ruff + pytest (324) + boundaries — PASS | Attribute allowlist + canary leak scan; sanitizer/mock-transport port. |
| P19 — Port typed Pumble webhook event models | DONE | p19 | `pytest tests/unit/test_webhook_events.py` — PASS (27) | ruff + pytest (351) + boundaries — PASS | 7 events, envelope+compact forms, unknown fields preserved. |
| P20 — Port webhook signature verification and ASGI receiver | DONE | p20 | `pytest tests/unit/test_webhooks.py tests/integration` — PASS (20) | ruff + pytest (371) + boundaries — PASS | Raw-body HMAC, ±300 s window, 1 MiB limit, 401/400/413/204/500. |
| P21 — Port event router and `PumbleApp` convenience class | DONE | p21 | `pytest tests/unit/test_event_router.py test_pumble_app.py` — PASS (12) | ruff + pytest (383) + boundaries — PASS | Registration-order dispatch; first failure stops (TS parity). |
| P22 — Port Pumble OAuth helpers and token store protocol | DONE | p22 | `pytest tests/unit/test_oauth.py test_token_store.py` — PASS (17) | ruff + pytest (400) + boundaries — PASS | Exact URLs/fields; constant-time state; in-memory store only. |
| P23 — Port experimental Pumble Socket Mode as an optional extra | DONE | p23 | `pytest tests/unit/test_socket_mode.py` — PASS (12) | ruff + pytest (412) + mypy/pylint/pyright + boundaries + inventory — PASS | Injected transport; [socket] extra via gen.yaml; regen compile gate learned. |
| P24 — Port the one-shot SDK CLI | DONE | p24 | `pytest tests/cli` — PASS (20) | ruff + pytest (432) + mypy/pylint/pyright + boundaries — PASS | No plaintext key flag; file>stdin>env; exit 0/1/2; façade receipts. |
| P25 — Create MCP configuration, lifespan, and server factory | DONE | p25 | `pytest tests/mcp/test_server_factory.py` — PASS (18) | ruff + pytest (450) + mypy/pylint/pyright + boundaries — PASS | Official MCPServer v2; env/file key; readwrite gates in config. |
| P26 — Implement MCP entry point, transports, and remote authorization | DONE | p26 | `pytest tests/mcp` — PASS (49) | ruff + pytest (481) + mypy/pylint/pyright + boundaries — PASS | stdio + stateless HTTP; 421/403/413/401 proven at HTTP level; sse rejected. |
| P27 — Register the seven curated read tools | DONE | p27 | `pytest tests/mcp/test_curated_read_tools.py` — PASS (12) | ruff + pytest (493) + mypy/pylint/pyright + boundaries — PASS | Exact 7 tools; limits 10/50; failures as values via real client session. |
| P28 — Implement signed preview/confirmed MCP writes | DONE | p28 | `pytest tests/mcp/test_write_plan.py test_curated_write_tools.py` — PASS (18) | ruff + pytest (511) + mypy/pylint/pyright + boundaries — PASS | HMAC-bound preview/confirm; expiry/workspace/request/text/replay checks. |
| P29 — Register MCP resources with bounded payloads and safe paths | DONE | p29 | `pytest tests/mcp/test_resources.py` — PASS (11) | ruff + pytest (522) + mypy/pylint/pyright + boundaries — PASS | 6 URIs; traversal/symlink/extension containment; bounded live payloads. |
| P30 — Port prompts and add argument completions | DONE | p30 | `pytest tests/mcp/test_prompts.py test_completions.py` — PASS (12) | ruff + pytest (534) + mypy/pylint/pyright + boundaries — PASS | 4 prompts (Python guidance); bounded deterministic completions. |
| P31 — Implement readonly, raw readwrite, and dry-run profiles | DONE | p31 | `pytest tests/mcp/test_raw_profiles.py` — PASS (10) | ruff + pytest (544) + mypy/pylint/pyright + boundaries — PASS | Exact 11/26 adapters; double gate; audit per attempt; dry-run zero writes. |
| P32 — Adopt stateless discovery, routing headers, cache hints, and deterministic catalogs | DONE | p32 | `pytest tests/mcp/test_mcp_2026_core.py` — PASS (13) | ruff + pytest (557) + mypy/pylint/pyright + boundaries — PASS | Modern discover per profile; TTL hints on every cacheable class; header deny pre-body. |
| P33 — Add optional MRTR interactive send/reply tools | DONE | p33 | `pytest tests/mcp/test_mrtr_writes.py` — PASS (11) | ruff + pytest (568) + mypy/pylint(10.00)/pyright + boundaries — PASS | Curated-interactive only; Resolve/Elicit MRTR; accept = one write; decline/cancel = none. |
| P34 — Bridge Pumble webhooks to modern MCP subscriptions | DONE | p34 | `pytest tests/mcp/test_subscriptions.py` — PASS (13) | ruff + pytest (581) + mypy/pylint(10.00)/pyright + boundaries — PASS | Signature-gated `/webhooks/pumble`; URI-only refetch cues on the shared bus; in-process bus documented as single-process. |
| P35 — Scaffold the single MCP App frontend | DONE | p35 | `npm run typecheck && npm test` — PASS (12) | app typecheck/test/build + pytest (581) — PASS | Plain TS + Vite + ext-apps 1.7.5; single-file deterministic build; value-typed bridge; memory-only state enforced by test. |
| P36 — Register the MCP App opening tool and UI resource | DONE | p36 | `pytest tests/mcp/test_app_registration.py` — PASS (5) | ruff + pytest (586) + mypy/pylint(10.00)/pyright + boundaries — PASS | One `Apps()` extension on app profiles; nested `_meta.ui` only; closed CSP; text/structured fallback. |
| P37 — Implement App read/browse/search/thread flows | DONE | p37 | `npm test` — PASS (25) + `pytest tests/mcp/test_app_registration.py` — PASS (7) | app typecheck/test/build + pytest (588) + mypy/pylint(10.00)/pyright — PASS | Three-pane/narrow UI; cursor paging; bounded search; textContent-only rendering; typed error states. |
| P38 — Implement App composer with preview and explicit confirmation | DONE | p38 | `npm test` — PASS (36) | app typecheck/test/build + pytest (588) — PASS | Preview-first composer; edit invalidation; no auto-retry; token never rendered or stored. |
| P39 — Finish App accessibility, host integration, and packaging | NOT_STARTED | — | — | — | — |
| P40 — Create sanitized replay corpus and TypeScript/Python parity tests | NOT_STARTED | — | — | — | — |
| P41 — Build the live sacrificial-workspace verification suite | NOT_STARTED | — | — | — | — |
| P42 — Write user and maintainer documentation | NOT_STARTED | — | — | — | — |
| P43 — Harden packaging and fresh-environment smoke tests | NOT_STARTED | — | — | — | — |
| P44 — Implement CI, security gates, and release workflow | NOT_STARTED | — | — | — | — |
| P45 — Perform final adversarial parity and release audit | NOT_STARTED | — | — | — | — |

## Current packet detail

- Packet: `P38` (DONE)
- Objective: Implement App composer with preview and explicit confirmation.
- Allowed files: updates under `app/src/`, `app/test/write-flows.test.ts`
- Exit condition: The UI cannot send or reply without an explicit user-visible preview/confirmation sequence.
- Started from commit: `07568bf` (p37)
- Commands/results:
  - `npm run typecheck --prefix app` → clean; `npm test --prefix app` → 36 passed (write-flows adds 11); `npm run build` → deterministic single file, external-reference scan still zero; full `pytest` → 588.
  - Composer (`app/src/composer.ts`): channel message and thread reply only — no other write, no raw/destructive operation reachable from the App. The first action is always `send_message_preview`/`reply_to_thread_preview`; the card shows resolved target name, redacted excerpt, risk level, expiry timestamp, and the full-text sha256 prefix (12).
  - Confirm: a separate button sends the UNCHANGED request + preview + token (asserted equal in the fake-bridge call log). The token and previewed request live in the controller closure — not in rendered state; the DOM scan proves the token never appears, and the storage scan still covers all of `app/src`.
  - Edit invalidation: changing text, channel, or mode drops the held preview; a confirm without a matching snapshot is blocked locally with a "request a new preview" error and no server call.
  - Safety: `busy` disables both buttons (gated-promise double-click test → exactly one confirmed call); a failed confirmed write clears the token and sets `needsNewPreview` — a second confirm cannot re-send (never auto-repeat). Server rejection (tamper/expiry, exercised via a `confirmation_expired` failure value) and transport failure both surface as errors distinct from the verification receipt, which renders its own `verification_state`/detail on success.
  - Server-side tamper/expiry/replay enforcement itself was proven in P28; the App tests prove the client passes bindings through unchanged and respects rejections.
- Deviations: `app/src/composer.ts` added (new file under the allowed `app/src/`); `app_assets/index.html` regenerated from the rebuilt bundle.

- Packet: `P37` (DONE)
- Objective: Implement App read/browse/search/thread flows.
- Allowed files: updates under `app/src/`, `app/test/read-flows.test.ts`, Python app-helper tests
- Exit condition: The App is genuinely useful for Pumble browsing without bypassing the MCP server.
- Started from commit: `810c6e6` (p36)
- Commands/results:
  - `npm run typecheck --prefix app` → clean; `npm test --prefix app` → 25 passed (bridge 12 + read-flows 13); `pytest tests/mcp/test_app_registration.py` → 7 (two new helper tests); full `pytest` → 588.
  - Layout (`render.ts`): desktop = channel rail + message/search pane + thread pane; `narrow: true` renders exactly one pane with a Back control (`back()` walks thread → messages → channels). Narrow flag driven by `matchMedia("(max-width: 640px)")` in `main.ts`.
  - Bootstrap (`flows.ts` → `pumble_ui_bootstrap`): identity, channel catalog with case-insensitive filter (`filteredChannels`) and channel-type labels, compact author map (`authorLabel` falls back to the raw id).
  - Paging: `pumble_ui_channel_page` with explicit `cursor` (asserted in the fake-bridge call log), pages append, exhausted cursor makes loadMore a no-op. Search: requires a non-blank query (no server call otherwise) and calls the curated `search_messages` with a bounded limit (25). Thread: exact `channel_id`/`message_id`.
  - Rendering safety: every dynamic value goes through `textContent`; the XSS test renders `<img onerror>`/`<script>` payloads and asserts no such elements exist while the raw text is displayed verbatim. No rich-text subset shipped (plain text only — the plan's escape-tests precondition for rich text was not spent).
  - States: loading, empty, recoverable error, auth error (`classifyFailure` maps permission/401/403), rate-limit (rate/429), and stale-data (failed refetch keeps items and flags `stale`). Request dedup: identical in-flight (tool,args) calls collapse to one bridge call (gated-promise test).
  - Every byte the app shows comes through `bridge.callTool` — no fetch, no direct API path (P35's external-URL scan still holds on the rebuilt bundle).
- Deviations: `app/src/flows.ts` added (new file under the allowed `app/src/`); `happy-dom` 20.11.2 added as an exact-pinned dev dependency for DOM tests; `app_assets/index.html` regenerated from the rebuilt deterministic bundle (hash test keeps it in sync); the P36 mock raw client's message page shape fixed to the real `result.messages` form.

- Packet: `P36` (DONE)
- Objective: Register the MCP App opening tool and UI resource.
- Allowed files: `src/pumble_keys/mcp_server/app.py`, `app_tools.py`, `app_assets/index.html` (generated from `app/dist`), `tests/mcp/test_app_registration.py`
- Exit condition: Exactly one interactive MCP App is discoverable and has a non-UI fallback.
- Started from commit: `732f38a` (p35)
- Commands/results:
  - `uv run pytest tests/mcp/test_app_registration.py -q` → 5 passed (red-first: collection failed before implementation); `pytest` → 586 passed.
  - Extension: `create_apps_extension` builds the official `mcp.server.apps.Apps()`; `create_server` passes it via `extensions=[...]` for `APP_ENABLED_PROFILES` only. Discover proves `io.modelcontextprotocol/ui` advertised on curated and absent on readonly (no app tools/resource there either).
  - Opening tool `open_pumble_workspace`: model-visible, read-only annotations, bound to `ui://pumble/workspace/v1/index.html` via the modern nested `_meta.ui.resourceUri` — asserted that the pre-GA flat `ui/resourceUri` key is absent. Returns a structured payload (identity id+name — no email, channel count, `capabilities.apps` from `client_supports_apps(ctx)`, `writes: preview_confirm`) whose JSON doubles as the text fallback; proven against a client that did NOT negotiate Apps.
  - App-only helpers `pumble_ui_bootstrap` / `pumble_ui_channel_page` / `pumble_ui_thread`: `visibility: ["app"]` stamped in `_meta.ui`; all go through the same façade layer as the curated tools (no second read path, no writes). Bootstrap bounds the author map (200) and channel catalog (200).
  - Resource: served as `text/html;profile=mcp-app`; `_meta.ui.csp = {connectDomains: [], resourceDomains: []}` (closed) and no `permissions` key; `resources/read` returns the packaged HTML byte-for-byte.
  - Packaged asset: `app_assets/index.html` copied from the P35 deterministic build; test compares sha256 against `app/dist/index.html` when present (`72aa1a8c…404af`).
- Deviations:
  - `server.py`: extension wiring in `create_server` (the P25 comment reserved this seat for P36); `extensions` remains override-able via server kwargs.
  - `app_assets/__init__.py` added (importlib.resources package anchor — the P24 knowledge precedent).
  - Catalog snapshots updated for the extension surface: `tests/mcp/test_server_factory.py`, `test_curated_read_tools.py`, `test_resources.py` (extension tools/resource list first — extension consumption precedes the profile registrars).
  - Known for P43: `[tool.setuptools.package-data]` does not yet include `app_assets/*.html` (or `knowledge/*.md`); the packaging packet must extend the documented pyproject patch.

- Packet: `P35` (DONE)
- Objective: Scaffold the single MCP App frontend.
- Allowed files: `app/package.json`, `app/tsconfig.json`, `app/vite.config.ts`, `app/src/main.ts`, `bridge.ts`, `state.ts`, `render.ts`, `styles.css`, `types.ts`
- Exit condition: A minimal secure App shell can be packaged by Python.
- Started from commit: `59fd7a4` (p34)
- Commands/results:
  - `npm run typecheck --prefix app` → clean; `npm test --prefix app` → 12 passed (vitest run, not watch); `npm run build --prefix app` → one self-contained `dist/index.html` (~342 KB).
  - Stack: plain TypeScript (7.0.2) + Vite (8.2.1, rolldown) + official `@modelcontextprotocol/ext-apps` 1.7.5 with its pinned peers `@modelcontextprotocol/sdk` 1.30.0 and `zod` 4.4.3 — no React. All versions exact-pinned; `engines.node: 22.x`; scripts named `typecheck`/`test`/`build` to match the plan's full-gate commands verbatim.
  - Bridge (`bridge.ts`): built against the introspected installed API (`App.connect`, `callServerTool`, `getHostContext`, `ontoolresult`, `onhostcontextchanged` — NOT from memory). `HostApp` is a structural subset so tests inject a fake host with no MCP connection. Every outcome is a value (`ToolSuccess`/`BridgeFailure` with `tool_error`/`protocol_error`/`malformed_result`), mirroring the Python façade contract; the `{"result": ...}` union envelope is unwrapped exactly like the Python test harness.
  - State (`state.ts`): in-memory store only; a test scans `app/src` and fails on any persistent-storage API. Render (`render.ts`): all dynamic values via `textContent`; no innerHTML anywhere.
  - Deterministic build: two consecutive builds hash sha256-identical (`72aa1a8c…404af`). External-reference scan of the built HTML: zero `src=`/`href=` http(s) references, zero `url(http`, zero `@import`; the only `fetch(` is Vite's inert modulepreload polyfill (no preload links exist in a single file) and the only URL strings are zod's validation/schema literals — nothing fetchable is referenced.
  - Vite 8 finding: `minify: "esbuild"` now fails (esbuild no longer bundled — rolldown/oxc is the default); the config uses the default minifier. `vite-plugin-singlefile` 2.3.3 (pinned) produces the single-file output; recorded as the documented dependency decision (the plan names no inliner).
- Deviations (infrastructure, beyond the allowed list): `app/index.html` (Vite entry), `app/package-lock.json` (P43 runs `npm ci`), `app/src/vite-env.d.ts` (CSS-module TS declaration), `app/test/bridge.test.ts` (the packet's required unit tests). Local build ran on Node 26 (`engines` pins 22.x, engine-strict off); CI pins Node 22 in P44.

- Packet: `P34` (DONE)
- Objective: Bridge Pumble webhooks to modern MCP subscriptions.
- Allowed files: `src/pumble_keys/mcp_server/subscriptions.py`, `webhook_bridge.py`, `tests/mcp/test_subscriptions.py`
- Exit condition: Live Pumble changes can invalidate client context through the new subscription model.
- Started from commit: `8909ef5` (p33)
- Commands/results:
  - `uv run pytest tests/mcp/test_subscriptions.py -q` → 13 passed (red-first: collection failed on the missing modules before implementation); `pytest` → 581 passed.
  - Cues (`subscriptions.py`): message events → channel context URI (+ thread URI when a reply); reactions → channel + rooted thread; channel-created → `pumble://channels`; uninstall/unauthorize → `pumble://me` + `pumble://channels`; workspace membership → no cue. Cues are URIs with IDs only — proven that message text never reaches an event or the stream.
  - Delivery seam: `EventPublisher` protocol; the SDK's `SubscriptionBus` satisfies it. One `InMemorySubscriptionBus` is passed to both `create_server(..., subscriptions=bus)` and the bridge. The module docstring states plainly that the in-process bus is single-process and that multi-replica deployments need a shared `SubscriptionBus` adapter (none is pretended).
  - Webhook mount (`webhook_bridge.py`): `mount_pumble_webhooks` adds a `POST /webhooks/pumble` Starlette route to `server.streamable_http_app(...)` beside `/mcp`; protection is the P20 Pumble HMAC receiver (timestamp tolerance, 1 MiB bound), not MCP bearer auth. Bad signature → 401 and zero publishes (bus listener capture).
  - End to end over real transports: signed POST via `httpx.ASGITransport` → 204 → `ResourceUpdated` arrives on an open `client.listen(...)` stream (official modern client) → the client refetches `pumble://channels` and reads fresh content.
  - Listen semantics proven: ack echoes the honored URI filter; a cue for an unsubscribed channel is withheld (exact filters; unsubscribed thread URI withheld too — no unsolicited events); three identical cues pending together collapse to one delivered event (the catalog cue proves the stream advanced); a raising bus listener is isolated from other listeners.
  - Slow-subscriber bound: per-stream backlog cap and end-at-cap behavior live in the SDK's `ListenHandler` (documented in the module docstring); clients re-listen and refetch — no replay.
  - SDK findings: the HTTP `session_manager.run()` exit runs the shared server lifespan teardown and clears the stashed static-resource state, so tests that mix the HTTP app with the in-process client keep the whole flow inside the manager context.
- Deviations: none — only the three allowed files were touched.
- Known limitation (recorded for the P45 audit): `mount_pumble_webhooks` is a proven seam but no deployment path calls it yet — the CLI's `run_server` hands off to `server.run(transport="streamable-http")`, which builds its own ASGI app, so a real deployment cannot mount `/webhooks/pumble` without assembling the app itself. The Pumble signing secret also has no `McpConfig` field yet, and the lifespan's `subscription_publisher` seat stays `None`. Wiring (CLI flag or documented manual-ASGI deployment) lands with the P42 documentation or earlier.

- Packet: `P33` (DONE)
- Objective: Add optional MRTR interactive send/reply tools.
- Allowed files: `src/pumble_keys/mcp_server/tools/interactive.py`, `dependencies.py`, `tests/mcp/test_mrtr_writes.py`
- Exit condition: MRTR improves supported-host UX without replacing the portable default safety path.
- Started from commit: `7a37e0d` (p32)
- Commands/results:
  - `uv run pytest tests/mcp/test_mrtr_writes.py -q` → 11 passed; `pytest` → 568 passed.
  - Registration: `send_message_interactive` and `reply_to_thread_interactive` register only on `curated-interactive` (`_INTERACTIVE_REGISTRARS` seat in the factory); the curated snapshot proves their absence elsewhere.
  - Schema invisibility: the `Resolve`-injected `resolved` and `outcome` parameters and the `Context` never appear in the model input schema — model-visible properties are exactly `channel`/`text` (+`message_id` for reply), asserted from the listed tool schemas.
  - Deterministic question (`dependencies.confirmation_question`): resolved target label, redacted excerpt, sha256 prefix, risk level — no random IDs, no timestamps. Proven identical across two rounds and different per target via the official `mcp.client.client.Client(mode="auto", elicitation_callback=...)` capture.
  - Confirmation semantics: accept + `send=true` → exactly one façade write with the direct read-by-ID verification receipt (`fetch_message` call count asserted); decline/cancel/accept-with-`send=false` → zero writes and a structured `CuratedFailure` (`confirmation_declined`/`_cancelled`/`_accepted`); channel-resolution failure skips the question AND the write; a raw API failure after accept stays a structured value. One shared façade write path with the preview/confirm tools — no duplicate safety logic.
  - SDK findings: the consumer opts into the full accept/decline/cancel union ONLY when the parameter is annotated exactly as `ElicitationResult[T]` (or members); wrapping it in `... | None` defeats the SDK's `_wants_union` detection and injects the unwrapped model (decline then aborts the call). `ctx` must be annotated `Context`, or the SDK treats it as a model-visible string argument. Elicit accept injects `AcceptedElicitation(data=T)`.
  - Fast gate: ruff (hand-written paths) + `pytest` (568) + mypy/pylint(10.00)/pyright (all on the hand-written src packages) + boundaries + inventory `--check` + `git diff --check` — all PASS.
- Deviations:
  - `server.py`: one-line wiring of `_register_interactive` into the existing `_INTERACTIVE_REGISTRARS` seat (the seat was scaffolded in P25 for exactly this packet); `tests/mcp/test_server_factory.py` snapshot extended with the two new curated-interactive tools.
  - `tools/raw_read.py` (P31 file): removed a dead `except asyncio.CancelledError: raise` arm and its function-local `asyncio` import — `CancelledError` is a `BaseException`, so the broad `except Exception` below never caught it; the arm and the local import were pylint findings (W0706/C0415) that earlier broad-scope pylint runs had rounded away. Gate pylint now runs scoped to the hand-written src packages and scores a true 10.00.

- Packet: `P32` (DONE)
- Objective: Adopt stateless discovery, routing headers, cache hints, and deterministic catalogs.
- Allowed files: `src/pumble_keys/mcp_server/cache_policy.py`, `middleware.py`, updates to registrations, `tests/mcp/test_mcp_2026_core.py`
- Exit condition: The server receives the concrete scale/cache/routing benefits of the 2026 revision.
- Started from commit: `78b4bf8` (p31)
- Commands/results:
  - `uv run pytest tests/mcp/test_mcp_2026_core.py -q` → 13 passed; `pytest tests` → 557 passed.
  - Discover: modern `server/discover` snapshot for all four profiles via the official in-process `mcp.client.client.Client` (mode "auto" and pinned "2026-07-28" — per-request envelope, NO initialize handshake): server name, `2026-07-28` in supported_versions, tools/prompts/resources/completions capabilities present, no `logging` capability. Legacy compatibility proven separately: the memory-stream harness (initialize handshake era) lists identical tools against the same server object. We implement no lifecycle RPC of our own.
  - Cache hints (`cache_policy.py`, wired through the factory as `MCPServer(cache_hints=...)`): catalogs + discover → private/60 s; `resources/read` → private/5 s (live-data bound; method-level hint, per-result opt-out documented for the P36 immutable App HTML). Asserted on every cacheable result class through real client calls (`ttl_ms`/`cache_scope`).
  - Deterministic catalogs: byte-stable JSON of tools/resources/templates/prompts across fresh server instances (curated + readonly) and repeated list calls in one session — registration order only, no sets, no import-order dependence.
  - Routing headers (`middleware.py`): `HeaderToolPolicy` (pure ASGI edge middleware) denies `tools/call` for a named raw write from the `Mcp-Method`/`Mcp-Name` headers with 403 BEFORE any body read (receive-call count asserted zero); allowed calls pass through the real streamable HTTP app. `MethodMetricsMiddleware` (official `ServerMiddleware` seat, `ctx.method`) proves route-aware metrics via `MCPServer(middleware=[...])`.
  - SDK findings: the 2026 client mirrors the method/name into `mcp-method`/`mcp-name` HTTP headers (constants in `mcp.shared.inbound`); `mcp.client.client.Client` is the official modern in-process client (memory ClientSession is handshake-era only); `DiscoverResult` carries `supported_versions`, not server_info (server info arrives via the client handshake state).
  - Fast gate: ruff + pytest + mypy/pylint(10.00)/pyright + boundaries + `git diff --check` — all PASS.
- Deviations: `server.py` passes `cache_hints` by default (override-able via server kwargs).

- Packet: `P31` (DONE)
- Objective: Implement readonly, raw readwrite, and dry-run profiles.
- Allowed files: `src/pumble_keys/mcp_server/tools/raw_read.py`, `raw_write.py`, `raw_manifest.py`, `dry_run.py`, `tests/mcp/test_raw_profiles.py`
- Exit condition: Complete OpenAPI access exists but is impossible to enable accidentally.
- Started from commit: `f4f2483` (p30)
- Commands/results:
  - `uv run pytest tests/mcp/test_raw_profiles.py -q` → 10 passed; `pytest tests` → 544 passed.
  - `raw_manifest.py`: checked-in manifest of all 26 operations in OpenAPI document order (11 reads / 15 writes) with typed parameter specs mirrored from the generated signatures; contract test asserts manifest ids/methods/paths equal `contracts/operations.json`. Destructive flags: removeUserFromChannel, deleteMessage, removeReaction, deleteScheduledMessage.
  - `raw_read.py`/`raw_write.py`: data-driven adapters with real typed input schemas (dynamic `__signature__`+`__annotations__`; ctx injected, excluded from schema); every adapter calls the sanctioned raw escape hatch (`client.raw.<ns>.<op>_async`) — no business fork; results/failures are structured JSON values. Readonly registers exactly 11 (incl. POST `/searchMessages`); readwrite exactly 26. Every operation adapter exercised through a real session.
  - Gates: config validation (gate 1) plus `raw_write.register` re-check raising `RawWriteGateError` (gate 2) — both proven. Curated profile exposes zero raw tools.
  - Audit: every write logs redacted `attempt` + `success`/`failure` events to the JSONL sink (30 events for 15 writes; failure path: attempt+failure with exactly one API call — never retried).
  - Dry-run: write tools titled "DRY-RUN SIMULATION", read-only annotated, return the planned method/path/destructive flag and redacted arguments; zero write endpoints touched (asserted across all 15).
  - Annotations: destructive→`destructive_hint`, all writes non-idempotent/open-world; reads read-only/idempotent.
  - Fast gate: ruff + pytest + mypy/pylint(10.00)/pyright + boundaries + `git diff --check` — all PASS.
- Deviations: `server.py` wires the raw registrars into the readonly/readwrite seats; factory snapshot updated.

- Packet: `P30` (DONE)
- Objective: Port prompts and add argument completions.
- Allowed files: `src/pumble_keys/mcp_server/prompts.py`, `completions.py`, `tests/mcp/test_prompts.py`, `test_completions.py`
- Exit condition: The MCP server preserves reusable workflows and improves target entry without extra model calls.
- Started from commit: `ecd16eb` (p29)
- Commands/results:
  - `uv run pytest tests/mcp/test_prompts.py tests/mcp/test_completions.py -q` → 12 passed; `pytest tests` → 534 passed.
  - `prompts.py` ports the four curated prompts (`summarize_thread`, `draft_reply`, `write_pumble_handler`, `debug_pumble_webhook`) with deterministic text; `write_pumble_handler` is rewritten for Python (`PumbleApp`, Pydantic `Notification*` bodies, `asgi_app()`; no `ack()`, no TypeScript syntax — asserted); `draft_reply` states "do not claim it was sent" and routes sending through preview→explicit-confirm; `debug_pumble_webhook` embeds the user payload verbatim in a fenced block, rejects unparseable JSON, and instructs never to request secrets in chat.
  - `completions.py` registers the completion handler: event names (sorted) and knowledge paths for the resource templates; channel names (API list order) and user names/emails for prompt arguments — all filtered by the partial value, bounded to 20 with `total`/`has_more`, empty on listing failure (never an error), zero secrets. All proven through real `session.complete` calls.
  - Fast gate: ruff + pytest + mypy/pylint(10.00)/pyright + boundaries + `git diff --check` — all PASS.
- Deviations: `server.py` wires the prompts/completions registrar into the curated and readonly seats; factory snapshot updated.

- Packet: `P29` (DONE)
- Objective: Register MCP resources with bounded payloads and safe paths.
- Allowed files: `src/pumble_keys/mcp_server/resources.py`, `src/pumble_keys/knowledge/*`, `tests/mcp/test_resources.py`
- Exit condition: Resources provide reusable context without unbounded model payloads.
- Started from commit: `3d1dd6d` (p28)
- Commands/results:
  - `uv run pytest tests/mcp/test_resources.py -q` → 11 passed; `pytest tests` → 522 passed.
  - Registered (deterministic order, byte-stable across fresh servers): static `pumble://me` and `pumble://channels`; templates `pumble://channel/{channel_id}`, `pumble://thread/{channel_id}/{message_id}`, `pumble://knowledge/{+path}`, `pumble://events/{name}`. Live payloads compact and bounded (catalog first 100 with `truncated`, channel last 20 messages, thread ≤50 replies); live failures serialize as structured JSON values; MIME types application/json / text/markdown asserted through real session reads.
  - Knowledge: packaged Markdown under `src/pumble_keys/knowledge/` (index + 2 guides) via `importlib.resources`. `resolve_knowledge_path` enforces containment: relative-only, no null bytes, resolved-path must stay under the root (kills `../` and symlink escapes — symlink attack tested), extension allowlist `.md/.txt`, missing file → not-found. The SDK's default `ResourceSecurity` adds its own traversal/absolute/null rejection in front.
  - `pumble://events/{name}`: field guide + sanitized example for each of the seven webhook events; unknown names raise a resource error.
  - SDK findings: static (no-variable) resources cannot receive a `Context` — the lifespan now stashes `AppState` on the server object (`server.pumble_app_state`) and static handlers read it; `{+path}` templates are supported, `{path*}` is not; client-side attrs are snake_case (`uri_template`, `mime_type`).
  - Fast gate: ruff + pytest + mypy/pylint(10.00)/pyright + boundaries + `git diff --check` — all PASS.
- Deviations: `lifespan.py` stashes/clears state on the server (required by the static-resource limitation); `server.py` wires the resources registrar into the curated and readonly seats; factory snapshot updated; `knowledge/__init__.py` added so `importlib.resources.files` resolves a real path.

- Packet: `P28` (DONE)
- Objective: Implement signed preview/confirmed MCP writes.
- Allowed files: `src/pumble_keys/mcp_server/tools/write.py`, `src/pumble_keys/extensions/write_plan.py`, `tests/mcp/test_curated_write_tools.py`, `test_write_plan.py`
- Exit condition: Default writes are inspectable and cryptographically bound to the confirmed request.
- Started from commit: `02ab499` (p27)
- Commands/results:
  - `uv run pytest tests/mcp/test_write_plan.py tests/mcp/test_curated_write_tools.py -q` → 18 passed; `pytest tests` → 511 passed.
  - `write_plan.py` ports write-plan.ts (canonical JSON, 160-char redacted excerpt, full-text SHA-256, risk inference, `pumble-write-plan-v1.` HMAC-SHA256 base64url token, timing-safe verify) plus the plan-mandated hardening: previews carry `issued_at_ms`/`expires_at_ms` (default 5-minute TTL), the workspace fingerprint, and a canonical `request_sha256`. `validate_confirmation` checks signature→expiry→workspace→request→text, all failing closed. `ReplayGuard` is a bounded in-memory used-token store (FIFO eviction); the one-worker/shared-store requirement for multi-worker write deployments is documented on the class and in the config field.
  - `tools/write.py` registers exactly `send_message_preview`, `send_message_confirmed`, `reply_to_thread_preview`, `reply_to_thread_confirmed`. Previews are read-only/idempotent and never write ("Nothing was sent" summaries; zero write calls asserted). Confirmed tools re-resolve the target (mismatch → `confirmation_target_mismatch`), verify the full plan, consume the replay guard, and perform ONE non-retried façade write with the direct-read receipt (`verification_state=verified`; exactly 1 write + 1 fetch asserted).
  - Cross-instance proofs: two servers sharing `PUMBLE_CONFIRMATION_SECRET` verify each other's previews (stateless-HTTP contract); a different secret rejects. Tamper matrix through a real session: changed text → request_mismatch, changed channel → target_mismatch, edited preview or token → invalid_token, duplicate token → replayed; expiry proven via direct validation (an edited expiry breaks the signature by design). Ephemeral stdio secret behavior covered in P25.
  - Workspace binding: `AppState.workspace_fingerprint` = keyed SHA-256 fingerprint of the credential (16 hex chars) — binds confirmations to one workspace without exposing the key.
  - Fast gate: ruff + pytest + mypy/pylint(10.00)/pyright + boundaries + `git diff --check` — all PASS.
- Deviations (narrow): `config.py` gains `confirmation_replay_size` (default 1024); `lifespan.py` gains `workspace_fingerprint` + `replay_guard` on AppState; `server.py` wires the write registrar; P25/P27 manifest snapshots updated for the four new tools.

- Packet: `P27` (DONE)
- Objective: Register the seven curated read tools.
- Allowed files: `src/pumble_keys/mcp_server/tools/read.py`, `models.py`, `tests/mcp/test_curated_read_tools.py`
- Exit condition: Default model tool surface has compact workflow-first reads.
- Started from commit: `c1f7912` (p26)
- Commands/results:
  - `uv run pytest tests/mcp/test_curated_read_tools.py -q` → 12 passed; `pytest tests` → 493 passed.
  - `tools/read.py` registers exactly `whoami`, `find_channel`, `find_user`, `list_channels`, `search_messages`, `get_channel_context`, `get_thread_context` in that order; every tool is read-only/idempotent/closed-world (`ToolAnnotations` asserted); handlers call the lifespan-owned curated client via `Context.request_context.lifespan_context` — no business logic fork.
  - `models.py` holds the compact Pydantic surface (union returns `X | CuratedFailure`); limits `ge=1, le=50` with default 10 enforced in the input schema (bounds asserted from `tools/list`; limit 51 → schema validation error before any Pumble call).
  - Behavior proven over the real in-memory client session (new `tests/mcp/harness.py`: lowlevel server run over memory streams — full initialize/lifespan/request-context path): compact whoami (no token in payload), find success + not-found/ambiguous as structured values (`is_error=False`), choices capped at 5 with labels, list filter + truncation flag (500 channels → 50 + `truncated`), search requires ≥1 filter and issues exactly one page call, channel context returns compact messages + explicit `next_cursor` (last id only when `hasMoreBefore`) + `pumble://channel/...` resource URI, thread context compact with participants/reply_count + thread URI, transport errors → `transport_error` value.
  - SDK findings recorded: `MCPServer.call_tool` alone has no request context — the memory-stream harness is the correct in-process test path; union-typed tool returns wrap structured content as `{"result": ...}` (harness `structured()` unwraps); `Tool.input_schema` is the snake_case accessor.
  - Fast gate: ruff + pytest + mypy/pylint(10.00)/pyright + boundaries + `git diff --check` — all PASS.
- Deviations: `server.py` wires `_register_curated_reads` into the curated registrar seat (the seat was designed for exactly this); P25's snapshot test updated for the now-populated curated profiles; `tools/__init__.py` + `tests/mcp/harness.py` added as infrastructure.

- Packet: `P26` (DONE)
- Objective: Implement MCP entry point, transports, and remote authorization.
- Allowed files: `src/pumble_keys/mcp_server/cli.py`, `transport.py`, `auth.py`, `tests/mcp/test_mcp_cli.py`, `test_auth.py`, `test_transport.py`
- Exit condition: The same packaged server runs safely as a local subprocess or remote stateless service.
- Started from commit: `d0a66d1` (p25)
- Commands/results:
  - `uv run pytest tests/mcp -q` → 49 passed.
  - `transport.py`: `stdio` (default) and `streamable-http` only; `sse` rejected with a clear "superseded" error; defaults 127.0.0.1:2718 `/mcp`; deployed HTTP uses `stateless_http=True` and keeps the SDK's 4 MiB body limit; non-loopback bind without a token verifier fails closed; `--unsafe-no-auth` allows it with a loud stderr WARNING; DNS-rebinding `TransportSecuritySettings` with Host/Origin allowlists (loopback defaults or explicit entries).
  - HTTP-level proofs against the real Streamable HTTP ASGI app (httpx ASGITransport + session manager): stateless `tools/list` → 200; wrong Host → 421; wrong Origin → 403 (the SDK's code — recorded; plan's generic "reject" satisfied); oversized body → 413; with a token verifier + `AuthSettings`: missing bearer → 401, wrong token → 401, valid token → 200.
  - `auth.py`: official `TokenVerifier`/`AuthSettings` only — `build_auth_settings` (issuer, resource URL, required scopes; no client-registration/DCR configuration, asserted), `StaticTokenVerifier` (dev/test; unknown/expired fail closed), `load_token_verifier("module:attr")` for provider-neutral production verifiers via `PUMBLE_MCP_TOKEN_VERIFIER`.
  - `cli.py`: `pumble-keys-mcp` argparse entry; secret-bearing flags (`--api-key`, `--api-key-auth`, `--confirmation-secret`) rejected with exit 2 before parsing; profile/gates flags flow into `McpConfig.from_env`; a configured verifier requires `--auth-issuer` + `--auth-resource-url`; exit codes 0/1/2; KeyboardInterrupt → clean 0; injectable runner for tests. Finding: `MCPServer` requires `auth` settings whenever `token_verifier` is set — the CLI enforces the pairing.
  - Fixed a cross-directory pytest module-name collision (`test_auth.py` exists in `tests/contract` and `tests/mcp`) by adding `__init__.py` to the test packages.
  - Fast gate: ruff + `pytest tests` → 481 passed; mypy/pylint(10.00)/pyright clean; boundaries — PASS; `git diff --check` clean.
- Deviations: `tests/*/__init__.py` files added (collection infrastructure).

- Packet: `P25` (DONE)
- Objective: Create MCP configuration, lifespan, and server factory.
- Allowed files: `src/pumble_keys/mcp_server/config.py`, `lifespan.py`, `server.py`, `profiles.py`, `tests/mcp/test_server_factory.py`
- Exit condition: All MCP behavior can be composed from one deterministic factory.
- Started from commit: `67afe96` (p24)
- Commands/results:
  - `uv run pytest tests/mcp/test_server_factory.py -q` → 18 passed.
  - Uses official `mcp.server.MCPServer` (v2; API confirmed by introspecting the installed `mcp==2.0.0`: constructor takes `lifespan`, `token_verifier`, `auth`, `cache_hints`, `subscriptions`, `middleware`, `extensions`; decorators `tool/resource/prompt/completion`; `run(transport=stdio|sse|streamable-http)` with `stateless_http` and 4 MiB default body limit on the HTTP runner — recorded for P26/P32).
  - `profiles.py`: immutable `Profile` enum (`curated`, `curated-interactive`, `readonly`, `readwrite`) + `APP_ENABLED_PROFILES`; `dry_run` is a readwrite option, not a profile.
  - `config.py`: frozen `McpConfig`; API key from env `PUMBLE_API_KEY` or `PUMBLE_API_KEY_FILE` (file wins) — never a tool argument; key and confirmation secret excluded from dump and repr; readwrite requires `allow_raw_writes` AND `audit_log_path` at construction (re-checked at registration in P31); `dry_run` outside readwrite rejected; unknown profile rejected.
  - `lifespan.py`: `make_lifespan`/`build_state` own one curated async client (resolver cache enabled with TTL), optional `RateLimiter`, `ConfirmationSigner` (configured shared secret → not ephemeral; else 32-byte ephemeral for stdio), optional redacted `JsonlAuditWriter`, and the P34 publisher seat. `aclose` closes exactly once (proven; also on error paths); single-workspace note in docstrings and server instructions.
  - `server.py`: `create_server(config)` composes `MCPServer` with the lifespan and profile-selected registrar seats in a fixed order (curated ⊂ curated-interactive; readonly ⊂ readwrite — order proven); per-profile tool/resource/prompt snapshots pinned (empty until P27+); `client_factory` injection for tests; extra kwargs (P26 auth) pass through; `log_level=WARNING`, no stdout writes.
  - Fast gate: ruff + `pytest tests` → 450 passed; mypy/pylint(10.00)/pyright clean; boundaries — PASS; `git diff --check` clean.
- Deviations: `mcp_server/__init__.py` added (package infrastructure).

- Packet: `P24` (DONE)
- Objective: Port the one-shot SDK CLI.
- Allowed files: `src/pumble_keys/cli/main.py`, `formatting.py`, `tests/cli/test_cli.py`, `test_cli_quiet.py`
- Exit condition: Packaged CLI covers the existing user workflows with safer secret handling.
- Started from commit: `5392b61` (p23)
- Commands/results:
  - `uv run pytest tests/cli -q` → 20 passed.
  - `main.py` ports pumble-keys-cli.mjs onto stdlib `argparse` (custom parser raises usage errors instead of exiting): commands `doctor`, `whoami`, `channels list|find|create`, `users find`, `send`, `dm`, `search`, `messages`, `thread`, `status set|clear`, `schedule list|create|cancel` (`schedule create` added per the plan's command list; the TS CLI lacked it). All commands run through the curated façade (`create_pumble_client`; injectable for tests) — writes get façade receipts with direct-read verification, no duplicated business logic. Explicit 24-hex IDs skip resolution.
  - Safety improvement over TS (plan-mandated): NO plaintext API-key flag exists. Credential precedence proven: `--api-key-file` > `--api-key-stdin` > `PUMBLE_API_KEY`. `doctor` masks the key (last 4 only); no secret appears in any output.
  - Output contract: `--json` writes machine JSON to stdout (`formatting.to_jsonable` handles generated pydantic models, receipts, dataclasses); human listings go to stdout; write success prose goes to stderr as a diagnostic; `--quiet` suppresses success prose but never JSON, read output, or errors (all four proven). Exit codes 0/1/2 (façade failure summaries → exit 1 with choices; argparse/usage → exit 2).
  - Emoji-code normalization (`palm_tree` → `:palm_tree:`) lives only in the CLI (`formatting.normalise_emoji_code`), per P17.
  - Fast gate: ruff (hand-written paths) — PASS; `pytest tests` → 432 passed; mypy/pylint(10.00)/pyright all clean (one pyright narrowing fix in `socket_mode.py` included); boundaries — PASS; `git diff --check` clean.
- Deviations: `cli/__init__.py` added (package infrastructure); one-line pyright fix in `pumble_app/socket_mode.py` needed to keep the generator compile gate green.

- Packet: `P23` (DONE)
- Objective: Port experimental Pumble Socket Mode as an optional extra.
- Allowed files: `src/pumble_keys/pumble_app/socket_mode.py`, `tests/unit/test_socket_mode.py`, `docs/EXPERIMENTAL.md`
- Exit condition: Experimental parity exists without imposing a hidden production policy.
- Started from commit: `d2c4c49` (p22)
- Commands/results:
  - `uv run pytest tests/unit/test_socket_mode.py -q` → 12 passed.
  - `socket_mode.py` ports app/socket-mode.ts: transport injection only (`connect` without `create_socket` raises `PumbleSocketModeUnsupportedError` "not bundled"); 25-second default ping started on `open` (injectable interval timer, cancelled on close/disconnect), `pong` ignored; JSON frames `{payload, correlation_id}`; `PUMBLE_EVENT`/`APP_EVENT` accepted; unsupported message/event types raise the dedicated error; malformed frames raise `ValueError`; events normalize through the shared P19 model (`normalize_webhook_event`) and dispatch through the P21 router; context value-or-factory; correlation ID surfaced in the dispatch result; cleanup removes listeners exactly once. Protocol evidence constant preserved.
  - `[socket]` optional dependency (`websockets>=13.0`) added via `.speakeasy/gen.yaml` `optionalDependencies` (config route) and regenerated; concrete adapter is a documented example only in `docs/EXPERIMENTAL.md` — no bundled transport, no hidden reconnect policy.
  - Coverage: string/bytes frames, pong, malformed JSON/missing payload/non-dict payload, unsupported types, missing correlation ID, ping lifecycle + cleanup, close-event cleanup, `on_error` routing, context factory, idempotent connect/disconnect.
  - Fast gate: ruff (hand-written paths) + `pytest tests` → 412 passed; mypy/pylint(10.00)/pyright clean; boundaries `--generator-run` — PASS; inventory rebuilt and byte-identical; `git diff --check` clean.
- Findings (recorded in docs/GENERATOR_DEVIATIONS.md):
  - The generator's "Compile SDK" step runs pylint+mypy+pyright over ALL of `src/pumble_keys` including hand-written code and fails generation on any finding. Fixed 4 real mypy/pyright findings in P14–P19 code (typed body cast, explicit `WriteVerification`, declared bound attributes, isinstance narrowing) and added inline pragmas for deliberate patterns.
  - Mishap + recovery: one `ruff --fix src` invocation reformatted generator-owned files; restored them byte-identical from HEAD before commit and added a NEVER-lint-generated-paths rule to the deviations doc.
  - Version-reset procedure updated per advisor guidance: text-reset gen.yaml/pyproject/_version.py/gen.lock only, then `uv lock` (never text-edit the lock).
- Deviations: `.speakeasy/gen.yaml` touched for the config-expressible `[socket]` extra; small hand-written fixes in P14–P19 files required to pass the generator's compile gate; `pumble_app/__init__.py` re-exports.

- Packet: `P22` (DONE)
- Objective: Port Pumble OAuth helpers and token store protocol.
- Allowed files: `src/pumble_keys/pumble_app/oauth.py`, `token_store.py`, `tests/unit/test_oauth.py`, `test_token_store.py`
- Exit condition: Pumble OAuth helper parity is available without conflating it with MCP OAuth.
- Started from commit: `32c1305` (p21)
- Commands/results:
  - `uv run pytest tests/unit/test_oauth.py tests/unit/test_token_store.py -q` → 17 passed.
  - `oauth.py` ports app/oauth.ts: consent URL `https://app.pumble.com/access-request` and access URL `https://api-ga.pumble.com/oauth2/access` as overridable defaults; ≥1 user/bot scope required; bot scopes prefixed `bot:`; `redirectUrl`/`clientId`/`scopes`/`defaultWorkspaceId`/`state`/`isReinstall` fields preserved with proper URL encoding; access-token request builds form fields `client-id`/`client-secret`/`code`; `verify_pumble_oauth_callback` extracts `code`/`state` with constant-time (`hmac.compare_digest`) state comparison; blank fields rejected with the TS error texts.
  - `token_store.py` ports app/token-store.ts: `TokenStore` async `Protocol` (runtime-checkable) with initialize/get_bot_token/get_user_token/get_bot_user_id/save_tokens/delete_for_workspace/delete_for_user; `InMemoryTokenStore` process-local (save merges bot fields only when present; deletes are narrow no-op-safe). No plaintext filesystem persistence ships.
  - Fast gate: ruff — PASS; `pytest tests` → 400 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `pumble_app/__init__.py` re-exports (continuation).

- Packet: `P21` (DONE)
- Objective: Port event router and `PumbleApp` convenience class.
- Allowed files: `src/pumble_keys/pumble_app/router.py`, `app.py`, `tests/unit/test_event_router.py`, `test_pumble_app.py`
- Exit condition: Python users can build Pumble webhook applications without MCP.
- Started from commit: `e5905d8` (p20)
- Commands/results:
  - `uv run pytest tests/unit/test_event_router.py tests/unit/test_pumble_app.py -q` → 12 passed.
  - `router.py` ports event-router.ts: `on(type, handler)` chains; `dispatch(event, context)` runs handlers in registration order (sync or async), returns `DispatchResult(handled=n)`. Failure semantics preserved from TS: the first failing handler stops dispatch and raises `PumbleEventHandlerError` with the exact `Pumble event handler failed for <TYPE>: <message>` text and `__cause__` chained; `CancelledError` propagates raw.
  - `app.py` ports pumble-app.ts: `PumbleApp(signing_secret=...)` wires P20 verification to the router via `on_event`; `.event(type)` works as decorator or direct call; `handle_webhook(raw_body, headers)` is the framework-neutral entry; `asgi_app()`/`starlette_route(path)` expose the P20 adapters. Docstrings state this is the integration helper, not the MCP App.
  - Coverage: zero/one/multiple handlers, order, async handlers, shared context, error callback (`on_error` receives `PumbleEventHandlerError`, response 500), all seven events routed independently, type isolation, invalid signature never reaches the router, ASGI end-to-end.
  - Fast gate: ruff — PASS; `pytest tests` → 383 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `pumble_app/__init__.py` re-exports (continuation).

- Packet: `P20` (DONE)
- Objective: Port webhook signature verification and ASGI receiver.
- Allowed files: `src/pumble_keys/pumble_app/webhooks.py`, `asgi.py`, `tests/unit/test_webhooks.py`, `tests/integration/test_webhook_asgi.py`
- Exit condition: Pumble webhook ingress is framework-safe and evidence-compatible.
- Started from commit: `183f593` (p19)
- Commands/results:
  - `uv run pytest tests/unit/test_webhooks.py tests/integration -q` → 20 passed (15 unit + 5 ASGI integration over `httpx.ASGITransport`).
  - `webhooks.py` ports webhooks.ts: `x-pumble-request-timestamp`/`x-pumble-request-signature` verified against HMAC-SHA256 of `<timestamp>:<raw-body>` (bytes exactly as received; never parse-then-reserialize), timing-safe hex compare with shape checks, seconds-or-milliseconds timestamps, ±300 s default tolerance, 1 MiB default body limit, injectable clock. Response contract proven: 401 (missing/bad/stale/wrong-secret/tampered/malformed-hex), 400 (malformed JSON / malformed envelope body / unsupported type), 413 (over limit, before verification), 204 (dispatched), 500 (handler raised → `on_error` gets the original error). `CancelledError` in a handler propagates instead of becoming 500. `sign_pumble_request` exposed for tests/tooling.
  - The receiver is framework-neutral (`(raw_body, headers) -> WebhookResult`); dispatch accepts a per-type handler map and/or a catch-all `on_event` (the P21 router plugs in there).
  - `asgi.py` ports http-receiver.ts: minimal ASGI app (POST-only, 405 otherwise) reading the body incrementally with the size limit enforced during the read; `starlette_route` adapter (lazy import) proven with a real Starlette app.
  - Fast gate: ruff — PASS; `pytest tests` → 371 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `pumble_app/__init__.py` re-exports (continuation).

- Packet: `P19` (DONE)
- Objective: Port typed Pumble webhook event models.
- Allowed files: `src/pumble_keys/pumble_app/events.py`, `tests/unit/test_webhook_events.py`
- Exit condition: Webhook and socket transports share one event model.
- Started from commit: `6a386f7` (p18)
- Commands/results:
  - `uv run pytest tests/unit/test_webhook_events.py -q` → 27 passed.
  - `events.py` ports webhook-events.ts plus the normalizer from webhooks.ts (the normalizer is an event-model concern; P20 imports it): seven event types; Pydantic bodies with the compact wire fields (`aId`, `cId`, `tx`, `mId`, `eph`, …) exposed as snake_case attributes with wire-name aliases; `extra="allow"` preserves unknown fields through round-trip; `PumbleWebhookEvent` carries type/body/workspace_id/workspace_user_ids plus the raw payload excluded from serialization and repr.
  - `normalize_webhook_event` supports the full envelope (`eventType` + dict-or-JSON-string `body` + `workspaceId`/`workspaceUserIds`, with workspace recovery from the body's `wId`/`workspace`) and the compact `ty` form. Unknown types and malformed payload shapes → `None`; a malformed JSON-string envelope body raises `ValueError` (TS parity; P20 maps to HTTP 400).
  - Coverage: one sanitized fixture per event in both forms, wire-name access, unknown-field preservation, malformed cases, invalid workspaceUserIds dropped, raw exclusion.
  - Fast gate: ruff — PASS; `pytest tests` → 351 passed; boundaries — PASS (pumble_app/** is a hand-written exception); `git diff --check` clean.
- Deviations: added `pumble_app/__init__.py` (package infrastructure for the named module).

- Packet: `P18` (DONE)
- Objective: Port telemetry and reusable testing helpers.
- Allowed files: `src/pumble_keys/extensions/telemetry.py`, `src/pumble_keys/testing/*`, `tests/unit/test_telemetry.py`, `test_testing_helpers.py`
- Exit condition: Later MCP/CLI tests can share deterministic fixtures and safe observability.
- Started from commit: `c20ebb6` (p17)
- Commands/results:
  - `uv run pytest tests/unit/test_telemetry.py tests/unit/test_testing_helpers.py -q` → 24 passed.
  - `telemetry.py`: `create_otel_span_recorder` (real recorder when `opentelemetry-api` importable, `NoopRecorder` otherwise — proven both ways: poisoned `sys.modules` → noop; installed → real tracer); `filter_span_attributes` enforces the §10.7 allowlist (operation_id, http_method, status_class/code, retry_count, duration_ms, result_category, bounded counts, error_class) and redacts surviving strings; `JsonlAuditWriter` appends redacted JSONL, creates the file mode 0600, warns once on stderr and never raises; `traced(name, awaitable, ...)` — no-recorder/no-writer mode is a plain await; CancelledError propagates unrecorded; failures record error class, never the message.
  - Finding: `opentelemetry-api` is present transitively via `mcp[cli]==2.0.0`. The "no required telemetry dependency" evidence is therefore asserted against this project's own `[project.dependencies]` (no opentelemetry entry) plus the poisoned-import no-op test.
  - `testing/`: `fixtures.py` ports the TS sanitizer contract (sequential 24-zero ID placeholders, `user-N@example.invalid`, `User N`/`example-name-<sha8>`, avatar URL, `[redacted]` text fields, embedded ID/email scrubbing) and the canonical key-sorted SHA-256 body hash; `mock_transport.py` ports mock-fetch onto `httpx.MockTransport` (method + sorted path/query + sanitized body hash, FIFO, miss raises — proven against the real generated `PumbleSDK` sync and async); `clocks.FakeClock`; `factories.py` builds valid generated models with sanitized defaults.
  - Canary leak scanner: pmb_ key, live email, 24-hex ID, and message text never survive span attributes or audit lines.
  - Fast gate: ruff — PASS; `pytest tests` → 324 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P17` (DONE)
- Objective: Add custom-status helpers and invalidate affected caches.
- Allowed files: `src/pumble_keys/extensions/status.py`, updates to `client.py`, `tests/unit/test_status.py`
- Exit condition: Status workflow is safe and consistent with other verified writes.
- Started from commit: `e290129` (p16)
- Commands/results:
  - `uv run pytest tests/unit/test_status.py -q` → 7 passed.
  - `status.py`: `StatusFacade.set_status(code, expires_at, status=None)` uses the exact OpenAPI payload (`code` in `:emoji_name:` form, `expiresAt` epoch-ms integer, 0 = never; optional field omitted when absent; no silent emoji normalization — that stays a P24 CLI convenience). `clear_status` writes an already-expired status (`expires_at=1`), matching the documented "past timestamp clears immediately" semantics.
  - After a successful write, exactly one `myInfo` read-proof; never a write retry (transient 503 → one attempt). Verified success invalidates the resolver cache's `users` entries; failed proof returns an honest `verification_failed` receipt and does NOT invalidate.
  - Wired as `client.users.set_status` / `client.users.clear_status` (client.py in the allowed list this packet); manifest snapshot updated.
  - Fast gate: ruff — PASS; `pytest tests` → 300 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P16` (DONE)
- Objective: Port scheduled-message façade.
- Allowed files: `src/pumble_keys/extensions/scheduled.py`, `tests/unit/test_scheduled.py`
- Exit condition: Scheduled workflows match the TypeScript façade contract.
- Started from commit: `c9ef6eb` (p15)
- Commands/results:
  - `uv run pytest tests/unit/test_scheduled.py -q` → 15 passed.
  - `scheduled.py` ports scheduled.ts: `ScheduledFacade` with create/list/get/edit/cancel; channel resolution shares the same target rules as P15 (explicit ID skips resolution unless `validate_target=True`); `send_at` must be an integer epoch-ms strictly greater than the injected clock (`now_ms` injectable; bool/float/str/past/equal all rejected before any API call). Create/edit receipts carry scheduled-message ID, channel ID, optional resolved channel, returned object, and §10.4 direct-read verification via `fetchScheduledMessage`. Cancel: one delete attempt (transient 503 → one attempt, failure value), receipt `verification.state="not_verifiable"` claiming nothing beyond the API response. `list` without channel passes through; with channel resolves first; page normalized to the result body.
  - Fast gate: ruff — PASS; `pytest tests` → 293 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `client.py` swaps the P14 `ScheduledReads` placeholder for `ScheduledFacade` (same wiring rationale as P15); manifest snapshot in `test_client_reads.py` updated; `extensions/__init__.py` re-exports.

- Packet: `P15` (DONE)
- Objective: Port safe message/channel write façades.
- Allowed files: `src/pumble_keys/extensions/writes.py`, `tests/unit/test_facade_writes.py`
- Exit condition: User-visible writes have precise receipts and cannot be duplicated by internal retry.
- Started from commit: `5b832c3` (p14)
- Commands/results:
  - `uv run pytest tests/unit/test_facade_writes.py -q` → 14 passed.
  - `writes.py` ports facade-writes.ts plus the plan-mandated direct-read verification (§10.4). `FacadeWrites` implements `send_message`, `dm_user`, `dm_group`, `reply_to_thread`, `create_channel`, and `search_recent` (a read; kept here for TS parity). Flow per write: shape validation → resolve unless explicit ID (with `validate_target=True` forcing resolution) → exactly one write call, never via a retry helper (proven with a transient 503: one attempt, failure value) → direct fetch by returned ID (`fetchMessage` for messages/replies/DMs, `getChannel` for channel create) → `WriteReceipt` with factual summary, ids, resolved target, write reference, and `WriteVerification`.
  - Write success + failed direct read → `ok=True` receipt with `verification.state="verification_failed"` and a detail stating the write was NOT retried and no rollback happened. Search is never used as proof (asserted: zero search calls in send flow).
  - TS parity texts preserved (`Sent message X to #chan.`, `Sent DM X to Name.`, `Replied with X in #chan.`); Python difference: receipts add the verification block (plan-mandated).
  - Fast gate: ruff — PASS; `pytest tests` → 278 passed; boundaries — PASS; `git diff --check` clean.
- Deviations (narrow, documented):
  - `client.py` (P14 file) wires the write façades into the namespaces (`messages.send/dm/dm_group`, `threads.reply`, `channels.create`, `search.recent`) — the same wiring split as client.ts/facade-writes.ts; without it the packet's exit condition is untestable through the public client.
  - `tests/unit/test_client_reads.py` namespace snapshot updated for the newly wired members.
  - `extensions/__init__.py` re-exports (continuation).

- Packet: `P14` (DONE)
- Objective: Build the async curated client façade and read namespaces.
- Allowed files: `src/pumble_keys/extensions/client.py`, `identity.py`, `channels.py`, `users.py`, `messages.py`, `tests/unit/test_client_reads.py`
- Exit condition: A stable ergonomic read API exists above the generated client.
- Started from commit: `8de2d77` (p13)
- Commands/results:
  - `uv run pytest tests/unit/test_client_reads.py -q` → 13 passed.
  - `create_pumble_client(api_key, server_url=, timeout_ms=, resolver_cache=, raw=)` → `PumbleClient` with `.raw`, `.identity`, `.channels`, `.users`, `.messages`, `.search`, `.scheduled` (reads), `.threads`, `.preflight`, `.cache`; namespace manifest snapshot-tested. Async-only (no nested loops); async context manager delegates to the generated client's `__aenter__/__aexit__`.
  - All 11 reads map to the expected generated `_async` callables with kwargs preserved (recorder-fake proof). Page wrappers normalized: `getChannel`→`.channel`, `listMessages`/`searchMessages`/`fetchScheduledMessages`/`fetchThreadReplies`→`.result`. Normal read errors become `FacadeFailure` values via `operation_failure`; `CancelledError` re-raises.
  - Facade find channel/user: pydantic `FindChannelSuccess`/`FindUserSuccess` (`Found channel #x.` / `Found user Y.`) or labeled `FacadeFailure`; `preflight` wires both. Resolver cache: disabled by default (proven: 2 resolves → 2 list calls, zero cache metrics), `resolver_cache=True`/dict enables (1 list call, 1 hit; `cache.clear/info/metrics/refresh`).
  - Safety: blank api_key rejected; non-HTTPS server_url rejected outside localhost; generated client built WITHOUT global `retry_config` — regression test asserts `sdk_configuration.retry_config is UNSET` (carry-forward from P04/P09 closed); api key never stored on the façade.
  - Fast gate: ruff — PASS; `pytest tests` → 264 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `Search`/`Threads`/`ScheduledReads`/`Messaging`/`CacheNamespace` classes live inside `client.py` (small, no extra files beyond the allowed list); `extensions/__init__.py` re-exports (continuation).

- Packet: `P13` (DONE)
- Objective: Port compact thread context and reply helper.
- Allowed files: `src/pumble_keys/extensions/threads.py`, `tests/unit/test_threads.py`
- Exit condition: Thread behavior is compact, predictable, and reusable by MCP resources.
- Started from commit: `554d110` (p12)
- Commands/results:
  - `uv run pytest tests/unit/test_threads.py -q` → 10 passed.
  - `threads.py` ports thread-context.ts: `get_thread_context` validates nonblank channel/message IDs and positive finite `reply_limit` before any fetch, fetches root (`fetchMessage`) and replies (`fetchThreadReplies` with `root_message_id`) concurrently (`asyncio.gather`, concurrency proven by event ordering), returns compact `ThreadContext` (root/replies as `ThreadContextMessage` with ISO-Z timestamp, first-seen deduped participant IDs with blanks skipped, `reply_count` from `threadRootInfo.replyCount` else the reply list length). `reply_to_thread` requires explicit channel/root IDs, rejects blank text before dispatch, forwards extra fields, sends exactly once, no retry.
  - Fetchers are injected async callables (P14 binds the generated `_async` operations), matching the P12/P10 pattern.
  - Coverage: concurrency, reply slicing + limit forwarding, participant dedupe/order, server count and fallback, blank inputs (no fetch), invalid limits (0/-1/NaN/bool), API failure propagation, reply extras, blank-reply rejection.
  - Fast gate: ruff — PASS; `pytest tests` → 251 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P12` (DONE)
- Objective: Port defensive exhaustive search and message pagination.
- Allowed files: `src/pumble_keys/extensions/search.py`, `pagination.py`, `tests/unit/test_search_all.py`, `test_list_all_messages.py`
- Exit condition: No exhaustive helper can silently loop forever or duplicate results.
- Started from commit: `2615205` (p11)
- Commands/results:
  - `uv run pytest tests/unit/test_search_all.py tests/unit/test_list_all_messages.py -q` → 22 passed.
  - `search.py` ports search-all.ts as a lazy async generator over an injected page fetcher (P14 binds `search_messages_async`): ID dedupe, same-second boundary overlap (`before_ts = min_ts + 1000`, ≤3 attempts) then cursor `min_ts - 1`, stops on empty page / repeated first ID / zero new IDs / `hasMore=false` with short page / missing timestamps / non-advancing cursor; hard 10,000-page cap (`PageCapExceededError`); `max_results`, `max_pages`, `on_page` observer (accurate counts before yields; raising aborts). Cancellation is plain task cancellation and propagates. Python difference (recorded): TS `AbortSignal` maps to `asyncio` cancellation; no signal parameter.
  - `pagination.py` ports list-all-messages.ts: default `BEFORE` strategy, opaque last-message-ID cursor, `has_more_before`/`has_more_after` per strategy (null → stop), dedupe, repeated-cursor bail, same cap/observer/limits.
  - Golden replay coverage: same-second boundary recovery, overlap cap, duplicate pages, missing timestamps, contradictory `hasMore` (false + full page walks on; false + short page stops), max-results mid-page, early `break` fetches no further page, page-cap guard, cancellation, observer counts and abort.
  - Fast gate: ruff — PASS; `pytest tests` → 241 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P11` (DONE)
- Objective: Implement optional resolver cache and preflight.
- Allowed files: `src/pumble_keys/extensions/resolver_cache.py`, `preflight.py`, `tests/unit/test_resolver_cache.py`, `test_preflight.py`
- Exit condition: Resolve-before-act can be reused safely across CLI, MCP, and App.
- Started from commit: `36c839e` (p10)
- Commands/results:
  - `uv run pytest tests/unit/test_resolver_cache.py tests/unit/test_preflight.py -q` → 15 passed.
  - `resolver_cache.py` ports resolver-cache.ts: `ResolverCache` wraps a source client and satisfies the same resolver protocols; TTL-bounded entries per kind (fake monotonic clock injectable — plan-mandated change from TS `Date.now()`), foreground-only reload, `refresh_on_miss=False` serves stale, `clear` (whole or per-kind for P15/P17 invalidation), `info`, `metrics` (hits/misses/evictions), failed load self-evicts, concurrent callers share one in-flight task (shielded from caller cancellation), stores source objects, never persists. `enabled=False` is a pure passthrough — proven to make zero cache reads/writes.
  - `preflight.py` ports resolver-preflight.ts: `preflight_resolvers` resolves channel/user concurrently (`asyncio.gather`, concurrency proven by an event-ordering test), `ok` only when every requested target resolved, failure keeps both underlying results for diagnostics, performs no write.
  - Fast gate: ruff — PASS; `pytest tests` → 219 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P10` (DONE)
- Objective: Implement deterministic user/channel resolution.
- Allowed files: `src/pumble_keys/extensions/resolve.py`, `find.py`, `tests/unit/test_resolve.py`, `test_find.py`
- Exit condition: Resolvers match the TypeScript behavioral contract exactly.
- Started from commit: `4c95397` (p09)
- Commands/results:
  - `uv run pytest tests/unit/test_resolve.py tests/unit/test_find.py -q` → 16 passed.
  - `resolve.py`: exact precedence (user: id→email→name→partial-name; channel: id→name→partial, one leading `#` stripped), trim + case-insensitive default with `case_insensitive=False` option, blank input → `not_found` with zero API calls, duplicate exact matches → `ambiguous`, candidates capped at 5 (overridable) in API list order, labels via the P07 formatters. Results are frozen dataclasses `ResolveSuccess`/`ResolveFailure` — values, never exceptions. Clients are `Protocol`s (`list_users`/`list_channels` async), so P14 binds them to the generated calls and tests use fakes.
  - `find.py`: `find_user_by_email` / `find_channel_by_name` thin conveniences returning the object or `None`.
  - Fast gate: ruff — PASS; `pytest tests` → 204 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P09` (DONE)
- Objective: Implement safe retry and in-process rate limiting primitives.
- Allowed files: `src/pumble_keys/extensions/retries.py`, `rate_limit.py`, `tests/unit/test_retries.py`, `test_rate_limit.py`
- Exit condition: Network resilience exists without duplicate-creating write retries.
- Started from commit: `c087346` (p08)
- Commands/results:
  - `uv run pytest tests/unit/test_retries.py tests/unit/test_rate_limit.py -q` → 27 passed.
  - `retries.py` ports with-retries.ts (transient-only via `categorize_error`, jittered exponential backoff `base_ms*2^attempt*(0.5+rng())`, `max_attempts`/`max_delay_ms`, `Retry-After` delta-seconds and HTTP-date parsing capped at max delay, `on_retry` observer, injectable sleep/rng/wall-clock). Safety tightening per plan: `with_retries` refuses any callable that is not a manifest read (`operation_id` in `READ_OPERATION_IDS`, contract-tested equal to `contracts/operations.json`), not marked `mark_safe_to_retry`, and lacks `unsafe_allow_write_retry=True`. `asyncio.CancelledError` re-raises before categorization — never counted, categorized, or slept on.
  - `rate_limit.py` ports rate-limiter.ts: bucket starts full at `burst`, fractional refill at `rps`, cap at burst, optional bounded queue with dedicated `RateLimitQueueFullError`, FIFO drain via injectable monotonic clock + timer, cancellation-safe waits (cancelled waiter leaves the queue; token passes to the next). A failing call still costs its token. Integration test proves the limiter inside the retry loop charges one token per attempt.
  - Fast gate: ruff — PASS; `pytest tests` → 188 passed; boundaries — PASS; `git diff --check` clean.
- Carry-forward note for P14 (from P04 finding): generated writes honor a client-wide `retry_config`; `create_pumble_client` must construct the generated client WITHOUT a global `retry_config`, and P14 needs a regression test for that.
- Deviations: `extensions/__init__.py` re-exports (continuation).

- Packet: `P08` (DONE)
- Objective: Implement structured results and error categorization.
- Allowed files: `src/pumble_keys/extensions/results.py`, `errors.py`, `operations.py`, `tests/unit/test_results.py`, `test_errors.py`
- Exit condition: Every later façade function has one uniform failure contract.
- Started from commit: `9342015` (p07)
- Commands/results:
  - `uv run pytest tests/unit/test_results.py tests/unit/test_errors.py -q` → 33 passed.
  - `results.py`: frozen Pydantic `FacadeFailure` (`ok=False`, 5 reasons, summary, labeled bounded choices, next_actions); `cause` excluded from dump and repr; `create_facade_failure` reproduces the exact TS summary/next-action text; `assert_facade_ok` raises `FacadeError` carrying the failure value.
  - `errors.py`: `categorize_error` ports the exact 8-step classification (403+structured→validation; 401/403→permission; 404→not-found; 429→rate-limit retryable; 408/425/5xx→transient retryable; 400/422+structured→validation; transport→transient; else unknown). Python difference: TS transient network codes (ECONNRESET…) map to `httpx.TransportError`/`ConnectionError`/`TimeoutError`. Works over generated `Error` (`.data` union), `PumbleSDKError` (body JSON parse), and arbitrary exceptions; `raw` excluded from serialization.
  - `operations.py`: `operation_failure_reason` (status_code→api_error else transport_error), `operation_failure` builder, `is_facade_operation_failure`, `OPERATION_FAILURE_NEXT_ACTION` constant — same texts as facade-operation.ts.
  - Fast gate: ruff format/check — PASS; `pytest tests` → 161 passed; boundaries — PASS; `git diff --check` clean.
- Deviations: `extensions/__init__.py` re-exports the new symbols (continuation of the P07 export surface).

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
