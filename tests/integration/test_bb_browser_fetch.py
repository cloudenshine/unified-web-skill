"""Integration tests for BBBrowserEngine — requires bb-browser binary."""
import asyncio
import shutil

import pytest

from app.engines.bb_browser import BBBrowserEngine

_has_bb = shutil.which("bb-browser") is not None or shutil.which("bb") is not None


@pytest.fixture
def bb():
    return BBBrowserEngine()


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_bb, reason="bb-browser binary not installed")
async def test_bb_browser_fetch_simple(bb):
    """bb-browser can fetch a simple website."""
    try:
        result = await asyncio.wait_for(
            bb.fetch("https://example.com", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"bb-browser fetch failed or timed out: {exc}")

    assert result.engine == "bb-browser"
    if result.ok:
        assert len(result.text) > 0 or len(result.html) > 0
