"""Deterministic mock client for offline API tests."""

from __future__ import annotations

import json
import re
from typing import Any

from api.client import QiwiWalletClient
from api.config import Settings
from api.models import ApiResponse

WALLET_PATTERN = re.compile(r"^[0-9]{11}$")
TRANSACTION_ID_PATTERN = re.compile(r"^[0-9]+$")
DEFAULT_MOCK_WALLET = "79991234567"


def _error_body(mock_responses: dict[str, Any], key: str) -> dict[str, Any]:
    body = mock_responses.get(key, {})
    return body if isinstance(body, dict) else {}


def _is_invalid_token(headers: dict[str, str]) -> bool:
    return headers.get("Authorization") == "Bearer invalid-token-xyz"


class MockQiwiWalletClient(QiwiWalletClient):
    """QIWI client that simulates API responses without network calls."""

    def __init__(self, settings: Settings, mock_responses: dict[str, Any]) -> None:
        super().__init__(settings)
        self._mock_responses = mock_responses

    def _resolve_wallet(self, wallet: str | None) -> str:
        return wallet or self.settings.wallet or DEFAULT_MOCK_WALLET

    def get_payments(self, rows: int = 10, *, wallet: str | None = None, **params: Any) -> ApiResponse:
        return super().get_payments(rows=rows, wallet=self._resolve_wallet(wallet), **params)

    def get_balance_accounts(self, *, wallet: str | None = None, **params: Any) -> ApiResponse:
        return super().get_balance_accounts(wallet=self._resolve_wallet(wallet), **params)

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

        if not use_auth or "Authorization" not in request_headers:
            body = _error_body(self._mock_responses, "error_unauthorized")
            return ApiResponse(status_code=401, headers={}, body=body, raw_text=json.dumps(body))

        if _is_invalid_token(request_headers):
            body = _error_body(self._mock_responses, "error_unauthorized")
            return ApiResponse(status_code=401, headers={}, body=body, raw_text=json.dumps(body))

        if method == "GET" and "/persons/" in path and path.endswith("/payments"):
            wallet = path.split("/persons/")[1].split("/payments")[0]
            if not WALLET_PATTERN.match(wallet):
                body = _error_body(self._mock_responses, "error_bad_wallet")
                return ApiResponse(status_code=400, headers={}, body=body, raw_text=json.dumps(body))
            body = self._mock_responses["payments_list"]
            return ApiResponse(status_code=200, headers={}, body=body, raw_text=json.dumps(body))

        if method == "GET" and "/persons/" in path and path.endswith("/accounts"):
            wallet = path.split("/persons/")[1].split("/accounts")[0]
            if not WALLET_PATTERN.match(wallet):
                body = _error_body(self._mock_responses, "error_bad_wallet")
                return ApiResponse(status_code=400, headers={}, body=body, raw_text=json.dumps(body))
            body = self._mock_responses["balance_accounts"]
            return ApiResponse(status_code=200, headers={}, body=body, raw_text=json.dumps(body))

        if method == "POST" and "/payments" in path:
            if not isinstance(json_body, dict):
                body = _error_body(self._mock_responses, "error_bad_request")
                return ApiResponse(status_code=400, headers={}, body=body, raw_text=json.dumps(body))

            missing_fields = [field for field in ("id", "sum", "paymentMethod", "fields") if field not in json_body]
            if missing_fields:
                body = _error_body(self._mock_responses, "error_missing_fields")
                return ApiResponse(status_code=400, headers={}, body=body, raw_text=json.dumps(body))

            sum_block = json_body.get("sum")
            if isinstance(sum_block, dict) and isinstance(sum_block.get("amount"), str):
                body = _error_body(self._mock_responses, "error_wrong_type")
                return ApiResponse(status_code=400, headers={}, body=body, raw_text=json.dumps(body))

            body = self._mock_responses["payment_created"]
            return ApiResponse(status_code=200, headers={}, body=body, raw_text=json.dumps(body))

        if method == "GET" and "/transactions/" in path:
            transaction_id = path.rsplit("/transactions/", maxsplit=1)[-1]
            if not TRANSACTION_ID_PATTERN.match(transaction_id):
                body = _error_body(self._mock_responses, "error_not_found")
                return ApiResponse(status_code=404, headers={}, body=body, raw_text=json.dumps(body))
            body = self._mock_responses["transaction_success"]
            return ApiResponse(status_code=200, headers={}, body=body, raw_text=json.dumps(body))

        body = {"message": "unmocked endpoint", "method": method, "path": path}
        return ApiResponse(status_code=404, headers={}, body=body, raw_text=json.dumps(body))

    def _clone(self) -> MockQiwiWalletClient:
        return MockQiwiWalletClient(self.settings, self._mock_responses)


def create_mock_client(settings: Settings, mock_responses: dict[str, Any]) -> MockQiwiWalletClient:
    """Return a QiwiWalletClient wired to deterministic mock responses."""
    return MockQiwiWalletClient(settings, mock_responses)
