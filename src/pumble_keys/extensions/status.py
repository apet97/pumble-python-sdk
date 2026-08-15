"""Custom-status helpers with read-proof and cache invalidation.

Exact OpenAPI payload semantics: ``customStatus`` requires ``code``
(``:emoji_name:`` form) and ``expiresAt`` (epoch ms; 0 = never
auto-clear; a past timestamp clears immediately). No emoji-code
normalization happens here — that is a CLI convenience (P24), never a
silent SDK transformation.

After a successful set/clear the façade calls ``myInfo`` exactly once
as the direct-read proof (§10.4) and invalidates the resolver cache's
user entries. The write is never retried.
"""

from __future__ import annotations

from typing import Any

from pumble_keys.extensions.results import (
    FacadeFailure,
    create_facade_invalid_request,
)
from pumble_keys.extensions.writes import WriteReceipt, _attempt, _verify


class StatusFacade:
    """Set and clear the authenticated user's custom status."""

    def __init__(self, *, raw: Any, resolver_cache: Any) -> None:
        self._raw = raw
        self._resolver_cache = resolver_cache

    async def set_status(
        self,
        *,
        code: str,
        expires_at: int,
        status: str | None = None,
        **rest: Any,
    ) -> WriteReceipt | FacadeFailure:
        """One ``customStatus`` write, then one ``myInfo`` read-proof."""
        if not code.strip():
            return create_facade_invalid_request(
                "users.set_status requires an emoji code.",
                "Pass a code in :emoji_name: form.",
            )
        if isinstance(expires_at, bool) or not isinstance(expires_at, int):
            return create_facade_invalid_request(
                "users.set_status requires expires_at as an "
                "epoch-millisecond integer (0 = never).",
                "Pass an integer epoch-millisecond timestamp.",
            )

        request: dict[str, Any] = {
            "code": code,
            "expires_at": expires_at,
            **rest,
        }
        if status is not None:
            request["status"] = status

        result = await _attempt(
            self._raw.users.custom_status_async(**request),
            "Pumble API rejected users.set_status.",
        )
        if isinstance(result, FacadeFailure):
            return result

        verification = await _verify(
            lambda: self._raw.users.my_info_async(),
            "the authenticated user",
        )
        if verification.state == "verified":
            self._resolver_cache.clear("users")

        return WriteReceipt(
            summary=f"Set custom status {code}.",
            ids={},
            verification=verification,
        )

    async def clear_status(self, **rest: Any) -> WriteReceipt | FacadeFailure:
        """Clear by writing an already-expired status (OpenAPI semantics)."""
        result = await _attempt(
            self._raw.users.custom_status_async(
                code=":speech_balloon:", expires_at=1, **rest
            ),
            "Pumble API rejected users.clear_status.",
        )
        if isinstance(result, FacadeFailure):
            return result

        verification = await _verify(
            lambda: self._raw.users.my_info_async(),
            "the authenticated user",
        )
        if verification.state == "verified":
            self._resolver_cache.clear("users")

        return WriteReceipt(
            summary="Cleared custom status.",
            ids={},
            verification=verification,
        )
