"""Environment-driven configuration for QIWI API tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://edge.qiwi.com"
DEFAULT_DOCS_URL = "https://developer.qiwi.com/ru/qiwi-wallet-personal/#intro"
RUB_CURRENCY_CODE = "643"
RUB_WALLET_ALIAS = "qw_wallet_rub"
P2P_PROVIDER_ID = "99"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    api_token: str
    wallet: str
    payment_recipient: str
    base_url: str
    mock_mode: bool
    request_timeout: int
    docs_url: str

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_token and self.wallet)

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings(
        api_token=os.getenv("QIWI_API_TOKEN", "").strip(),
        wallet=os.getenv("QIWI_WALLET", "").strip(),
        payment_recipient=os.getenv("QIWI_PAYMENT_RECIPIENT", "").strip(),
        base_url=os.getenv("QIWI_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        mock_mode=_env_bool("QIWI_MOCK_MODE"),
        request_timeout=int(os.getenv("QIWI_REQUEST_TIMEOUT", "30")),
        docs_url=os.getenv("QIWI_DOCS_URL", DEFAULT_DOCS_URL),
    )
