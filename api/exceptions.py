"""Custom exceptions for QIWI API client."""

from __future__ import annotations

from typing import Any


class QiwiApiError(Exception):
    """Raised when the QIWI API returns an unexpected response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class QiwiSchemaError(Exception):
    """Raised when a response does not match the documented schema."""

    def __init__(self, message: str, *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []
