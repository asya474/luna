"""Shared pytest fixtures for QIWI Wallet API tests."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Generator

import pytest
import requests

from api.client import QiwiWalletClient
from api.config import Settings, get_settings
from api.models import PaymentRequest
from helpers.mock_client import create_mock_client
from helpers.payment_id import generate_payment_id
from helpers.schema_validator import SchemaValidator

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "mock_responses.json"
logger = logging.getLogger("qiwi.tests")


def _load_mock_responses() -> dict[str, Any]:
    with FIXTURES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def validate_test_environment(settings: Settings) -> None:
    """Log effective configuration once per test session."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info(
        "Session config: mock_mode=%s, has_credentials=%s, wallet=%s",
        settings.mock_mode,
        settings.has_credentials,
        settings.wallet or "(not set)",
    )


@pytest.fixture(scope="session")
def schema_validator() -> SchemaValidator:
    return SchemaValidator()


@pytest.fixture(scope="session")
def mock_responses() -> dict[str, Any]:
    return _load_mock_responses()


@pytest.fixture
def qiwi_client(settings: Settings) -> Generator[QiwiWalletClient, None, None]:
    session = requests.Session()
    client = QiwiWalletClient(settings, session=session)
    yield client
    session.close()


@pytest.fixture
def mock_qiwi_client(settings: Settings, mock_responses: dict[str, Any]) -> QiwiWalletClient:
    """Client that returns documented fixture payloads without network calls."""
    return create_mock_client(settings, mock_responses)


@pytest.fixture
def payment_request(settings: Settings) -> PaymentRequest:
    recipient = settings.payment_recipient or settings.wallet or "79997654321"
    if not recipient.startswith("+"):
        recipient = f"+{recipient}"

    return PaymentRequest(
        payment_id=generate_payment_id(),
        amount=1.0,
        recipient_account=recipient,
        comment="API test payment 1 RUB",
    )


@pytest.fixture
def created_payment(
    settings: Settings,
    qiwi_client: QiwiWalletClient,
    mock_qiwi_client: QiwiWalletClient,
    payment_request: PaymentRequest,
) -> dict[str, Any]:
    """Create a payment and return parsed response body."""
    use_mock = settings.mock_mode or not settings.has_credentials
    client = mock_qiwi_client if use_mock else qiwi_client
    response = client.create_p2p_payment(payment_request)

    if not use_mock and not response.ok:
        pytest.skip(f"Payment creation unavailable: HTTP {response.status_code} {response.body}")

    assert isinstance(response.body, dict)
    return response.body


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: live API tests")
    config.addinivalue_line("markers", "mock: fixture-based tests")
    config.addinivalue_line("markers", "regression: negative and extended scenarios")
    config.addinivalue_line("markers", "playwright: browser-based documentation validation")


def _playwright_available() -> bool:
    try:
        import pytest_playwright  # noqa: F401

        return True
    except ImportError:
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    settings = get_settings()
    skip_integration = pytest.mark.skip(reason="QIWI_API_TOKEN or QIWI_WALLET is not configured")
    skip_live_payment = pytest.mark.skip(reason="QIWI_PAYMENT_RECIPIENT is not configured")
    skip_playwright = pytest.mark.skip(
        reason=(
            "pytest-playwright not installed; run: "
            "pip install -e '.[playwright]' && playwright install chromium webkit"
        )
    )

    for item in items:
        if "integration" in item.keywords and not settings.has_credentials:
            item.add_marker(skip_integration)
        if "integration" in item.keywords and "e2e" in item.keywords and not settings.payment_recipient:
            item.add_marker(skip_live_payment)
        if "playwright" in item.keywords and not _playwright_available():
            item.add_marker(skip_playwright)
