# TypeScript/Python parity matrix

Reference: the pinned TypeScript SDK source at
`psdk-reference/sdk/src/extensions/` (commit `cc20de1`), read-only.

**How "replayed through the TS contract" is implemented here:** the
pinned reference ships without `node_modules`, so the corpus does not
execute TypeScript. Each fixture in `fixtures/replay/` records (a) the
raw SDK input, (b) the expected NORMALIZED semantic output (canonical
JSON: sorted keys, `None` dropped), and (c) a `ts_source` reference to
the contract file at `cc20de1` its semantics were checked against. The
parity suite (`tests/parity/`) replays every fixture through the Python
implementation and compares canonical output — so port completeness is
evidence-based, and any behavioural drift breaks the suite.

Gates (mandatory, offline):

```bash
uv run python tools/sanitize_fixture.py --check   # no live data in the corpus
uv run pytest tests/parity                        # full replay suite
```

## Coverage

| Area | Fixtures | Parity test | TS contract source |
|---|---|---|---|
| All 26 generated operations (11 read + 15 write): adapter routing, request wrapping, kwargs cleaning, ok-envelope | `operations/*.json` (26; completeness meta-test against the manifest) | `TestOperations` | `client.ts` |
| Webhook normalization, all 7 event types (envelope + compact forms) | `webhooks/*.json` (7; completeness meta-test against `KNOWN_EVENT_TYPES`) | `TestWebhooks` | `webhook-events.ts` |
| Resolver: exact, case-insensitive, ambiguous (labeled choices), not-found, 24-hex passthrough, user by email/name | `resolver/*.json` (8) | `TestResolver` | `find.ts`, `resolve.ts`, `facade-failure.ts` |
| Pagination: boundary-overlap dedupe, cursor walk, `hasMoreBefore` stop | `pagination/list_all_messages_overlap.json` | `TestPagination` | `list-all-messages.ts` |
| CLI display goldens: key masking, channel/user/message/scheduled lines, emoji normalization | `cli/formatting.json` (6 cases) | `TestCliGoldens` | `display.ts` |
| MCP catalogs per profile (tools/resources/templates/prompts) | `mcp/manifests.json` (4 profiles) | `TestMcpManifests` | Python-only surface — see differences |
| Write-preview canonicalization: canonical JSON ordering/None-drop, text hash, request hash, excerpt bound | `write_plan/canonical.json` (5 vectors) | `TestWritePlanCanonicalization` | `write-plan.ts` |

## Intentional differences (recorded as they were made)

| # | Area | Difference | Why |
|---|---|---|---|
| 1 | Write receipts | Python receipts add the direct-read verification block (`verification_state`/detail); TS summary texts preserved verbatim | Plan-mandated write proof (P15) |
| 2 | Search/pagination | TS `AbortSignal` maps to asyncio task cancellation; no signal parameter | Language idiom (P13) |
| 3 | Error taxonomy | TS transient network codes (ECONNRESET…) map to `httpx.TransportError`/`ConnectionError`/`TimeoutError` | Runtime difference (P10) |
| 4 | Branded IDs | `ValueError` where TS throws `TypeError`; message text preserved | Python convention (P09) |
| 5 | CLI | stdlib `argparse` port; `schedule create` added (the TS CLI lacked it, plan command list requires it) | P25 plan directive |
| 6 | Prompts | `write_pumble_handler` rewritten for the Python SDK surface (no `ack()`, no TS syntax) | P30 plan directive |
| 7 | MCP server + App | The whole MCP surface (profiles, preview/confirm HMAC plans, MRTR, subscriptions, Apps) is Python-only — the TS reference has no MCP server | New scope of this project |
| 8 | Fixture IDs | Corpus uses the synthetic `0…0NNNN` 24-hex convention; the scanner rejects any other 24-hex shape | No-live-data rule |

`tools/scan_secrets.py` (repo-wide secret scan, `--changed`/`--all`) is
owned by P44's security gates; `sanitize_fixture.py` is the corpus
scanner and is already a gate as of P40.
