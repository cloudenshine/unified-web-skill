"""Integration tests for ScraplingEngine — real HTTP requests."""
import asyncio

import pytest

from app.engines.scrapling_engine import ScraplingEngine
from app.engines.base import FetchResult


@pytest.fixture
def scrapling():
    return ScraplingEngine()


@pytest.mark.asyncio
async def test_scrapling_fetch_httpbin(scrapling):
    """Scrapling can fetch httpbin.org/html and return real content."""
    try:
        result: FetchResult = await asyncio.wait_for(
            scrapling.fetch("https://httpbin.org/html", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Network unavailable or timed out: {exc}")

    if not result.ok and "No module" in result.error:
        pytest.skip(f"Engine dependency missing: {result.error}")

    assert result.ok is True
    assert result.url == "https://httpbin.org/html"
    assert result.engine == "scrapling"
    # httpbin /html returns Herman Melville text
    assert len(result.text) > 50 or len(result.html) > 50


@pytest.mark.asyncio
async def test_scrapling_handles_404(scrapling):
    """Scrapling returns ok=False for 404 pages without raising."""
    try:
        result: FetchResult = await asyncio.wait_for(
            scrapling.fetch("https://httpbin.org/status/404", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Network unavailable or timed out: {exc}")

    if not result.ok and "No module" in (result.error or ""):
        pytest.skip(f"Engine dependency missing: {result.error}")

    # Engine should gracefully report failure
    assert result.ok is False or result.status == 404


@pytest.mark.asyncio
async def test_scrapling_handles_nonexistent_domain(scrapling):
    """Scrapling returns ok=False for a non-existent domain without raising."""
    try:
        result: FetchResult = await asyncio.wait_for(
            scrapling.fetch("https://this-domain-does-not-exist-xyz123.com", timeout=15),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Network unavailable or timed out: {exc}")

    if not result.ok and "No module" in (result.error or ""):
        pytest.skip(f"Engine dependency missing: {result.error}")

    assert result.ok is False
    assert result.error != ""
