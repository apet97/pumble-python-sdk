# MCP write safety

The model can never cause a Pumble write in one step on the curated
profile, and no layer of this server retries a write.

## Preview → confirm

1. `send_message_preview` / `reply_to_thread_preview` performs **no
   write**. It resolves the target and returns a signed plan: resolved
   target id+name, a redacted 160-character excerpt, the full-text
   sha256, a risk level, an expiry, the workspace fingerprint, and the
   request hash — plus an HMAC token over the canonical JSON of all of
   it.
2. `send_message_confirmed` / `reply_to_thread_confirmed` re-derives
   everything from the UNCHANGED request and verifies: signature,
   expiry, workspace fingerprint, request hash, text hash, and a
   bounded replay guard (a token is consumed on success). Any edit,
   tamper, expiry, or replay is rejected with a structured value and
   nothing is sent.
3. The confirmed write runs exactly once — **never retried** — and the
   receipt embeds the direct read-by-ID verification
   (`verification_state: verified`, or an honest
   `verification_failed`).

Stateless HTTP deployments must set `PUMBLE_CONFIRMATION_SECRET` so any
instance can verify any instance's token; stdio generates an ephemeral
per-process secret.

## MRTR interactive tools (`curated-interactive`)

`send_message_interactive` / `reply_to_thread_interactive` carry the
confirmation inside the tool call: the server elicits one deterministic
question (target label, redacted excerpt, hash prefix, risk — no
random IDs or timestamps, so retry rounds render identically). Accept
sends exactly once through the same façade write path; decline or
cancel sends nothing. Hosts without elicitation support get the SDK's
clear missing-capability error and no write occurs.

## Raw writes (`readwrite`)

Double-gated (`--allow-raw-writes` AND `--audit-log`), destructive
operations flagged, every attempt audited to a redacted JSONL sink,
`--dry-run` executes nothing. Raw writes are for operators, not
models; keep them off any host a model drives unattended.

## Cross-cutting rules

- One workspace per process; the workspace fingerprint binds every
  confirmation token to it.
- Failures are values, not protocol errors; error text never contains
  the API key, e-mails, or message content.
- The App's composer uses the same preview/confirm tools — there is
  exactly one write-safety implementation.
