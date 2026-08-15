# Security policy

## Supported versions

Only the latest released version receives security fixes.

## API-key handling model

This SDK targets the Pumble API-Keys add-on. The workspace API key is
a bearer-equivalent secret. The project enforces these rules; report
any violation as a vulnerability:

- The key is read from the environment (or explicit constructor
  argument) only. It is never written to disk, logs, or telemetry.
- Debug and error output is redacted: the `ApiKey` header and other
  sensitive fields are masked before display
  (`pumble_keys.extensions.redaction`).
- The MCP server never echoes the key. The workspace fingerprint is a
  salted hash, not the key.
- Raw MCP writes are double-gated (`--allow-raw-writes` plus a
  mandatory `--audit-log` path). Audit-log records are redacted.
- CI runs a shape-based secret scanner over the whole tree
  (`tools/scan_secrets.py --all`); a finding fails the build.

## Operator obligations

- Issue keys from a dedicated workspace where possible. Live tests
  must only run against a sacrificial workspace
  ([docs/LIVE-TESTING.md](docs/LIVE-TESTING.md)).
- Rotate any key that was used for pre-release live verification
  before you use the workspace in production ("pre-launch credential
  rotation"). Rotate immediately on any suspected exposure: *Workspace
  settings → API keys* in the Pumble web app.
- Do not commit keys. `.env` files are gitignored; keep them that way.

## Reporting a vulnerability

Open a private security advisory on GitHub
(<https://github.com/apet97/pumble-python-sdk/security/advisories/new>)
or open an issue asking for a private contact channel — do not post
secrets or exploit details in a public issue. You get an initial
response within 7 days.
