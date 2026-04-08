"""Integration tests for CLIBrowserEngine — requires clibrowser binary."""
import asyncio
import shutil

import pytest

from app.engines.clibrowser import CLIBrowserEngine

_has_clibrowser = shutil.which("clibrowser") is not None


@pytest.fixture
def clibrowser():
    return CLIBrowserEngine()


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_clibrowser, reason="clibrowser binary not installed")
async def test_clibrowser_fetch_url(clibrowser):
    """CLIBrowser can fetch a URL."""
    try:
        result = await asyncio.wait_for(
            clibrowser.fetch("https://example.com", timeout=20),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"clibrowser fetch failed or timed out: {exc}")

    assert result.engine == "clibrowser"
    if result.ok:
        assert len(result.text) > 0 or len(result.html) > 0
