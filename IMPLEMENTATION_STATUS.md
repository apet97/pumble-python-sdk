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
