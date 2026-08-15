"""TokenStore protocol and the in-memory implementation.

Ported from ``extensions/app/token-store.ts``. No plaintext filesystem
persistence ships with this package — production deployments implement
the protocol over an encrypted store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class PumbleOAuthAccessTokenResponse:
    access_token: str
    user_id: str
    workspace_id: str
    bot_token: str | None = None
    bot_id: str | None = None


@runtime_checkable
class TokenStore(Protocol):
    async def initialize(self) -> None: ...

    async def get_bot_token(self, workspace_id: str) -> str | None: ...

    async def get_user_token(
        self, workspace_id: str, workspace_user_id: str
    ) -> str | None: ...

    async def get_bot_user_id(self, workspace_id: str) -> str | None: ...

    async def save_tokens(self, response: PumbleOAuthAccessTokenResponse) -> None: ...

    async def delete_for_workspace(self, workspace_id: str) -> None: ...

    async def delete_for_user(
        self, workspace_user_id: str, workspace_id: str
    ) -> None: ...


@dataclass
class _WorkspaceTokens:
    bot_token: str | None = None
    bot_user_id: str | None = None

    def __post_init__(self) -> None:
        self.user_tokens: dict[str, str] = {}


class InMemoryTokenStore:
    """Process-local token store; nothing touches disk."""

    def __init__(self) -> None:
        self._workspaces: dict[str, _WorkspaceTokens] = {}

    async def initialize(self) -> None:
        """No external resource to open; tokens remain process-local."""

    async def get_bot_token(self, workspace_id: str) -> str | None:
        workspace = self._workspaces.get(workspace_id)
        return workspace.bot_token if workspace else None

    async def get_user_token(
        self, workspace_id: str, workspace_user_id: str
    ) -> str | None:
        workspace = self._workspaces.get(workspace_id)
        return workspace.user_tokens.get(workspace_user_id) if workspace else None

    async def get_bot_user_id(self, workspace_id: str) -> str | None:
        workspace = self._workspaces.get(workspace_id)
        return workspace.bot_user_id if workspace else None

    async def save_tokens(self, response: PumbleOAuthAccessTokenResponse) -> None:
        workspace = self._workspaces.setdefault(
            response.workspace_id, _WorkspaceTokens()
        )
        workspace.user_tokens[response.user_id] = response.access_token
        if response.bot_token is not None:
            workspace.bot_token = response.bot_token
        if response.bot_id is not None:
            workspace.bot_user_id = response.bot_id

    async def delete_for_workspace(self, workspace_id: str) -> None:
        self._workspaces.pop(workspace_id, None)

    async def delete_for_user(self, workspace_user_id: str, workspace_id: str) -> None:
        workspace = self._workspaces.get(workspace_id)
        if workspace:
            workspace.user_tokens.pop(workspace_user_id, None)
