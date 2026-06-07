"""Balance verification scenarios."""

from __future__ import annotations

import pytest

from api.client import QiwiWalletClient
from api.exceptions import QiwiSchemaError
from helpers.assertions import assert_balance_positive, assert_status_code
from helpers.schema_validator import SchemaValidator


@pytest.mark.smoke
class TestBalance:
    """
    Balance strategy:
    - GET /funding-sources/v2/persons/{wallet}/accounts
    - Validate accounts[] schema
    - Key business assertion: qw_wallet_rub balance.amount > 0
    """

    def test_balance_schema_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
        settings,
    ) -> None:
        schema_validator.validate_request(
            {"wallet": settings.wallet or "79991234567"},
            "balance_accounts_request.json",
        )

        response = mock_qiwi_client.get_balance_accounts()

        assert_status_code(response, 200)
        schema_validator.validate_response(response.body, "balance_accounts.json")
        assert_balance_positive(response.body)

    @pytest.mark.integration
    @pytest.mark.regression
    def test_rub_balance_is_positive(
        self,
        qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
        settings,
    ) -> None:
        schema_validator.validate_request({"wallet": settings.wallet}, "balance_accounts_request.json")

        response = qiwi_client.get_balance_accounts()

        assert_status_code(response, 200)
        assert isinstance(response.body, dict)

        schema_validator.validate_response(response.body, "balance_accounts.json")
        rub_balance = assert_balance_positive(response.body)

        assert rub_balance > 0


@pytest.mark.regression
class TestBalanceNegative:
    """Negative scenarios for GET /funding-sources/v2/persons/{wallet}/accounts."""

    def test_invalid_wallet_format_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        invalid_wallet = "abc123"
        with pytest.raises(QiwiSchemaError):
            schema_validator.validate_request({"wallet": invalid_wallet}, "balance_accounts_request.json")

        response = mock_qiwi_client.get_balance_accounts(wallet=invalid_wallet)

        assert_status_code(response, 400)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_invalid_wallet_format_live(self, qiwi_client: QiwiWalletClient) -> None:
        response = qiwi_client.get_balance_accounts(wallet="bad-wallet")

        assert response.status_code in {400, 404, 422}, (
            f"Expected client error for invalid wallet, got HTTP {response.status_code}"
        )

    def test_missing_authorization_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        client = mock_qiwi_client.without_auth()
        response = client.get_balance_accounts()

        assert_status_code(response, 401)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_invalid_token_live(self, qiwi_client: QiwiWalletClient, schema_validator: SchemaValidator) -> None:
        client = qiwi_client.with_invalid_token()
        response = client.get_balance_accounts()

        assert response.status_code in {401, 403}, (
            f"Expected auth failure, got HTTP {response.status_code}"
        )
        if isinstance(response.body, dict):
            schema_validator.validate_response(response.body, "error_response.json")
