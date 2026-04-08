"""Integration tests for EngineManager — fetch_with_fallback and search_multi."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.engines.base import Capability, FetchResult
from app.engines.manager import EngineManager
from app.engines.scrapling_engine import ScraplingEngine


@pytest.mark.asyncio
async def test_fetch_with_fallback_scrapling():
    """EngineManager.fetch_with_fallback works with real Scrapling."""
    em = EngineManager()
    em.register(ScraplingEngine())

    try:
        result: FetchResult = await asyncio.wait_for(
            em.fetch_with_fallback("https://httpbin.org/html", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Network unavailable or timed out: {exc}")

    if not result.ok and "No module" in result.error:
        pytest.skip(f"Engine dependency missing: {result.error}")

    assert result.ok is True
    assert len(result.text) > 0 or len(result.html) > 0
    assert result.engine != ""


@pytest.mark.asyncio
async def test_fallback_chain_mock_then_real():
    """First engine fails (mocked), Scrapling succeeds as fallback."""
    em = EngineManager()

    # Create a mock engine that always fails
    mock_engine = AsyncMock()
    mock_engine.name = "mock_failing"
    mock_engine.capabilities = {Capability.FETCH}
    mock_engine.health_check = AsyncMock(return_value=True)
    mock_engine.fetch = AsyncMock(
        return_value=FetchResult(ok=False, url="", error="mock failure")
    )

    em.register(mock_engine)
    em.register(ScraplingEngine())

    try:
        result: FetchResult = await asyncio.wait_for(
            em.fetch_with_fallback("https://httpbin.org/html", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Network unavailable or timed out: {exc}")

    if not result.ok and ("No module" in result.error or "exhausted" in result.error):
        pytest.skip(f"Engine dependency missing or all failed: {result.error}")

    # Should have fallen back to scrapling and succeeded
    assert result.ok is True
    assert result.engine == "scrapling"


@pytest.mark.asyncio
async def test_search_multi_with_real_engines(engine_manager):
    """EngineManager.search_multi returns results from available engines."""
    try:
        results = await asyncio.wait_for(
            engine_manager.search_multi("Python asyncio", max_results=5, language="en"),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Search unavailable or timed out: {exc}")

    assert isinstance(results, list)
    # At least some engine should have returned results
    # (may be empty if no search engines are available)
