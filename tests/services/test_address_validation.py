"""Test the validate address method of the ShipEngine SDK."""
import re

from shipengine_sdk.errors import ClientSystemError, ValidationError
from shipengine_sdk.models import (
    Address,
    AddressValidateResult,
    ErrorCode,
    ErrorSource,
    ErrorType,
)

from ..util.test_helpers import (
    address_missing_required_fields,
    address_with_all_fields,
    address_with_errors,
    address_with_invalid_country,
    address_with_warnings,
    canada_valid_avs_assertions,
    get_server_side_error,
    multi_line_address,
    non_latin_address,
    unknown_address,
    valid_address_assertions,
    valid_canadian_address,
    valid_commercial_address,
    valid_residential_address,
    validate_an_address,
)


class TestValidateAddress:
    TEST_METHOD: str = "validate"

    def test_valid_residential_address(self) -> None:
        """DX-1024 - Valid residential address."""
        residential_address = valid_residential_address()
        validated_address = validate_an_address(residential_address)
        address = validated_address.normalized_address

        valid_address_assertions(
            test_method=self.TEST_METHOD,
            locale="domestic",
            original_address=residential_address,
            returned_address=validated_address,
            expected_residential_indicator=True,
        )
        assert (
            address.street[0]
            == (residential_address.street[0] + " " + residential_address.street[1])
            .replace(".", "")
            .upper()
        )

    def test_valid_commercial_address(self) -> None:
        """DX-1025 - Valid commercial address."""
        commercial_address = valid_commercial_address()
        validated_address = validate_an_address(commercial_address)
        address = validated_address.normalized_address

        valid_address_assertions(
            test_method=self.TEST_METHOD,
            locale="domestic",
            original_address=commercial_address,
            returned_address=validated_address,
            expected_residential_indicator=False,
        )
        assert (
            address.street[0]
            == (commercial_address.street[0] + " " + commercial_address.street[1])
            .replace(".", "")
            .upper()
        )

    def test_multi_line_address(self) -> None:
        """DX-1027 - Validate multiline address."""
        valid_multi_line_address = multi_line_address()
        validated_address = validate_an_address(valid_multi_line_address)
        address = validated_address.normalized_address

        valid_address_assertions(
            test_method=self.TEST_METHOD,
            locale="domestic",
            original_address=valid_multi_line_address,
            returned_address=validated_address,
            expected_residential_indicator=False,
        )
        assert (
            address.street[0]
            == (valid_multi_line_address.street[0] + " " + valid_multi_line_address.street[1])
            .replace(".", "")
            .upper()
        )
        assert address.street[1] == valid_multi_line_address.street[2].upper()

    def test_numeric_postal_code(self) -> None:
        """DX-1028 - Validate numeric postal code."""
        residential_address = valid_residential_address()
        validated_address = validate_an_address(residential_address)
        valid_address_assertions(
            test_method=self.TEST_METHOD,
            locale="domestic",
            original_address=residential_address,
            returned_address=validated_address,
            expected_residential_indicator=True,
        )
        assert re.match(r"\d", validated_address.normalized_address.postal_code)

    def test_alpha_postal_code(self) -> None:
        """DX-1029 - Alpha postal code."""
        canadian_address = valid_canadian_address()
        validated_address = validate_an_address(canadian_address)
        valid_address_assertions(
            test_method=self.TEST_METHOD,
            locale="international",
            original_address=canadian_address,
            returned_address=validated_address,
            expected_residential_indicator=False,
        )

    def test_unknown_address(self) -> None:
        """DX-1026 - Validate address of unknown address."""
        address = unknown_address()
        validated_address = validate_an_address(address)
        canada_valid_avs_assertions(
            original_address=address,
            validated_address=validated_address,
            expected_residential_indicator=None,
        )

    def test_address_with_non_latin_chars(self) -> None:
        """DX-1030 - non-latin characters."""
        non_latin = non_latin_address()
        validated_address = validate_an_address(non_latin)
        address = validated_address.normalized_address

        assert validated_address.is_valid is True
        assert address is not None
        assert type(address) is Address
        assert address.street[0] == "68 Kamitobatsunodacho"
        assert address.city_locality == "Kyoto-Shi Minami-Ku"
        assert address.state_province == "Kyoto"
        assert address.postal_code == non_latin.postal_code
        assert address.country_code == non_latin.country_code
        assert address.is_residential is False
        assert len(address.street) == 1

    def test_address_with_warnings(self) -> None:
        """DX-1031 - validate with warnings."""
        warnings_address = address_with_warnings()
        validated_address = validate_an_address(warnings_address)
        address = validated_address.normalized_address

        assert type(validated_address) is AddressValidateResult
        assert validated_address.is_valid is True
        assert type(address) is Address
        assert len(validated_address.info) == 0
        assert len(validated_address.warnings) != 0
        assert (
            validated_address.warnings[0]["code"]
            == ErrorCode.PARTIALLY_VERIFIED_TO_PREMISE_LEVEL.value
        )
        assert (
            validated_address.warnings[0]["message"]
            == "This address has been verified down to the house/building level (highest possible accuracy with the provided data)"  # noqa
        )
        assert len(validated_address.errors) == 0
        assert address.city_locality == warnings_address.city_locality
        assert address.state_province == warnings_address.state_province.title()
        assert address.postal_code == "M6K 3C3"
        assert address.country_code == warnings_address.country_code.upper()
        assert address.is_residential is True

    def test_address_with_errors(self) -> None:
        """DX-1032 - Validate with error messages."""
        error_address = address_with_errors()
        validated_address = validate_an_address(error_address)
        address = validated_address.normalized_address

        assert type(validated_address) is AddressValidateResult
        assert validated_address.is_valid is False
        assert address is None
        assert len(validated_address.info) == 0
        assert len(validated_address.warnings) != 0
        assert validated_address.warnings[0]["message"] == "Address not found"
        assert len(validated_address.errors) != 0
        assert validated_address.errors[0]["code"] == ErrorCode.ADDRESS_NOT_FOUND.value
        assert validated_address.errors[0]["message"] == "Invalid City, State, or Zip"
        assert validated_address.errors[1]["code"] == ErrorCode.ADDRESS_NOT_FOUND.value
        assert validated_address.errors[1]["message"] == "Insufficient or Incorrect Address Data"

    def test_missing_city_state_and_postal_code(self) -> None:
        """DX-1035 & DX-1036 - Missing city, state, and postal code."""
        try:
            address_missing_required_fields()
        except ValidationError as err:
            assert err.request_id is None
            assert err.source is ErrorSource.SHIPENGINE.value
            assert err.error_type is ErrorType.VALIDATION.value
            assert err.error_code is ErrorCode.FIELD_VALUE_REQUIRED.value
            assert (
                err.message
                == "Invalid address. Either the postal code or the city/locality and state/province must be specified."  # noqa
            )

    def test_invalid_country_code(self) -> None:
        """DX-1037 - Invalid country code."""
        try:
            address_with_invalid_country()
        except ValidationError as err:
            assert err.request_id is None
            assert err.source is ErrorSource.SHIPENGINE.value
            assert err.error_type is ErrorType.VALIDATION.value
            assert err.error_code is ErrorCode.FIELD_VALUE_REQUIRED.value
            assert err.message == "Invalid address: [RZ] is not a valid country code."

    def test_server_side_error(self) -> None:
        """DX-1038 - Server-side error."""
        try:
            get_server_side_error()
        except ClientSystemError as err:
            assert err.request_id is not None
            assert err.request_id.startswith("req_") is True
            assert err.source is ErrorSource.SHIPENGINE.value
            assert err.error_type is ErrorType.SYSTEM.value
            assert err.error_code is ErrorCode.UNSPECIFIED.value

    def test_address_with_name_company_phone(self) -> None:
        """DX-1393 - Validate address with name, company, and phone."""
        address = address_with_all_fields()
        validated_address = validate_an_address(address=address)

        valid_address_assertions(
            test_method=self.TEST_METHOD,
            locale="domestic",
            original_address=address,
            returned_address=validated_address,
            expected_residential_indicator=True,
        )
