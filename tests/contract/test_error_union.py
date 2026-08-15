"""P06: error contract — both Pumble error body shapes parse without loss."""

from __future__ import annotations

import pydantic
import pytest


def _adapter():
    from pumble_keys.models.errors import ErrorUnion

    return pydantic.TypeAdapter(ErrorUnion)


def test_legacy_error_body_parses() -> None:
    from pumble_keys.models.errors import LegacyErrorData

    parsed = _adapter().validate_python({"error": "Channel not found"})
    assert isinstance(parsed, LegacyErrorData)
    assert parsed.error == "Channel not found"


def test_structured_error_body_parses() -> None:
    from pumble_keys.models.errors import StructuredErrorData

    parsed = _adapter().validate_python(
        {
            "message": "channelId must not be blank",
            "localizedMessage": "channelId must not be blank",
            "code": 400,
        }
    )
    assert isinstance(parsed, StructuredErrorData)
    assert parsed.message == "channelId must not be blank"
    assert parsed.localized_message == "channelId must not be blank"
    assert parsed.code == 400


def test_error_union_is_not_a_lossy_string() -> None:
    parsed = _adapter().validate_python(
        {"message": "m", "localizedMessage": "lm", "code": 403}
    )
    dumped = parsed.model_dump(mode="json", by_alias=True)
    assert dumped == {"message": "m", "localizedMessage": "lm", "code": 403}


def test_error_exception_carries_typed_data() -> None:
    import httpx

    from pumble_keys.models.errors import (
        Error,
        LegacyErrorData,
        PumbleSDKBaseError,
    )

    response = httpx.Response(
        403,
        json={"error": "forbidden"},
        request=httpx.Request("GET", "https://sanitized.example.invalid"),
    )
    error = Error(LegacyErrorData(error="forbidden"), response)
    assert isinstance(error, PumbleSDKBaseError)
    assert isinstance(error.data, LegacyErrorData)
    assert error.data.error == "forbidden"


def test_malformed_error_body_is_rejected_not_guessed() -> None:
    with pytest.raises(pydantic.ValidationError):
        _adapter().validate_python({"unexpected": "shape"})


def test_generated_operations_raise_error_union_on_4xx() -> None:
    """The generated surface maps documented 4xx bodies to the typed union."""
    import httpx
    import respx

    from pumble_keys import PumbleSDK
    from pumble_keys.models import errors

    with respx.mock(
        base_url="https://pumble-api-keys.addons.marketplace.cake.com"
    ) as router:
        router.get("/listChannels").mock(
            return_value=httpx.Response(403, json={"error": "invalid api key"})
        )
        with (
            PumbleSDK(api_key_auth="test-key-not-real") as sdk,
            pytest.raises(errors.Error) as excinfo,
        ):
            sdk.channels.list_channels()

    assert isinstance(excinfo.value.data, errors.LegacyErrorData)
    assert excinfo.value.data.error == "invalid api key"
