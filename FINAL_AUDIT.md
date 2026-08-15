# Final adversarial parity and release audit (P45)

Audited state: commit `0321cc7` (p44) as pushed to origin, plus this
audit's own regeneration-normalization drift (gen.lock metadata + one
generator-refreshed README ToC line) committed with p45. Auditor: the
implementing session, running the plan's checks independently of the
per-packet claims.

## 1. Source manifests and parity (independent comparison)

Every TypeScript extension file at the pinned reference (`cc20de1`)
maps to a Python module or a recorded difference:

| TS (`sdk/src/extensions/`) | Python |
|---|---|
| branded-ids.ts | `extensions/ids.py` |
| categorize-error.ts | `extensions/errors.py` |
| client.ts | `extensions/client.py` (+ namespace split: `identity.py`, `channels.py`, `users.py`, `messages.py`, `status.py` — Python-side organization, recorded) |
| debug-redaction.ts | `extensions/redaction.py` |
| display.ts | `extensions/display.py` |
| facade-failure.ts | `extensions/results.py` |
| facade-operation.ts | `extensions/operations.py` |
| facade-writes.ts | `extensions/writes.py` |
| find.ts | `extensions/find.py` |
| index.ts | `extensions/__init__.py` (re-export surface) |
| list-all-messages.ts | `extensions/pagination.py` |
| rate-limiter.ts | `extensions/rate_limit.py` |
| resolve.ts | `extensions/resolve.py` |
| resolver-cache.ts | `extensions/resolver_cache.py` |
| resolver-preflight.ts | `extensions/preflight.py` |
| scheduled.ts | `extensions/scheduled.py` |
| search-all.ts | `extensions/search.py` |
| telemetry.ts | `extensions/telemetry.py` |
| thread-context.ts | `extensions/threads.py` |
| webhook-events.ts | `pumble_app/events.py` |
| webhooks.ts | `pumble_app/webhooks.py` |
| with-retries.ts | `extensions/retries.py` |
| write-plan.ts | `extensions/write_plan.py` |

All 26 operations, the 7 webhook types, resolver/pagination/CLI/
write-plan contracts, and the four MCP profile catalogs are replay-
verified (`tests/parity`, 53 tests; completeness meta-tests make a
missing operation or event type a failure). Intentional differences:
the 8-row table in `PARITY_MATRIX.md`. MCP server + App behavior is
Python-only scope, frozen in `fixtures/replay/mcp/manifests.json` and
the P25–P39 suites.

## 2. Adversarial sweep

| Search | Result |
|---|---|
| Write retries (`retry` in write paths) | None — only the documented "never through a retry helper" contract text; retries live in `retries.py` for idempotent reads only |
| `print(` outside the CLI | One, in `telemetry.py`, explicitly `file=sys.stderr` (audit-sink failure warning). MCP stdout carries only the wire |
| SSE / session-state assumptions | Only in rejection/documentation code (`transport.py` rejects `sse`; stateless HTTP default) |
| Plaintext secrets | `scan_secrets.py --all` clean over 435 tracked files (shape-based detectors; red-tested) |
| Manual edits to generated code | Boundary checker green; regeneration (below) byte-identical for all generated sources |
| Unguarded raw writes | Double gate (`--allow-raw-writes` + `--audit-log`) test-enforced; dry-run executes nothing |
| Dynamic/unbounded tool output | All curated/app tool outputs bounded (limits 10/50, catalog 200, excerpt 160) |
| Capability claims vs tests | Discover/caching/routing-header/MRTR/subscription claims each traced to `tests/mcp/test_mcp_2026_core.py`, `test_mrtr_writes.py`, `test_subscriptions.py`; no `logging` capability advertised |

## 3. Regeneration and determinism

- `speakeasy run --pinned` (pin 1.763.6, local CLI 1.793.0, generation
  2.928.0) re-run at audit time: after the documented version reset and
  pyproject patch, every generated SOURCE file is byte-identical; the
  only drift is gen.lock bookkeeping and a generator-refreshed README
  ToC line (both committed with p45). The generator's compile gate
  (pylint+mypy+pyright over all of `src/pumble_keys`, now including
  every P33–P44 module) passed.
