# Live testing (sacrificial workspace only)

Normal CI never talks to Pumble: `tests/live` collects as skipped
unless `PUMBLE_LIVE=1` is set explicitly. The live suite exists to
prove real API behavior against a workspace that is EXPENDABLE.

## Requirements (environment only)

| Variable | Meaning |
|---|---|
| `PUMBLE_LIVE=1` | Explicit opt-in; nothing runs without it. |
| `PUMBLE_API_KEY` | The sacrificial workspace's key. Environment only — never a file, argv, fixture, or log. The runner rejects key-shaped argv values. |
| `PUMBLE_LIVE_CHANNEL_ID` | The sacrificial channel. Its presence in the key's channel list is the workspace marker; the session aborts before any write if it is missing. |
| `PUMBLE_LIVE_RECEIPT` | Optional receipt path (default `live_receipt.json`, gitignored). |

## Running

```bash
PUMBLE_LIVE=1 uv run python tools/run_live.py --profile full --require-cleanup
PUMBLE_LIVE=1 uv run python tools/run_live.py --profile read   # reads only
```

## What it does

- Read smoke covers all 11 read operations (asserted in the final
  coverage test, not inferred).
- Write smoke creates only `PYSDK-PROBE-<stamp>-<nonce>`-prefixed
  objects in the sacrificial channel: message + thread reply (façade
  receipts with direct-read verification), edit, reaction add/remove,
  scheduled message create/fetch/cancel, custom status with a
  self-clearing 60 s expiry. Everything tracked is deleted and the
  delete is verified by direct read; the suite fails on nonzero
  residue.
- MCP live check: curated reads, preview→confirm send (verified, then
  deleted), `open_pumble_workspace`, and `pumble_ui_bootstrap` through
  the official in-process client against a real server.
- Webhook/subscription live checks run only when a signing secret and
  callback ingress exist; otherwise they are recorded as skipped.

Deliberately not exercised: `createChannel` / `addUsersToChannel` /
`removeUserFromChannel` — the API has no channel delete, so a created
channel would be permanent residue in ANY workspace.

## Receipt

`tools/run_live.py` stamps the pytest-written receipt with the commit
and the OpenAPI spec sha256. The receipt contains operation counts,
sha256-hashed created/deleted IDs, the cleanup residue (must be empty),
and the skipped checks — never message content, e-mails, raw live IDs,
or the key.

## Live findings (recorded)

- `dmUser`/`clearStatus` returned `api_error` on the sacrificial
  workspace (self-DM rejected; the expired-status clear trick
  rejected). Both are recorded as skips in the receipt, not failures.
- The live run caught a real façade bug: `dm_user_async`/`dm_group_async`
  take flat kwargs, not a `request={...}` wrapper (fixed in
  `extensions/writes.py` with unit regressions).
