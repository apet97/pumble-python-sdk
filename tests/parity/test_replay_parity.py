"""P40: replay the sanitized corpus through the Python implementation.

Each fixture pins the TS contract source (pinned commit cc20de1) and
the expected NORMALIZED semantic output — canonical JSON, not
language-specific serialization. `PARITY_MATRIX.md` records coverage
and every intentional difference.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from pumble_keys.extensions.client import create_pumble_client
from pumble_keys.extensions.pagination import list_all_messages
from pumble_keys.extensions.write_plan import (
    canonical_json,
    excerpt_text,
    hash_request,
    hash_text,
)
from pumble_keys.mcp_server.tools.raw_manifest import (
    RAW_READ_OPERATIONS,
    RAW_WRITE_OPERATIONS,
)
from pumble_keys.mcp_server.tools.raw_read import call_raw_operation
from pumble_keys.pumble_app.events import (
    KNOWN_EVENT_TYPES,
    normalize_webhook_event,
)
from tests.parity.conftest import fixture_names, load

ALL_OPERATIONS = {
    op.operation_id: op for op in RAW_READ_OPERATIONS + RAW_WRITE_OPERATIONS
}


def normalized(value) -> str:
    return canonical_json(value)


class Recorder:
    def __init__(self, value) -> None:
        self.value = value
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.value


class TestOperations:
    def test_every_generated_operation_has_a_fixture(self) -> None:
        assert sorted(ALL_OPERATIONS) == fixture_names("operations")
        assert len(ALL_OPERATIONS) == 26

    @pytest.mark.asyncio
    @pytest.mark.parametrize("operation_id", sorted(ALL_OPERATIONS))
    async def test_operation_replay(self, operation_id: str) -> None:
        fixture = load("operations", operation_id)
        operation = ALL_OPERATIONS[operation_id]
        recorder = Recorder(fixture["raw"])
        state = SimpleNamespace(
            client=SimpleNamespace(
                raw=SimpleNamespace(
                    **{
                        operation.namespace: SimpleNamespace(
                            **{operation.method: recorder}
                        )
                    }
                )
            )
        )
        result = await call_raw_operation(state, operation, dict(fixture["arguments"]))
        assert normalized(result) == normalized(fixture["expected"])
        expected_call = fixture["expected_call"]
        assert operation.namespace == expected_call["namespace"]
        assert operation.method == expected_call["method"]
        assert normalized(recorder.calls[0]) == normalized(expected_call["kwargs"])


class TestWebhooks:
    def test_all_seven_event_types_have_fixtures(self) -> None:
        assert sorted(KNOWN_EVENT_TYPES) == fixture_names("webhooks")

    @pytest.mark.parametrize("kind", sorted(KNOWN_EVENT_TYPES))
    def test_webhook_replay(self, kind: str) -> None:
        fixture = load("webhooks", kind)
        event = normalize_webhook_event(fixture["payload"])
        assert event is not None
        produced = json.loads(event.model_dump_json(exclude={"raw"}))
        assert normalized(produced) == normalized(fixture["expected"])


class TestResolver:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", fixture_names("resolver"))
    async def test_resolver_replay(self, name: str) -> None:
        fixture = load("resolver", name)
        directory = fixture["directory"]
        raw = SimpleNamespace(
            channels=SimpleNamespace(
                list_channels_async=Recorder(
                    [
                        SimpleNamespace(channel=SimpleNamespace(**channel))
                        for channel in directory["channels"]
                    ]
                )
            ),
            users=SimpleNamespace(
                list_users_async=Recorder(
                    [SimpleNamespace(**user) for user in directory["users"]]
                )
            ),
        )
        client = create_pumble_client(raw=raw)
        target = client.channels if fixture["kind"] == "channels" else client.users
        found = await target.find(fixture["query"])
        produced = json.loads(found.model_dump_json(exclude={"cause"}))
        assert normalized(produced) == normalized(fixture["expected"])


class TestPagination:
    @pytest.mark.asyncio
    async def test_boundary_overlap_dedup_and_cursor_walk(self) -> None:
        fixture = load("pagination", "list_all_messages_overlap")
        served = [
            SimpleNamespace(
                result=SimpleNamespace(
                    messages=[
                        SimpleNamespace(**message) for message in page["messages"]
                    ],
                    has_more_before=page["has_more_before"],
                    has_more_after=False,
                )
            )
            for page in fixture["pages"]
        ]
        requests: list[dict] = []
        index = 0

        async def fetch(request: dict):
            nonlocal index
            requests.append(dict(request))
            page = served[index]
            index += 1
            return page

        ids = [
            message.id
            async for message in list_all_messages(fetch, dict(fixture["request"]))
        ]
        assert ids == fixture["expected"]["yielded_ids"]
        assert normalized(requests) == normalized(fixture["expected"]["requests"])


class TestCliGoldens:
    def test_formatting_cases(self) -> None:
        from pumble_keys.cli import formatting as fmt

        cases = load("cli", "formatting")["cases"]
        assert len(cases) >= 6
        for name, case in cases.items():
            fn = getattr(fmt, case["fn"])
            raw_input = case["input"]
            value = (
                SimpleNamespace(**raw_input)
                if isinstance(raw_input, dict)
                else raw_input
            )
            assert fn(value) == case["expected"], name


class TestMcpManifests:
    @pytest.mark.asyncio
    async def test_frozen_catalogs_per_profile(self) -> None:
        from pumble_keys.mcp_server.config import McpConfig
        from pumble_keys.mcp_server.profiles import Profile
        from pumble_keys.mcp_server.server import create_server

        class FakeClient:
            async def aclose(self) -> None:
                return None

        profiles = load("mcp", "manifests")["profiles"]
        assert sorted(profiles) == sorted(p.value for p in Profile)
        for profile in Profile:
            extra = {}
            if profile is Profile.READWRITE:
                extra = {
                    "allow_raw_writes": True,
                    "audit_log_path": "/tmp/x.jsonl",
                }
            server = create_server(
                McpConfig(api_key="fixture-key-not-real", profile=profile, **extra),
                client_factory=lambda _c: FakeClient(),
            )
            produced = {
                "tools": [t.name for t in await server.list_tools()],
                "resources": [str(r.uri) for r in await server.list_resources()],
                "templates": [
                    t.uri_template for t in await server.list_resource_templates()
                ],
                "prompts": [p.name for p in await server.list_prompts()],
            }
            assert produced == profiles[profile.value], profile.value


class TestWritePlanCanonicalization:
    def test_fixed_vectors(self) -> None:
        vectors = load("write_plan", "canonical")["vectors"]
        assert (
            canonical_json(vectors["canonical_json"]["input"])
            == (vectors["canonical_json"]["expected"])
        )
        assert (
            canonical_json(vectors["canonical_json_nested"]["input"])
            == (vectors["canonical_json_nested"]["expected"])
        )
        assert (
            hash_text(vectors["hash_text"]["input"])
            == (vectors["hash_text"]["expected"])
        )
        assert (
            hash_request(vectors["hash_request"]["input"])
            == (vectors["hash_request"]["expected"])
        )
        assert (
            excerpt_text(vectors["excerpt_long"]["input"])
            == (vectors["excerpt_long"]["expected"])
        )
        # The canonicalization drops None and sorts keys — the exact TS
        # write-plan.ts contract the HMAC binding depends on.
        assert '"extra"' not in vectors["canonical_json"]["expected"]
        assert vectors["canonical_json_nested"]["expected"].startswith('{"a"')