- Two independent clones of the pushed commit ran the offline suite
  (662 passed / 10 skipped each — the extra skip vs. local is the
  packaged-asset comparison before the app build exists) and produced:
  identical `app/dist/index.html` sha256
  (`7dd83c2d…4a2a5`, equal to the committed `app_assets` manifest), and
  identical wheel per-file content digests (`68d1ed121d1a28cc`, 179
  entries, RECORD excluded, `SOURCE_DATE_EPOCH` pinned). Scope note:
  raw wheel bytes differ across checkouts through zip mtimes; the
  determinism claim is per-file content, stated exactly as compared.

## 4. Coverage (target: ≥95% line / ≥90% branch; security modules 100% branch)

`coverage run --branch` over the hand-written packages: **92% combined
(3697 statements, 976 branches)**. Security-critical modules:
`redaction.py` 100%, `oauth.py` 100%, `profiles.py` 100%,
`write_plan.py` 99% (one unreached defensive branch),
`webhooks.py` 91%, `auth.py` 88% (lines 87–89).

**OPEN WAIVER W1:** the 95% aggregate target and the 100%-branch bar
for `webhooks.py`/`auth.py` are not met. The uncovered paths are
defensive (header-shape edge cases, verifier-import failure arms).
This must be closed or explicitly re-waived before the first release
tag; P45's allowed files cannot add tests.

## 5. Gate deltas (documented, not silently substituted)

- `tools/check_version_consistency.py` (named in the plan's gate block)
  was never assigned to a packet and does not exist; the same check is
  enforced in `release.yml` ("Version consistency" step) and was run
  manually (tag-less equivalence: pyproject == `_version.py` == 0.1.0).
- The plan's `pytest --cov` invocation needs pytest-cov, which is not a
  dev dependency; `coverage run --branch -m pytest` (coverage 7.x) was
  used instead — same measurement, different runner.
- Full-gate live line executed: `run_live.py --profile full
  --require-cleanup` → 8 passed, 1 skipped (self-DM rejected by the
  live API), zero residue, receipt commit `0321cc7`.

## 6. Waivers and known limitations (consolidated from the status log)

| # | Item | State |
|---|---|---|
| W1 | Coverage below target (see §4) | OPEN — pre-release blocker |
| W2 | `/webhooks/pumble` mount is a proven seam but the stock CLI does not mount it; manual ASGI assembly required (documented in MCP.md); no `McpConfig` signing-secret field; lifespan `subscription_publisher` seat unused | Documented limitation |
| W3 | Live suite skips: self-DM and expired-status clear rejected by the live API; webhook/subscription live check needs ingress; channel create/membership ops untestable without residue (no channel delete exists) | Truthful skips in the receipt |
| W4 | `test_duplicate_cues_collapse` paces with `anyio.sleep(0.2)` — flake candidate on slow CI | Documented; lengthen if it flakes |
| W5 | Pre-audit generator README snippets were invalid Python; the audit regeneration emits valid ones — the GENERATOR_DEVIATIONS entry stays until confirmed on the next routine regeneration | Narrowed |
| W6 | dmUser/dmGroup request-wrapping bug found by the live run (P41), fixed with regressions | CLOSED |
| W7 | Node engines pin is `22.x`; local builds ran on Node 26 (engine-strict off); CI pins 22.12.0 | Documented |

## 7. Verdict

All 46 packets are `DONE`. Every mandatory offline gate passes twice
from clean clones of the pushed commit; the live suite passes with
zero residue against the sacrificial workspace; no secret finding; no
undocumented waiver. The candidate is **defensible and reproducible**,
and is ready for a separate, explicit release action **after W1 is
closed** (and the pre-launch credential rotation noted in the
repository's security policy is performed). Release evidence:
`RELEASE_EVIDENCE.json`.
