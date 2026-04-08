"""Tests for app.engines.base — Capability, data objects, BaseEngine."""

import asyncio
import hashlib
import pytest
from unittest.mock import patch, AsyncMock

from app.engines.base import (
    Capability,
    FetchResult,
    SearchResult,
    InteractResult,
    BaseEngine,
    _timed,
)


# ── Capability enum ──────────────────────────────────────────────────

class TestCapability:
    def test_values(self):
        assert Capability.FETCH.value == "fetch"
        assert Capability.SEARCH.value == "search"
        assert Capability.INTERACT.value == "interact"
        assert Capability.CRAWL.value == "crawl"
        assert Capability.STRUCTURED.value == "structured"

    def test_all_members(self):
        assert len(Capability) == 5


# ── FetchResult ──────────────────────────────────────────────────────

class TestFetchResult:
    def test_creation_minimal(self):
        r = FetchResult(ok=True, url="https://example.com")
        assert r.ok is True
        assert r.url == "https://example.com"
        assert r.status == 0
        assert r.text == ""
        assert r.html == ""
        assert r.engine == ""
        assert r.metadata == {}

    def test_creation_full(self):
        r = FetchResult(
            ok=False, url="https://x.com", status=403,
            text="blocked", html="<p>blocked</p>",
            title="Blocked", engine="scrapling", route="scrapling:fetch",
            duration_ms=123.4, error="403 Forbidden",
            metadata={"retries": 2},
        )
        assert r.ok is False
        assert r.status == 403
        assert r.error == "403 Forbidden"
        assert r.metadata["retries"] == 2

    def test_compute_hash(self):
        r = FetchResult(ok=True, url="https://a.com", text="hello world")
        h = r.compute_hash()
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert h == expected
        assert r.content_hash == expected


# ── SearchResult ─────────────────────────────────────────────────────

class TestSearchResult:
    def test_creation(self):
        r = SearchResult(url="https://a.com", title="A", snippet="desc", source="g")
        assert r.url == "https://a.com"
        assert r.credibility == 0.5  # default

    def test_defaults(self):
        r = SearchResult(url="u", title="t")
        assert r.rank == 0
        assert r.metadata == {}


# ── InteractResult ───────────────────────────────────────────────────

class TestInteractResult:
    def test_creation(self):
        r = InteractResult(ok=True, url="https://a.com", engine="pinchtab", text="done")
        assert r.ok is True
        assert r.engine == "pinchtab"

    def test_defaults(self):
        r = InteractResult(ok=False, url="u")
        assert r.snapshot == ""
        assert r.instance_id == ""


# ── BaseEngine (abstract) ───────────────────────────────────────────

class ConcreteEngine(BaseEngine):
    @property
    def name(self):
        return "concrete"

    @property
    def capabilities(self):
        return {Capability.FETCH}


class TestBaseEngine:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseEngine()

    def test_concrete_instantiation(self):
        eng = ConcreteEngine()
        assert eng.name == "concrete"
        assert Capability.FETCH in eng.capabilities

    def test_repr(self):
        eng = ConcreteEngine()
        r = repr(eng)
        assert "concrete" in r
        assert "fetch" in r

    @pytest.mark.asyncio
    async def test_default_health_check(self):
        eng = ConcreteEngine()
        assert await eng.health_check() is True

    @pytest.mark.asyncio
    async def test_fetch_not_implemented_with_capability(self):
        eng = ConcreteEngine()
        with pytest.raises(NotImplementedError):
            await eng.fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_without_capability(self):
        class NoFetch(BaseEngine):
            @property
            def name(self):
                return "nofetch"

            @property
            def capabilities(self):
                return {Capability.SEARCH}

        eng = NoFetch()
        result = await eng.fetch("https://x.com")
        assert result.ok is False
        assert "does not support FETCH" in result.error

    @pytest.mark.asyncio
    async def test_search_raises(self):
        eng = ConcreteEngine()
        with pytest.raises(NotImplementedError):
            await eng.search("test query")

    @pytest.mark.asyncio
    async def test_interact_without_capability(self):
        eng = ConcreteEngine()
        result = await eng.interact("https://x.com", [])
        assert result.ok is False
        assert "does not support INTERACT" in result.error


# ── _run_subprocess ──────────────────────────────────────────────────

class TestRunSubprocess:
    @pytest.mark.asyncio
    async def test_successful_command(self):
        eng = ConcreteEngine()
        code, stdout, stderr = await eng._run_subprocess(
            ["python", "-c", "print('hello')"], timeout=10
        )
        assert code == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_binary_not_found(self):
        eng = ConcreteEngine()
        code, stdout, stderr = await eng._run_subprocess(
            ["nonexistent_binary_xyz_123"], timeout=5
        )
        assert code == 78
        assert "binary not found" in stderr

    @pytest.mark.asyncio
    async def test_timeout(self):
        eng = ConcreteEngine()
        code, stdout, stderr = await eng._run_subprocess(
            ["python", "-c", "import time; time.sleep(60)"], timeout=1
        )
        assert code == 75
        assert "timeout" in stderr


# ── _timed context manager ──────────────────────────────────────────

class TestTimed:
    @pytest.mark.asyncio
    async def test_timed_returns_elapsed(self):
        async with _timed() as elapsed:
            await asyncio.sleep(0.05)
        ms = elapsed()
        assert ms >= 40  # at least ~50ms minus jitter
        assert ms < 1000
