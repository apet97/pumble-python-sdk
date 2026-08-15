"""Reusable, safe test helpers: sanitized fixtures, mock HTTP transport,
deterministic clocks, and generated-model factories.

Ported from ``extensions/testing/*``. Everything here is offline and
credential-free; nothing depends on a live workspace.
"""

from pumble_keys.testing.clocks import FakeClock
from pumble_keys.testing.factories import (
    make_channel,
    make_channel_list_entry,
    make_message,
    make_message_ref,
    make_user,
)
from pumble_keys.testing.fixtures import (
    create_fixture_body_hash,
    sanitize_pumble_fixture_value,
)
from pumble_keys.testing.mock_transport import (
    MockFixture,
    MockPumbleFetchMissError,
    create_mock_pumble_transport,
)

__all__ = [
    "FakeClock",
    "MockFixture",
    "MockPumbleFetchMissError",
    "create_fixture_body_hash",
    "create_mock_pumble_transport",
    "make_channel",
    "make_channel_list_entry",
    "make_message",
    "make_message_ref",
    "make_user",
    "sanitize_pumble_fixture_value",
]
