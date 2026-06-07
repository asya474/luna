"""Domain-specific assertions for QIWI API tests."""

from __future__ import annotations

from typing import Any

from api.config import RUB_WALLET_ALIAS
from api.exceptions import QiwiApiError
from api.models import ApiResponse


def assert_status_code(response: ApiResponse, expected: int | set[int] | frozenset[int]) -> None:
    """Assert HTTP response status code matches expected value(s)."""
    allowed = frozenset({expected}) if isinstance(expected, int) else frozenset(expected)
    if response.status_code not in allowed:
        raise QiwiApiError(
            f"Expected HTTP status {sorted(allowed)}, got {response.status_code}",
            status_code=response.status_code,
            payload=response.body,
        )


def assert_balance_positive(accounts_payload: dict[str, Any]) -> float:
    """Assert RUB wallet balance exists and is strictly greater than zero."""
    accounts = accounts_payload.get("accounts")
    if not isinstance(accounts, list):
        raise QiwiApiError("Balance response must contain 'accounts' array")

    rub_account = next((item for item in accounts if item.get("alias") == RUB_WALLET_ALIAS), None)
    if rub_account is None:
        raise QiwiApiError(f"RUB account '{RUB_WALLET_ALIAS}' not found in balance response")

    if not rub_account.get("hasBalance"):
        raise QiwiApiError("RUB wallet account must have hasBalance=true")

    balance = rub_account.get("balance")
    if not isinstance(balance, dict):
        raise QiwiApiError("RUB wallet balance object is missing")

    amount = balance.get("amount")
    if not isinstance(amount, (int, float)):
        raise QiwiApiError("RUB wallet balance amount must be numeric")

    if amount <= 0:
        raise QiwiApiError(f"RUB wallet balance must be > 0, got {amount}")

    return float(amount)


def assert_payment_accepted(payment_payload: dict[str, Any]) -> str:
    """Assert payment creation response matches PaymentInfo with Accepted state."""
    transaction = payment_payload.get("transaction")
    if not isinstance(transaction, dict):
        raise QiwiApiError("Payment response must contain 'transaction' object")

    transaction_id = transaction.get("id")
    if not transaction_id:
        raise QiwiApiError("Payment transaction id is missing")

    state = transaction.get("state", {})
    state_code = state.get("code") if isinstance(state, dict) else None
    if state_code != "Accepted":
        raise QiwiApiError(
            f"Expected transaction.state.code='Accepted', got '{state_code}'",
            payload=payment_payload,
        )

    return str(transaction_id)
