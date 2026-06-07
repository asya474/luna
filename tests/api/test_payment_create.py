"""Payment creation scenarios — P2P transfer for 1 RUB (provider 99)."""

from __future__ import annotations

import pytest

from api.client import QiwiWalletClient
from api.config import P2P_PROVIDER_ID, RUB_CURRENCY_CODE
from api.exceptions import QiwiSchemaError
from api.models import PaymentRequest
from helpers.assertions import assert_payment_accepted, assert_status_code
from helpers.schema_validator import SchemaValidator


@pytest.mark.smoke
@pytest.mark.e2e
class TestPaymentCreate:
    """
    Creation strategy:
    - POST /sinap/api/v2/terms/99/payments
    - Amount: 1 RUB (currency 643)
    - Validate PaymentInfo schema and transaction.state.code == Accepted
    """

    def test_create_payment_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        payment_request: PaymentRequest,
        schema_validator: SchemaValidator,
    ) -> None:
        payload = payment_request.to_dict()
        schema_validator.validate_request(payload, "payment_request.json")

        response = mock_qiwi_client.create_p2p_payment(payment_request, provider_id=P2P_PROVIDER_ID)

        assert_status_code(response, 200)
        assert isinstance(response.body, dict)

        schema_validator.validate_response(response.body, "payment_info.json")
        transaction_id = assert_payment_accepted(response.body)

        assert response.body["sum"]["amount"] == 1
        assert response.body["terms"] == P2P_PROVIDER_ID
        assert transaction_id

    @pytest.mark.integration
    @pytest.mark.regression
    def test_create_payment_live(
        self,
        qiwi_client: QiwiWalletClient,
        payment_request: PaymentRequest,
        schema_validator: SchemaValidator,
    ) -> None:
        payload = payment_request.to_dict()
        schema_validator.validate_request(payload, "payment_request.json")

        response = qiwi_client.create_p2p_payment(payment_request)

        if response.status_code in {401, 403}:
            pytest.skip(f"Payment creation blocked by auth: HTTP {response.status_code}")

        if not response.ok:
            pytest.skip(f"Live payment creation not available: HTTP {response.status_code} {response.body}")

        assert isinstance(response.body, dict)
        schema_validator.validate_response(response.body, "payment_info.json")
        assert_payment_accepted(response.body)


@pytest.mark.regression
class TestPaymentCreateExtended:
    """Extended request payload validation for payment creation."""

    def test_create_payment_request_payload(
        self,
        payment_request: PaymentRequest,
        schema_validator: SchemaValidator,
    ) -> None:
        payload = payment_request.to_dict()

        schema_validator.validate_request(payload, "payment_request.json")
        assert payload["sum"]["amount"] == 1.0
        assert payload["sum"]["currency"] == RUB_CURRENCY_CODE
        assert payload["paymentMethod"]["type"] == "Account"
        assert payload["paymentMethod"]["accountId"] == RUB_CURRENCY_CODE
        assert payload["fields"]["account"]
        assert len(str(payload["id"])) <= 20


@pytest.mark.regression
class TestPaymentCreateNegative:
    """Negative scenarios for POST /sinap/api/v2/terms/99/payments."""

    def test_missing_required_fields_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        schema_validator: SchemaValidator,
    ) -> None:
        incomplete_payload = {"id": "1234567890", "sum": {"amount": 1.0, "currency": "643"}}

        with pytest.raises(QiwiSchemaError):
            schema_validator.validate_request(incomplete_payload, "payment_request.json")

        response = mock_qiwi_client.create_p2p_payment(incomplete_payload)

        assert_status_code(response, 400)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_missing_required_fields_live(self, qiwi_client: QiwiWalletClient) -> None:
        incomplete_payload = {"id": "1234567890"}
        response = qiwi_client.create_p2p_payment(incomplete_payload)

        assert response.status_code in {400, 422}, (
            f"Expected validation error, got HTTP {response.status_code}"
        )

    def test_wrong_amount_type_mock(
        self,
        mock_qiwi_client: QiwiWalletClient,
        payment_request: PaymentRequest,
        schema_validator: SchemaValidator,
    ) -> None:
        payload = payment_request.to_dict()
        payload["sum"]["amount"] = "one ruble"

        with pytest.raises(QiwiSchemaError):
            schema_validator.validate_request(payload, "payment_request.json")

        response = mock_qiwi_client.create_p2p_payment(payload)

        assert_status_code(response, 400)
        schema_validator.validate_response(response.body, "error_response.json")

    @pytest.mark.integration
    def test_missing_authorization_live(self, qiwi_client: QiwiWalletClient, payment_request: PaymentRequest) -> None:
        client = qiwi_client.without_auth()
        response = client.create_p2p_payment(payment_request)

        assert response.status_code in {401, 403}, (
            f"Expected auth failure, got HTTP {response.status_code}"
        )
