"""Assertion helper functions."""
import re
from typing import List

from shipengine_sdk.errors import (
    ClientSystemError,
    ClientTimeoutError,
    InvalidFieldValueError,
    RateLimitExceededError,
    ValidationError,
)
from shipengine_sdk.models import ErrorCode, ErrorSource, ErrorType
from shipengine_sdk.models.address import Address, AddressValidateResult
from shipengine_sdk.models.enums import Country

validation_message = "Invalid address. Either the postal code or the city/locality and state/province must be specified."  # noqa


def is_street_valid(street: List) -> None:
    """Checks that street is not empty and that it is not too many address lines."""
    if len(street) == 0:
        raise ValidationError(
            message="Invalid address. At least one address line is required.",
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )
    elif len(street) > 3:
        raise ValidationError(
            message="Invalid address. No more than 3 street lines are allowed.",
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.INVALID_FIELD_VALUE.value,
        )


def is_city_valid(city: str) -> None:
    """Asserts that city in not an empty string and contains valid characters."""
    latin_pattern = re.compile(r"^[a-zA-Z0-9\s\W]*$")
    non_latin_pattern = re.compile(r"[\u4e00-\u9fff]+")

    if non_latin_pattern.match(city):
        return
    elif not latin_pattern.match(city) or city == "":
        raise ValidationError(
            message=validation_message,
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )


def is_state_valid(state: str) -> None:
    """Asserts that state is 2 capitalized letters and that it is not an empty string."""
    latin_pattern = re.compile(r"^[a-zA-Z\W]*$")
    non_latin_pattern = re.compile(r"[\u4e00-\u9fff]+")

    if non_latin_pattern.match(state):
        return
    elif not latin_pattern.match(state) or state == "":
        raise ValidationError(
            message=validation_message,
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )


def is_postal_code_valid(postal_code: str) -> None:
    """Checks that the given postal code is alpha-numeric. A match would be '78756-123', '02215' or 'M6K 3C3'"""
    pattern = re.compile(r"^[a-zA-Z0-9\s-]*$")

    if not pattern.match(postal_code) or postal_code == "":
        raise ValidationError(
            message=validation_message,
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )


def is_country_code_valid(country: str) -> None:
    """Check if the given country code is valid."""
    if country not in (member.value for member in Country):
        raise ValidationError(
            message=f"Invalid address: [{country}] is not a valid country code.",
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )


def is_api_key_valid(config: dict) -> None:
    """
    Check if API Key is set and is not empty or whitespace.

    :param dict config: The config dictionary passed into `ShipEngineConfig`.
    :returns: None, only raises exceptions.
    :rtype: None
    """
    message = "A ShipEngine API key must be specified."
    if "api_key" not in config or config["api_key"] == "":
        raise ValidationError(
            message=message,
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )

    if re.match(r"\s", config["api_key"]):
        raise ValidationError(
            message=message,
            source=ErrorSource.SHIPENGINE.value,
            error_type=ErrorType.VALIDATION.value,
            error_code=ErrorCode.FIELD_VALUE_REQUIRED.value,
        )


def is_retries_valid(config: dict) -> None:
    """
    Checks that config.retries is a valid value.

    :param dict config: The config dictionary passed into `ShipEngineConfig`.
    :returns: None, only raises exceptions.
    :rtype: None
    """
    if "retries" in config and config["retries"] < 0:
        raise InvalidFieldValueError(
            field_name="retries",
            reason="Retries must be zero or greater.",
            field_value=config["retries"],
            source=ErrorSource.SHIPENGINE.value,
        )


def is_timeout_valid(config: dict) -> None:
    """
    Checks that config.timeout is valid value.

    :param dict config: The config dictionary passed into `ShipEngineConfig`.
    :returns: None, only raises exceptions.
    :rtype: None
    """
    if "timeout" in config and config["timeout"] < 0:
        raise InvalidFieldValueError(
            field_name="timeout",
            reason="Timeout must be zero or greater.",
            field_value=config["timeout"],
            source=ErrorSource.SHIPENGINE.value,
        )


