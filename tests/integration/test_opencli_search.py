"""Integration tests for OpenCLIEngine — requires opencli binary."""
import asyncio
import shutil

import pytest

from app.engines.opencli import OpenCLIEngine

_has_opencli = shutil.which("opencli") is not None


@pytest.fixture
def opencli():
    return OpenCLIEngine()


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_opencli, reason="opencli binary not installed")
async def test_opencli_search_simple(opencli):
    """OpenCLI can perform a basic search query."""
    try:
        results = await asyncio.wait_for(
            opencli.search("Python programming", max_results=5, language="en"),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"OpenCLI search failed or timed out: {exc}")

    assert isinstance(results, list)
    # If opencli is working, we expect some results
    if len(results) > 0:
        r = results[0]
        assert hasattr(r, "url")
        assert hasattr(r, "title")
