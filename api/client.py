"""HTTP client wrapper for QIWI Wallet Personal API."""

from __future__ import annotations

import json
from typing import Any

import requests

from api.config import P2P_PROVIDER_ID, Settings
from api.exceptions import QiwiApiError
from api.models import ApiResponse, PaymentRequest


class QiwiWalletClient:
    """Thin requests-based client aligned with QIWI Personal API documentation."""

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.session.headers.update(settings.auth_headers)

    def _url(self, path: str) -> str:
        return f"{self.settings.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        use_auth: bool = True,
    ) -> ApiResponse:
        request_headers = dict(self.session.headers)
        if not use_auth:
            request_headers.pop("Authorization", None)
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.request(
                method=method,
                url=self._url(path),
                params=params,
                json=json_body,
                headers=request_headers,
                timeout=self.settings.request_timeout,
            )
        except requests.RequestException as exc:
            raise QiwiApiError(f"Transport error: {exc}") from exc

        raw_text = response.text
        try:
            body: Any = response.json() if raw_text else None
        except json.JSONDecodeError:
            body = raw_text

        return ApiResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            raw_text=raw_text,
        )

    def _clone(self) -> QiwiWalletClient:
        """Return an isolated client copy that preserves custom request bindings."""
        clone = QiwiWalletClient(self.settings)
        if type(self).request is not QiwiWalletClient.request:
            clone.request = self.request  # type: ignore[method-assign]
        return clone

    def with_invalid_token(self) -> QiwiWalletClient:
        """Return a client that sends an invalid Bearer token."""
        client = self._clone()
        client.session.headers["Authorization"] = "Bearer invalid-token-xyz"
        return client

    def without_auth(self) -> QiwiWalletClient:
        """Return a client that omits the Authorization header."""
        client = self._clone()
        client.session.headers.pop("Authorization", None)
        return client

    def get_payments(self, rows: int = 10, *, wallet: str | None = None, **params: Any) -> ApiResponse:
        """GET /payment-history/v2/persons/{wallet}/payments — service health probe."""
        wallet_id = wallet or self.settings.wallet
        query = {"rows": rows, **params}
        return self.request(
            "GET",
            f"/payment-history/v2/persons/{wallet_id}/payments",
            params=query,
        )

    def get_balance_accounts(self, *, wallet: str | None = None, **params: Any) -> ApiResponse:
        """GET /funding-sources/v2/persons/{wallet}/accounts."""
        wallet_id = wallet or self.settings.wallet
        return self.request(
            "GET",
            f"/funding-sources/v2/persons/{wallet_id}/accounts",
            params=params,
        )

    def create_p2p_payment(
        self,
        payment: PaymentRequest | dict[str, Any],
        provider_id: str = P2P_PROVIDER_ID,
    ) -> ApiResponse:
        """POST /sinap/api/v2/terms/{providerId}/payments — create P2P transfer."""
        payload = payment.to_dict() if isinstance(payment, PaymentRequest) else payment
        headers = {"User-Agent": "Android v3.2.0 MKT"}
        original_headers = dict(self.session.headers)
        self.session.headers.update(headers)
        try:
            return self.request(
                "POST",
                f"/sinap/api/v2/terms/{provider_id}/payments",
                json_body=payload,
            )
        finally:
            self.session.headers.clear()
            self.session.headers.update(original_headers)

    def get_transaction(
        self,
        transaction_id: str,
        transaction_type: str | None = None,
        *,
        use_auth: bool = True,
    ) -> ApiResponse:
        """GET /payment-history/v2/transactions/{transactionId}."""
        params = {"type": transaction_type} if transaction_type else None
        return self.request(
            "GET",
            f"/payment-history/v2/transactions/{transaction_id}",
            params=params,
            use_auth=use_auth,
        )

    def get_profile(self) -> ApiResponse:
        """GET /person-profile/v1/profile/current — lightweight auth probe."""
        return self.request(
            "GET",
            "/person-profile/v1/profile/current",
            params={"authInfoEnabled": "false", "contractInfoEnabled": "true"},
        )