def api_key_validation_error_assertions(error) -> None:
    """
    Helper test function that has common assertions pertaining to ValidationErrors.

    :param error: The error to execute assertions on.
    :returns: None, only executes assertions.
    :rtype: None
    """
    assert type(error) is ValidationError
    assert error.request_id is None
    assert error.error_type is ErrorType.VALIDATION.value
    assert error.error_code is ErrorCode.FIELD_VALUE_REQUIRED.value
    assert error.source is ErrorSource.SHIPENGINE.value
    assert error.message == "A ShipEngine API key must be specified."


def timeout_validation_error_assertions(error) -> None:
    """Helper test function that has common assertions pertaining to InvalidFieldValueError."""
    assert type(error) is InvalidFieldValueError
    assert error.request_id is None
    assert error.error_type is ErrorType.VALIDATION.value
    assert error.error_code is ErrorCode.INVALID_FIELD_VALUE.value
    assert error.source is ErrorSource.SHIPENGINE.value


def is_response_404(status_code: int, response_body: dict) -> None:
    """Check if status_code is 404 and raises an error if so."""
    if "error" in response_body:
        error = response_body["error"]
        error_data = error["data"]
        if status_code == 404:
            raise ClientSystemError(
                message=error["message"],
                request_id=response_body["id"],
                source=error_data["source"],
                error_type=error_data["type"],
                error_code=error_data["code"],
            )


def is_response_429(status_code: int, response_body: dict, config) -> None:
    """Check if status_code is 429 and raises an error if so."""
    if "error" in response_body and status_code == 429:
        error = response_body["error"]
        retry_after = error["data"]["retryAfter"]
        if retry_after > config.timeout:
            raise ClientTimeoutError(
                retry_after=config.timeout,
                source=ErrorSource.SHIPENGINE.value,
                request_id=response_body["id"],
            )
        else:
            raise RateLimitExceededError(
                retry_after=retry_after,
                source=ErrorSource.SHIPENGINE.value,
                request_id=response_body["id"],
            )


def is_response_500(status_code: int, response_body: dict) -> None:
    """Check if the status code is 500 and raises an error if so."""
    if status_code == 500:
        error = response_body["error"]
        error_data = error["data"]
        raise ClientSystemError(
            message=error["message"],
            request_id=response_body["id"],
            source=error_data["source"],
            error_type=error_data["type"],
            error_code=error_data["code"],
        )


def us_valid_address_assertions(
    original_address: Address,
    validated_address: AddressValidateResult,
    expected_residential_indicator,
) -> None:
    """A set of common assertions that are regularly made on the commercial US address used for testing."""
    address = validated_address.normalized_address
    assert type(validated_address) is AddressValidateResult
    assert validated_address.is_valid is True
    assert type(address) is Address
    assert len(validated_address.info) == 0
    assert len(validated_address.warnings) == 0
    assert len(validated_address.errors) == 0
    assert address is not None
    assert address.city_locality == original_address.city_locality.upper()
    assert address.state_province == original_address.state_province.upper()
    assert address.postal_code == original_address.postal_code
    assert address.country_code == original_address.country_code.upper()
    assert address.is_residential is expected_residential_indicator


def canada_valid_address_assertions(
    original_address: Address,
    validated_address: AddressValidateResult,
    expected_residential_indicator,
) -> None:
    """A set of common assertions that are regularly made on the canadian_address used for testing."""
    address = validated_address.normalized_address
    assert type(validated_address) is AddressValidateResult
    assert validated_address.is_valid is True
    assert type(address) is Address
    assert len(validated_address.info) == 0
    assert len(validated_address.warnings) == 0
    assert len(validated_address.errors) == 0
    assert address is not None
    assert address.city_locality == original_address.city_locality
    assert address.state_province == original_address.state_province.title()
    assert address.postal_code == "M6 K 3 C3"
    assert address.country_code == original_address.country_code.upper()
    assert address.is_residential is expected_residential_indicator
