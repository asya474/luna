"""Optional Playwright smoke tests for QIWI API documentation availability."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from api.config import Settings


@pytest.mark.playwright
@pytest.mark.smoke
def test_docs_page_loads(browser_page: tuple[Page, str], settings: Settings) -> None:
    """Verify official documentation is reachable and contains key API sections."""
    page, browser_engine = browser_page
    page.goto(settings.docs_url, wait_until="domcontentloaded", timeout=60_000)

    content = page.content()
    assert "edge.qiwi.com" in content, f"Docs URL not found in page content ({browser_engine})"
    assert "payment-history" in content or "История платежей" in content
    assert "funding-sources" in content or "Баланс" in content
    assert "sinap/api/v2/terms" in content or "Перевод на QIWI" in content


@pytest.mark.playwright
@pytest.mark.smoke
def test_docs_contains_auth_section(browser_page: tuple[Page, str], settings: Settings) -> None:
    page, browser_engine = browser_page
    page.goto(settings.docs_url, wait_until="domcontentloaded", timeout=60_000)

    assert (
        page.locator("text=Bearer").count() > 0 or "Bearer token" in page.content()
    ), f"Bearer auth section not found ({browser_engine})"
