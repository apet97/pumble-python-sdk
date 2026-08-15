"""P08: error categorization — six categories, exact classification order."""

from __future__ import annotations

import json

import httpx
import pytest

from pumble_keys.extensions.errors import categorize_error
from pumble_keys.models.errors import (
    Error,
    LegacyErrorData,
    PumbleSDKError,
    StructuredErrorData,
)


def _response(status: int, body: object = None) -> httpx.Response:
    request = httpx.Request("GET", "https://sanitized.example.invalid")
    if body is None:
        return httpx.Response(status, text="", request=request)
    return httpx.Response(status, json=body, request=request)


def _typed_error(status: int, data) -> Error:
    return Error(
        data, _response(status, json.loads(data.model_dump_json(by_alias=True)))
    )


def _sdk_error(status: int, body: object = None) -> PumbleSDKError:
    return PumbleSDKError("API error occurred", _response(status, body))


def test_structured_403_is_validation() -> None:
    error = _typed_error(
        403,
        StructuredErrorData(
            message="channelId must not be blank",
            localizedMessage="channelId must not be blank",
            code=400,
        ),
    )
    out = categorize_error(error)
    assert out.category == "validation"
    assert out.retryable is False
    assert out.status_code == 403
    assert out.message == "channelId must not be blank"
    assert out.localized_message == "channelId must not be blank"
    assert out.code == 400


def test_legacy_403_is_permission() -> None:
    error = _typed_error(403, LegacyErrorData(error="invalid api key"))
    out = categorize_error(error)
    assert out.category == "permission"
    assert out.retryable is False
    assert out.message == "invalid api key"
    assert out.localized_message is None


def test_401_is_permission() -> None:
    out = categorize_error(_sdk_error(401, {"error": "no key"}))
    assert out.category == "permission"
    assert out.retryable is False


def test_404_is_not_found() -> None:
    out = categorize_error(_sdk_error(404, {"error": "missing"}))
    assert out.category == "not-found"
    assert out.retryable is False
    assert out.message == "missing"


def test_429_is_retryable_rate_limit() -> None:
    out = categorize_error(_sdk_error(429))
    assert out.category == "rate-limit"
    assert out.retryable is True


@pytest.mark.parametrize("status", [408, 425, 500, 502, 503, 504])
def test_transient_statuses(status: int) -> None:
    out = categorize_error(_sdk_error(status))
    assert out.category == "transient"
    assert out.retryable is True
    assert out.status_code == status


def test_structured_body_400_via_sdk_error_is_validation() -> None:
    out = categorize_error(
        _sdk_error(
            400,
            {"message": "bad", "localizedMessage": "bad", "code": 400},
        )
    )
    assert out.category == "validation"
    assert out.retryable is False
    assert out.localized_message == "bad"


def test_plain_400_is_unknown() -> None:
    out = categorize_error(_sdk_error(400, {"error": "free-form"}))
    assert out.category == "unknown"
    assert out.retryable is False
    assert out.message == "free-form"


def test_validation_style_fields_count_as_structured() -> None:
    out = categorize_error(_sdk_error(422, {"message": "bad", "errors": ["fieldA"]}))
    assert out.category == "validation"


def test_connection_errors_are_transient() -> None:
    for error in (
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        ConnectionResetError("reset"),
        TimeoutError("timed out"),
    ):
        out = categorize_error(error)
        assert out.category == "transient", error
        assert out.retryable is True
        assert out.status_code is None


def test_empty_and_malformed_bodies_do_not_crash() -> None:
    assert categorize_error(_sdk_error(418)).category == "unknown"
    error = PumbleSDKError(
        "API error occurred",
        httpx.Response(
            418,
            text="<html>not json</html>",
            request=httpx.Request("GET", "https://sanitized.example.invalid"),
        ),
    )
    assert categorize_error(error).category == "unknown"


def test_arbitrary_exception_is_unknown_with_message() -> None:
    out = categorize_error(RuntimeError("surprise"))
    assert out.category == "unknown"
    assert out.retryable is False
    assert out.status_code is None
    assert out.message == "surprise"


def test_none_is_unknown() -> None:
    out = categorize_error(None)
    assert out.category == "unknown"
    assert out.message == "Unknown error"


def test_raw_is_excluded_from_serialization() -> None:
    error = _sdk_error(404, {"error": "missing"})
    out = categorize_error(error)
    assert out.raw is error
    dumped = out.model_dump(mode="json")
    assert "raw" not in dumped
    assert "raw" not in repr(out)
