"""Typed models for QIWI Wallet Personal API payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MoneyAmount:
    amount: float
    currency: str


@dataclass(slots=True)
class PaymentMethod:
    type: str = "Account"
    account_id: str = "643"

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "accountId": self.account_id}


@dataclass(slots=True)
class PaymentRequest:
    """Payment body for POST /sinap/api/v2/terms/{providerId}/payments."""

    payment_id: str
    amount: float
    recipient_account: str
    currency: str = "643"
    comment: str = ""
    payment_method: PaymentMethod = field(default_factory=PaymentMethod)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.payment_id,
            "sum": {"amount": self.amount, "currency": self.currency},
            "paymentMethod": self.payment_method.to_dict(),
            "fields": {"account": self.recipient_account},
        }
        if self.comment:
            payload["comment"] = self.comment
        return payload


@dataclass(slots=True)
class ApiResponse:
    """Normalized HTTP response wrapper."""

    status_code: int
    headers: dict[str, str]
    body: Any
    raw_text: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300
