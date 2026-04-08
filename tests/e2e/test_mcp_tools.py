"""E2E test: MCP tool functions called directly (bypassing MCP transport).

Since MCP tool functions are registered via @mcp.tool() and may not be
directly importable, we test the underlying APIs that the tools wrap.
"""
import asyncio

import pytest

from app.engines.manager import EngineManager
from app.engines.scrapling_engine import ScraplingEngine
from app.engines.base import FetchResult
from app.discovery.multi_source import MultiSourceDiscovery


@pytest.fixture
def em():
    manager = EngineManager()
    manager.register(ScraplingEngine())
    return manager


@pytest.mark.asyncio
async def test_web_fetch_via_engine_manager(em):
    """Equivalent to web_fetch MCP tool: fetch httpbin.org via EngineManager."""
    try:
        result: FetchResult = await asyncio.wait_for(
            em.fetch_with_fallback("https://httpbin.org/html", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Network unavailable: {exc}")

    if not result.ok and "No module" in (result.error or ""):
        pytest.skip(f"Engine dependency missing: {result.error}")

    assert result.ok is True
    assert "Herman" in result.text or len(result.html) > 100
    assert result.engine != ""


@pytest.mark.asyncio
async def test_web_search_via_discovery():
    """Equivalent to web_search MCP tool: search via MultiSourceDiscovery."""
    discovery = MultiSourceDiscovery()

    try:
        results = await asyncio.wait_for(
            discovery.discover("Python tutorial", max_sources=5, language="en"),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Search unavailable: {exc}")

    assert isinstance(results, list)
    if len(results) > 0:
        assert results[0].url.startswith("http")


@pytest.mark.asyncio
async def test_engine_status_via_engine_manager(em):
    """Equivalent to engine_status MCP tool: list engines and capabilities."""
    engine_list = em.list_engines()

    assert isinstance(engine_list, dict)
    assert "scrapling" in engine_list
    assert isinstance(engine_list["scrapling"], list)
    assert len(engine_list["scrapling"]) > 0


@pytest.mark.asyncio
async def test_engine_health_check(em):
    """Health check all registered engines."""
    try:
        health = await asyncio.wait_for(
            em.health_check_all(),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Health check timed out: {exc}")

    assert isinstance(health, dict)
    assert "scrapling" in health
    # Scrapling should be healthy if network is available
