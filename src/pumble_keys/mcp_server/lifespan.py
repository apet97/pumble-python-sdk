"""Server lifespan: owns the one async Pumble client and shared state.

One workspace per process. The lifespan owns the curated client (and
its resolver cache), the optional rate limiter, the confirmation
signer secret, the redacted audit sink, and the (P34) subscription
publisher seat. Everything closes exactly once on shutdown.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from pumble_keys.extensions.client import PumbleClient, create_pumble_client
from pumble_keys.extensions.rate_limit import RateLimiter
from pumble_keys.extensions.telemetry import JsonlAuditWriter
from pumble_keys.extensions.write_plan import ReplayGuard
from pumble_keys.mcp_server.config import McpConfig


@dataclass(frozen=True)
class ConfirmationSigner:
    """Holds the confirmation-signing secret (P28 consumes it).

    ``ephemeral`` is true when the secret was generated for this
    process (stdio); stateless HTTP deployments must configure
    ``PUMBLE_CONFIRMATION_SECRET`` so any instance can verify.
    """

    secret: bytes = field(repr=False)
    ephemeral: bool = False


@dataclass
class AppState:
    """Lifespan-owned state reachable from every handler via Context."""

    config: McpConfig
    client: PumbleClient
    rate_limiter: RateLimiter | None
    confirmation_signer: ConfirmationSigner
    audit_writer: JsonlAuditWriter | None
    workspace_fingerprint: str = ""
    replay_guard: ReplayGuard | None = None
    subscription_publisher: Any = None
    close_count: int = 0

    async def aclose(self) -> None:
        """Close owned resources exactly once; later calls are no-ops."""
        if self.close_count:
            self.close_count += 1
            return
        self.close_count = 1
        await self.client.aclose()


def build_state(
    config: McpConfig,
    *,
    client_factory: Callable[[McpConfig], PumbleClient] | None = None,
) -> AppState:
    if client_factory is not None:
        client = client_factory(config)
    else:
        client = create_pumble_client(
            config.api_key,
            server_url=config.base_url,
            timeout_ms=config.timeout_ms,
            resolver_cache={"enabled": True, "ttl_s": config.resolver_cache_ttl_s},
        )

    rate_limiter = None
    if config.rate_limit_rps is not None:
        rate_limiter = RateLimiter(
            rps=config.rate_limit_rps,
            burst=config.rate_limit_burst or max(1.0, config.rate_limit_rps),
        )

    if config.confirmation_secret:
        signer = ConfirmationSigner(
            secret=config.confirmation_secret.encode("utf-8"), ephemeral=False
        )
    else:
        signer = ConfirmationSigner(secret=secrets.token_bytes(32), ephemeral=True)

    audit_writer = (
        JsonlAuditWriter(config.audit_log_path) if config.audit_log_path else None
    )

    # Keyed per-process-independent fingerprint of the credential: binds
    # confirmations to one workspace without ever exposing the key.
    fingerprint = hashlib.sha256(
        b"pumble-workspace-fingerprint:" + config.api_key.encode("utf-8")
    ).hexdigest()[:16]

    replay_guard = (
        ReplayGuard(config.confirmation_replay_size)
        if config.confirmation_replay_size
        else None
    )

    return AppState(
        config=config,
        client=client,
        rate_limiter=rate_limiter,
        confirmation_signer=signer,
        audit_writer=audit_writer,
        workspace_fingerprint=fingerprint,
        replay_guard=replay_guard,
    )


def make_lifespan(
    config: McpConfig,
    *,
    client_factory: Callable[[McpConfig], PumbleClient] | None = None,
) -> Callable[[Any], Any]:
    """Build the ``MCPServer`` lifespan callable yielding ``AppState``."""

    @asynccontextmanager
    async def lifespan(_server: Any) -> AsyncIterator[AppState]:
        state = build_state(config, client_factory=client_factory)
        try:
            yield state
        finally:
            await state.aclose()

    return lifespan
