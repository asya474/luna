"""Payment execution verification scenarios."""

from __future__ import annotations

import pytest

from api.client import QiwiWalletClient
from api.exceptions import QiwiSchemaError
from helpers.assertions import assert_payment_accepted, assert_status_code
from helpers.schema_validator import SchemaValidator


@pytest.mark.smoke
@pytest.mark.e2e
class TestPaymentExecute:
    """
    Execution strategy (per QIWI docs):
    - POST /sinap/api/v2/terms/99/payments accepts payment (state.code=Accepted)
    - Final status is verified via GET /payment-history/v2/transactions/{txnId}
    - SUCCESS or WAITING are acceptable post-acceptance states; ERROR fails the test
    """

    def test_payment_accepted_state_mock(self, created_payment: dict) -> None:
        transaction_id = assert_payment_accepted(created_payment)
        assert transaction_id == "11982501857"

    def test_transaction_status_after_payment_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        created_payment: dict,
        schema_validator: SchemaValidator,
    ) -> None:
        transaction_id = assert_payment_accepted(created_payment)
        request_params = {"transaction_id": transaction_id, "type": "OUT"}
        schema_validator.validate_request(request_params, "transaction_request.json")

        response = mock_qiwi_client.get_transaction(transaction_id, transaction_type="OUT")

        assert_status_code(response, 200)
        schema_validator.validate_response(response.body, "transaction.json")

        status = response.body["status"]
        assert status in {"SUCCESS", "WAITING"}, f"Unexpected transaction status: {status}"

    @pytest.mark.integration
    @pytest.mark.regression
    def test_transaction_status_after_payment_live(
        self,
        qiwi_client: QiwiWalletClient,
        created_payment: dict,
        schema_validator: SchemaValidator,
    ) -> None:
        transaction_id = assert_payment_accepted(created_payment)
        schema_validator.validate_request(
            {"transaction_id": transaction_id, "type": "OUT"},
            "transaction_request.json",
        )

        response = qiwi_client.get_transaction(transaction_id, transaction_type="OUT")

        if response.status_code == 404:
            pytest.skip("Transaction not yet visible in history — API may be unavailable")

        assert_status_code(response, 200)
        schema_validator.validate_response(response.body, "transaction.json")

        status = response.body["status"]
        assert status != "ERROR", f"Payment execution failed with status ERROR: {response.body}"
        assert status in {"SUCCESS", "WAITING"}


@pytest.mark.regression
class TestPaymentExecuteNegative:
    """Negative scenarios for GET /payment-history/v2/transactions/{id}."""

    def test_invalid_transaction_id_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        invalid_id = "not-a-txn-id"
        with pytest.raises(QiwiSchemaError):
            schema_validator.validate_request({"transaction_id": invalid_id}, "transaction_request.json")

        response = mock_qiwi_client.get_transaction(invalid_id, transaction_type="OUT")

        assert_status_code(response, 404)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_invalid_transaction_id_live(self, qiwi_client: QiwiWalletClient) -> None:
        response = qiwi_client.get_transaction("00000000000", transaction_type="OUT")

        assert response.status_code in {404, 400}, (
            f"Expected not-found for invalid transaction id, got HTTP {response.status_code}"
        )

    def test_missing_authorization_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        client = mock_qiwi_client.without_auth()
        response = client.get_transaction("11982501857", transaction_type="OUT", use_auth=False)

        assert_status_code(response, 401)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_invalid_token_live(self, qiwi_client: QiwiWalletClient, schema_validator: SchemaValidator) -> None:
        client = qiwi_client.with_invalid_token()
        response = client.get_transaction("11982501857", transaction_type="OUT")

        assert response.status_code in {401, 403}, (
            f"Expected auth failure, got HTTP {response.status_code}"
        )
        if isinstance(response.body, dict):
            schema_validator.validate_response(response.body, "error_response.json")
