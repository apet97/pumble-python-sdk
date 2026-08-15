"""MCP server configuration.

The API key comes from the environment or a key file — never from an
MCP tool argument, never from App data. One Pumble workspace/API key
per process/deployment: the config carries exactly one credential and
every handler uses the one client the lifespan owns.
"""

from __future__ import annotations

import os
from typing import Any

import pydantic

from pumble_keys.mcp_server.profiles import Profile


class McpConfig(pydantic.BaseModel):
    """Frozen server configuration. ``api_key`` never serializes."""

    model_config = pydantic.ConfigDict(frozen=True)

    api_key: str = pydantic.Field(exclude=True, repr=False)
    base_url: str | None = None
    timeout_ms: int | None = None
    profile: Profile = Profile.CURATED

    # readwrite-profile gates (enforced again at registration in P31)
    allow_raw_writes: bool = False
    audit_log_path: str | None = None
    dry_run: bool = False

    # optional shared confirmation secret for stateless HTTP (P28);
    # stdio generates an ephemeral secret when absent.
    confirmation_secret: str | None = pydantic.Field(
        default=None, exclude=True, repr=False
    )

    # Bounded in-memory replay store for confirmation tokens (P28).
    # Multi-worker write-enabled deployments need a shared store or one
    # worker; this guard is per-process.
    confirmation_replay_size: int | None = 1024

    resolver_cache_ttl_s: float | None = 300.0
    rate_limit_rps: float | None = None
    rate_limit_burst: float | None = None

    @pydantic.field_validator("api_key")
    @classmethod
    def _nonblank_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("api_key must not be blank")
        return value

    @pydantic.model_validator(mode="after")
    def _validate_profile_gates(self) -> McpConfig:
        if self.profile is Profile.READWRITE:
            if not self.allow_raw_writes:
                raise ValueError(
                    "the readwrite profile requires allow_raw_writes=True "
                    "(an explicit gate, never a default)"
                )
            if not self.audit_log_path:
                raise ValueError("the readwrite profile requires an audit_log_path")
        elif self.dry_run:
            raise ValueError("dry_run is an option of the readwrite profile")
        return self

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, **overrides: Any) -> McpConfig:
        """Build from environment variables.

        ``PUMBLE_API_KEY_FILE`` beats ``PUMBLE_API_KEY``; the key is
        required. Other variables: ``PUMBLE_BASE_URL``,
        ``PUMBLE_MCP_PROFILE``, ``PUMBLE_MCP_ALLOW_RAW_WRITES``,
        ``PUMBLE_MCP_AUDIT_LOG``, ``PUMBLE_MCP_DRY_RUN``,
        ``PUMBLE_CONFIRMATION_SECRET``.
        """
        active = env if env is not None else dict(os.environ)

        api_key = overrides.pop("api_key", None)
        if api_key is None:
            key_file = active.get("PUMBLE_API_KEY_FILE")
            if key_file:
                with open(key_file, encoding="utf-8") as handle:
                    api_key = handle.read().strip()
            else:
                api_key = active.get("PUMBLE_API_KEY", "")

        values: dict[str, Any] = {
            "api_key": api_key,
            "base_url": active.get("PUMBLE_BASE_URL"),
            "confirmation_secret": active.get("PUMBLE_CONFIRMATION_SECRET"),
        }
        if "PUMBLE_MCP_PROFILE" in active:
            values["profile"] = Profile.parse(active["PUMBLE_MCP_PROFILE"])
        if "PUMBLE_MCP_ALLOW_RAW_WRITES" in active:
            values["allow_raw_writes"] = active["PUMBLE_MCP_ALLOW_RAW_WRITES"] == "1"
        if "PUMBLE_MCP_AUDIT_LOG" in active:
            values["audit_log_path"] = active["PUMBLE_MCP_AUDIT_LOG"]
        if "PUMBLE_MCP_DRY_RUN" in active:
            values["dry_run"] = active["PUMBLE_MCP_DRY_RUN"] == "1"
        values.update(overrides)
        return cls(**values)
