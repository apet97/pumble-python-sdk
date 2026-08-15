"""P25: MCP factory — profiles, lifespan ownership, key handling."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pumble_keys.mcp_server.config import McpConfig
from pumble_keys.mcp_server.lifespan import build_state, make_lifespan
from pumble_keys.mcp_server.profiles import APP_ENABLED_PROFILES, Profile
from pumble_keys.mcp_server.server import (
    SERVER_NAME,
    create_server,
    registrars_for,
)

KEY = "test-key-not-real"


class FakeClient:
    def __init__(self) -> None:
        self.close_calls = 0

    async def aclose(self) -> None:
        self.close_calls += 1


def config(**overrides) -> McpConfig:
    return McpConfig(api_key=KEY, **overrides)


def client_factory(_config):
    return FakeClient()


class TestConfig:
    def test_blank_api_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="api_key must not be blank"):
            McpConfig(api_key="  ")

    def test_from_env_key_and_profile(self) -> None:
        built = McpConfig.from_env(
            {
                "PUMBLE_API_KEY": KEY,
                "PUMBLE_MCP_PROFILE": "readonly",
                "PUMBLE_BASE_URL": "https://x.example.invalid",
            }
        )
        assert built.api_key == KEY
        assert built.profile is Profile.READONLY
        assert built.base_url == "https://x.example.invalid"

    def test_from_env_key_file_beats_env_key(self, tmp_path) -> None:
        key_file = tmp_path / "key"
        key_file.write_text("file-key\n")
        built = McpConfig.from_env(
            {"PUMBLE_API_KEY": "env-key", "PUMBLE_API_KEY_FILE": str(key_file)}
        )
        assert built.api_key == "file-key"

    def test_missing_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="api_key"):
            McpConfig.from_env({})

    def test_unknown_profile_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown MCP profile"):
            McpConfig.from_env({"PUMBLE_API_KEY": KEY, "PUMBLE_MCP_PROFILE": "banana"})

    def test_readwrite_requires_both_gates(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="allow_raw_writes"):
            config(profile=Profile.READWRITE)
        with pytest.raises(ValueError, match="audit_log_path"):
            config(profile=Profile.READWRITE, allow_raw_writes=True)
        gated = config(
            profile=Profile.READWRITE,
            allow_raw_writes=True,
            audit_log_path=str(tmp_path / "audit.jsonl"),
        )
        assert gated.profile is Profile.READWRITE

    def test_dry_run_only_on_readwrite(self) -> None:
        with pytest.raises(ValueError, match="dry_run"):
            config(dry_run=True)

    def test_api_key_never_serializes_or_reprs(self) -> None:
        built = config(confirmation_secret="conf-secret-not-real")
        dumped = built.model_dump()
        assert "api_key" not in dumped
        assert "confirmation_secret" not in dumped
        assert KEY not in repr(built)
        assert "conf-secret-not-real" not in repr(built)

    def test_profiles_are_immutable_enum_values(self) -> None:
        assert [profile.value for profile in Profile] == [
            "curated",
            "curated-interactive",
            "readonly",
            "readwrite",
        ]
        assert APP_ENABLED_PROFILES == {
            Profile.CURATED,
            Profile.CURATED_INTERACTIVE,
        }


class TestFactory:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "profile",
        [Profile.CURATED, Profile.CURATED_INTERACTIVE, Profile.READONLY],
    )
    async def test_snapshot_per_profile_is_deterministic(self, profile) -> None:
        server = create_server(config(profile=profile), client_factory=client_factory)
        assert server.name == SERVER_NAME
        curated_tools = [
            "whoami",
            "find_channel",
            "find_user",
            "list_channels",
            "search_messages",
            "get_channel_context",
            "get_thread_context",
            "send_message_preview",
            "send_message_confirmed",
            "reply_to_thread_preview",
            "reply_to_thread_confirmed",
        ]
        expected_tools = {
            Profile.CURATED: curated_tools,
            Profile.CURATED_INTERACTIVE: curated_tools,
            Profile.READONLY: [],  # raw adapters arrive in P31
        }
        snapshot = {
            "tools": [tool.name for tool in await server.list_tools()],
            "resources": [
                str(resource.uri) for resource in await server.list_resources()
            ],
            "prompts": [prompt.name for prompt in await server.list_prompts()],
        }
        assert snapshot == {
            "tools": expected_tools[profile],
            "resources": ["pumble://me", "pumble://channels"],
            "prompts": [],
        }

        again = create_server(config(profile=profile), client_factory=client_factory)
        assert [t.name for t in await again.list_tools()] == snapshot["tools"]

    def test_registrar_composition_order(self) -> None:
        # curated-interactive extends curated; readwrite extends readonly.
        assert registrars_for(Profile.CURATED_INTERACTIVE)[
            : len(registrars_for(Profile.CURATED))
        ] == registrars_for(Profile.CURATED)
        assert registrars_for(Profile.READWRITE)[
            : len(registrars_for(Profile.READONLY))
        ] == registrars_for(Profile.READONLY)

    def test_server_kwargs_pass_through(self) -> None:
        server = create_server(
            config(),
            client_factory=client_factory,
            version="9.9.9",
        )
        assert server.version == "9.9.9"


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_owns_and_closes_client_exactly_once(self) -> None:
        lifespan = make_lifespan(config(), client_factory=client_factory)
        async with lifespan(SimpleNamespace()) as state:
            client = state.client
            assert isinstance(client, FakeClient)
            assert state.config.profile is Profile.CURATED
            assert state.confirmation_signer.ephemeral is True
        assert client.close_calls == 1

        # A second aclose is a no-op.
        await state.aclose()
        assert client.close_calls == 1

    @pytest.mark.asyncio
    async def test_lifespan_closes_even_on_error(self) -> None:
        lifespan = make_lifespan(config(), client_factory=client_factory)
        with pytest.raises(RuntimeError):
            async with lifespan(SimpleNamespace()) as state:
                raise RuntimeError("handler blew up")
        assert state.client.close_calls == 1

    def test_configured_confirmation_secret_is_not_ephemeral(self) -> None:
        state = build_state(
            config(confirmation_secret="shared-secret-not-real"),
            client_factory=client_factory,
        )
        assert state.confirmation_signer.ephemeral is False
        assert state.confirmation_signer.secret == b"shared-secret-not-real"
        assert "shared-secret-not-real" not in repr(state.confirmation_signer)

    def test_rate_limiter_and_audit_only_when_configured(self, tmp_path) -> None:
        bare = build_state(config(), client_factory=client_factory)
        assert bare.rate_limiter is None
        assert bare.audit_writer is None

        full = build_state(
            config(
                profile=Profile.READWRITE,
                allow_raw_writes=True,
                audit_log_path=str(tmp_path / "audit.jsonl"),
                rate_limit_rps=5.0,
            ),
            client_factory=client_factory,
        )
        assert full.rate_limiter is not None
        assert full.audit_writer is not None
