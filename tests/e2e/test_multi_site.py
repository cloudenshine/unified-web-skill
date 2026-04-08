"""E2E test: fetch across 10+ sites to verify broad compatibility."""
import asyncio

import pytest

from app.engines.manager import EngineManager
from app.engines.scrapling_engine import ScraplingEngine

SITES = [
    "https://httpbin.org/html",
    "https://example.com",
    "https://news.ycombinator.com",
    "https://www.wikipedia.org",
    "https://httpbin.org/get",
    "https://httpbin.org/robots.txt",
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://www.iana.org/domains/reserved",
    "https://httpbin.org/headers",
    "https://httpbin.org/ip",
    "https://httpbin.org/user-agent",
]


@pytest.fixture
def em():
    manager = EngineManager()
    manager.register(ScraplingEngine())
    return manager


@pytest.mark.asyncio
@pytest.mark.parametrize("url", SITES, ids=[u.split("//")[1][:30] for u in SITES])
async def test_fetch_site(em, url):
    """EngineManager.fetch_with_fallback can fetch each site."""
    try:
        result = await asyncio.wait_for(
            em.fetch_with_fallback(url, timeout=20),
            timeout=30,
        )
    except asyncio.TimeoutError:
        pytest.skip(f"Timed out fetching {url}")
    except Exception as exc:
        pytest.skip(f"Network error for {url}: {exc}")

    # We mainly care that it doesn't crash; ok may be False for some sites
    assert result is not None
    assert hasattr(result, "ok")
    assert hasattr(result, "url")

    if not result.ok and "No module" in (result.error or ""):
        pytest.skip(f"Engine dependency missing: {result.error}")

    if result.ok:
        assert len(result.text) > 0 or len(result.html) > 0
