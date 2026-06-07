"""Playwright-specific pytest configuration and browser fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generator

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page, Playwright

# Playwright engine names: chromium = Chrome, webkit = Safari (WebKit engine).
BROWSER_ENGINES = ("chromium", "webkit")
BROWSER_IDS = ("chrome", "safari")


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict:
    return {"headless": True}


@pytest.fixture(params=BROWSER_ENGINES, ids=BROWSER_IDS)
def browser_engine(request: pytest.FixtureRequest) -> str:
    """
    Parametrize each Playwright test across Chrome and Safari engines.

    Playwright uses ``chromium`` for Chrome and ``webkit`` for Safari (WebKit).
    """
    return request.param


@pytest.fixture(scope="session")
def playwright_instance(playwright: Playwright) -> Playwright:
    """Session-scoped Playwright driver (alias for pytest-playwright ``playwright``)."""
    return playwright


@pytest.fixture
def browser_context_page(
    playwright_instance: Playwright,
    browser_engine: str,
) -> Generator[tuple[Page, str], None, None]:
    """Create an isolated browser context and page for the parametrized engine."""
    browser_type = getattr(playwright_instance, browser_engine)
    browser = browser_type.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page, browser_engine
    finally:
        context.close()
        browser.close()


@pytest.fixture
def browser_page(browser_context_page: tuple[Page, str]) -> tuple[Page, str]:
    """
    Recommended fixture for Playwright tests.

    Returns ``(page, browser_engine)`` where ``browser_engine`` is ``chromium``
    (Chrome) or ``webkit`` (Safari).
    """
    return browser_context_page
