# Stability and support boundaries

Unofficial project; Pumble/CAKE.com do not endorse it. Version `0.1.x`:
pre-1.0, minor versions may break.

## Stability tiers

| Tier | Surface | Promise |
|---|---|---|
| Supported | `pumble_keys.extensions` façade, CLI commands, MCP curated/curated-interactive tool shapes, `PumbleApp`/webhook verification, OAuth helpers | Breaking changes only with a version bump and changelog entry |
| Generated | `pumble_keys.*` raw SDK | Follows the OpenAPI document and the pinned Speakeasy generator; regenerated wholesale |
| Experimental | Socket Mode (`docs/EXPERIMENTAL.md`), raw `readwrite` MCP profile | May change without notice |

## Deliberate design commitments

- **No write retries**, anywhere, ever. Retries are for
  proven-idempotent reads only.
- **Direct-read proof** on every write receipt; honesty over optimism
  (`verification_failed` is a real state).
- **Single-workspace deployment**: one API key, one process, one
  workspace; confirmation tokens are fingerprint-bound to it.
- **Preview/confirm** is the only model-reachable write path on the
  curated profile.
- **No SSE**: Streamable HTTP only, stateless by default.
- **App CSP closed**: the MCP App requests no iframe permissions and
  declares no external connect/resource domains.

## Deliberately deferred

- **MCP Tasks**: no homemade task/queue layer; adopt the SDK's Tasks
  support if/when the project needs it.
- **Client-credentials broker extension** for machine-to-machine MCP
  auth: deferred; the server verifies bearer tokens from any
  spec-compliant authorization server instead.
- Multi-replica subscription fan-out: needs a shared `SubscriptionBus`
  adapter (Redis/NATS); the in-process bus is single-process by design.
