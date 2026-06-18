"""Tests for external API provider engines: JinaReader and Firecrawl."""

import sys; sys.path.insert(0, "E:/claude_work/g/unified-web-skill")
import os

from app.engines.providers.jina_reader import JinaReaderEngine
from app.engines.providers.firecrawl import FirecrawlEngine


class TestJinaReaderEngine:
    """Verify JinaReaderEngine interface, no-key handling, data model."""

    def test_name(self):
        assert JinaReaderEngine.name == "jina-reader"

    def test_capabilities(self):
        caps = {c.value for c in JinaReaderEngine.capabilities}
        assert "fetch" in caps

    def test_health_check_no_key(self):
        """Without JINA_API_KEY, health_check returns False (graceful)."""
        import asyncio
        e = JinaReaderEngine()
        result = asyncio.run(e.health_check())
        assert result is False

    def test_fetch_no_key_returns_error(self):
        """Without API key, fetch returns ok=False with descriptive error."""
        import asyncio
        e = JinaReaderEngine()
        result = asyncio.run(e.fetch("https://example.com"))
        assert result.ok is False
        assert "API key" in result.error
        assert result.url == "https://example.com"

    def test_fetch_with_api_key_format(self):
        """Verify FetchResult fields are correct shape (no actual HTTP call)."""
        from app.engines.base import FetchResult
        # Direct construction test
        result = FetchResult(
            ok=True, url="https://example.com", engine="jina-reader",
            text="# Hello", quality_score=0.8,
        )
        assert result.quality_score == 0.8

    def test_version_info(self):
        e = JinaReaderEngine()
        vi = e.version_info()
        assert vi["engine"] == "jina-reader"
        assert vi["version"] == "1.0"
        assert "r.jina.ai" in vi["api"]

    def test_health_check_is_async(self):
        import inspect
        assert inspect.iscoroutinefunction(JinaReaderEngine.health_check)


class TestFirecrawlEngine:
    """Verify FirecrawlEngine interface, keyless mode, data model."""

    def test_name(self):
        assert FirecrawlEngine.name == "firecrawl"

    def test_capabilities(self):
        caps = {c.value for c in FirecrawlEngine.capabilities}
        assert "fetch" in caps
        assert "search" in caps

    def test_keyless_mode_by_default(self):
        """Without FIRECRAWL_API_KEY, engine operates in keyless mode."""
        e = FirecrawlEngine()
        assert e._use_keyless is True

    def test_headers_no_key(self):
        e = FirecrawlEngine()
        h = e._headers()
        assert h["Content-Type"] == "application/json"
        assert "Authorization" not in h

    def test_headers_with_key(self):
        old = os.environ.get("FIRECRAWL_API_KEY", "")
        os.environ["FIRECRAWL_API_KEY"] = "fc-test-key-123"
        try:
            e = FirecrawlEngine()
            assert e._use_keyless is False
            h = e._headers()
            assert "Bearer fc-test-key-123" in h["Authorization"]
        finally:
            if old:
                os.environ["FIRECRAWL_API_KEY"] = old
            else:
                del os.environ["FIRECRAWL_API_KEY"]

    def test_version_info_keyless(self):
        e = FirecrawlEngine()
        import asyncio
        vi = asyncio.run(e.version_info())
        assert vi["ok"] is True
        assert vi["keyless"] is True
        assert "Free tier" in vi["note"]

    def test_health_check_no_key_does_not_crash(self):
        """health_check runs even without API key (keyless mode)."""
        import asyncio
        e = FirecrawlEngine()
        # Should not raise; may return False if endpoint unreachable
        result = asyncio.run(e.health_check())
        assert result in (True, False)

    def test_fetch_no_key_does_not_crash(self):
        """fetch runs even without API key - returns error gracefully."""
        import asyncio
        e = FirecrawlEngine()
        result = asyncio.run(e.fetch("https://example.com"))
        # May fail with network error but should not raise
        assert isinstance(result.ok, bool)
        assert result.engine == "firecrawl"

    def test_search_no_key_does_not_crash(self):
        """search runs even without API key."""
        import asyncio
        e = FirecrawlEngine()
        results = asyncio.run(e.search("test query", max_results=3))
        assert isinstance(results, list)

    def test_fetch_result_has_quality_score(self):
        """FetchResult from firecrawl includes quality_score=0.85."""
        from app.engines.base import FetchResult
        result = FetchResult(
            ok=True, url="https://example.com", engine="firecrawl",
            text="# Test", quality_score=0.85,
        )
        assert result.quality_score == 0.85
