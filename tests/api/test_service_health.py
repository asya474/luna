"""Service availability checks based on payment history endpoint."""

from __future__ import annotations

import pytest

from api.client import QiwiWalletClient
from api.exceptions import QiwiSchemaError
from helpers.assertions import assert_status_code
from helpers.schema_validator import SchemaValidator


@pytest.mark.smoke
class TestServiceHealth:
    """
    Health strategy:
    - Call GET /payment-history/v2/persons/{wallet}/payments?rows=10
    - Expect HTTP 200 and JSON matching PaymentHistoryList schema
    - Any schema drift or non-JSON/5xx response indicates unhealthy service
    """

    def test_payments_list_response_format_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
        settings,
    ) -> None:
        request_params = {"wallet": settings.wallet or "79991234567", "rows": 10}
        schema_validator.validate_request(request_params, "payments_list_request.json")

        response = mock_qiwi_client.get_payments(rows=10)

        assert_status_code(response, 200)
        schema_validator.validate_response(response.body, "payments_list.json")

    @pytest.mark.integration
    @pytest.mark.regression
    def test_payments_list_service_available(
        self,
        qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
        settings,
    ) -> None:
        request_params = {"wallet": settings.wallet, "rows": 10}
        schema_validator.validate_request(request_params, "payments_list_request.json")

        response = qiwi_client.get_payments(rows=10)

        assert_status_code(response, 200)
        assert isinstance(response.body, dict), "Payments endpoint must return JSON object"

        try:
            schema_validator.validate_response(response.body, "payments_list.json")
        except QiwiSchemaError as exc:
            pytest.fail(
                "Service may be unhealthy: payments response does not match documentation schema. "
                f"Errors: {exc.errors}"
            )

    @pytest.mark.integration
    @pytest.mark.regression
    def test_auth_token_accepted(self, qiwi_client: QiwiWalletClient) -> None:
        """Profile endpoint is a secondary probe for Bearer token validity."""
        response = qiwi_client.get_profile()

        assert response.status_code in {200, 403}, (
            f"Unexpected auth/profile response: {response.status_code}"
        )
        if response.status_code == 403:
            pytest.skip("Token rejected by API — credentials may be expired (docs note token issuance stopped)")


@pytest.mark.regression
class TestServiceHealthNegative:
    """Negative scenarios for GET /payment-history/v2/persons/{wallet}/payments."""

    def test_invalid_wallet_format_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        invalid_wallet = "not-a-wallet"
        with pytest.raises(QiwiSchemaError):
            schema_validator.validate_request(
                {"wallet": invalid_wallet, "rows": 10},
                "payments_list_request.json",
            )

        response = mock_qiwi_client.get_payments(rows=10, wallet=invalid_wallet)

        assert_status_code(response, 400)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_invalid_wallet_format_live(self, qiwi_client: QiwiWalletClient) -> None:
        response = qiwi_client.get_payments(rows=10, wallet="invalid")

        assert response.status_code in {400, 404, 422}, (
            f"Expected client error for invalid wallet, got HTTP {response.status_code}"
        )

    def test_missing_authorization_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        client = mock_qiwi_client.without_auth()
        response = client.get_payments(rows=10)

        assert_status_code(response, 401)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_invalid_token_live(self, qiwi_client: QiwiWalletClient, schema_validator: SchemaValidator) -> None:
        client = qiwi_client.with_invalid_token()
        response = client.get_payments(rows=10)

        assert response.status_code in {401, 403}, (
            f"Expected auth failure, got HTTP {response.status_code}"
        )
        if isinstance(response.body, dict):
            schema_validator.validate_response(response.body, "error_response.json")
