"""Tests for app.engines.manager — EngineManager and SmartRouter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.engines.base import Capability, FetchResult, SearchResult, InteractResult
from app.engines.manager import EngineManager, SmartRouter, SiteRegistry as ManagerSiteRegistry
from app.engines.health import EngineHealthMonitor

from .conftest import StubEngine, FailingEngine


# ── EngineManager registration ───────────────────────────────────────

class TestEngineManagerRegistration:
    def test_register_engine(self):
        mgr = EngineManager()
        eng = StubEngine("alpha", {Capability.FETCH})
        mgr.register(eng)
        assert mgr.get_engine("alpha") is eng
        assert "alpha" in mgr.list_engines()

    def test_register_overwrites(self):
        mgr = EngineManager()
        eng1 = StubEngine("alpha")
        eng2 = StubEngine("alpha")
        mgr.register(eng1)
        mgr.register(eng2)
        assert mgr.get_engine("alpha") is eng2

    def test_unregister(self):
        mgr = EngineManager()
        mgr.register(StubEngine("alpha"))
        mgr.unregister("alpha")
        assert mgr.get_engine("alpha") is None

    def test_unregister_idempotent(self):
        mgr = EngineManager()
        mgr.unregister("nonexistent")  # no error

    def test_list_engines(self):
        mgr = EngineManager()
        mgr.register(StubEngine("a", {Capability.FETCH, Capability.SEARCH}))
        mgr.register(StubEngine("b", {Capability.FETCH}))
        listing = mgr.list_engines()
        assert set(listing.keys()) == {"a", "b"}
        assert "fetch" in listing["a"]
        assert "search" in listing["a"]

    def test_get_engines_with_capability(self):
        mgr = EngineManager()
        mgr.register(StubEngine("a", {Capability.FETCH}))
        mgr.register(StubEngine("b", {Capability.SEARCH}))
        mgr.register(StubEngine("c", {Capability.FETCH, Capability.SEARCH}))
        fetchers = mgr.get_engines_with_capability(Capability.FETCH)
        assert len(fetchers) == 2
        searchers = mgr.get_engines_with_capability(Capability.SEARCH)
        assert len(searchers) == 2


# ── SmartRouter ──────────────────────────────────────────────────────

class TestSmartRouter:
    def _make_router(self):
        sr = ManagerSiteRegistry()
        hm = EngineHealthMonitor()
        return SmartRouter(sr, hm), sr, hm

    def test_default_fetch_order(self):
        router, sr, hm = self._make_router()
        engines = {
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
            "lightpanda": StubEngine("lightpanda", {Capability.FETCH}),
            "clibrowser": StubEngine("clibrowser", {Capability.FETCH}),
        }
        order = router.resolve_fetch_order("https://example.com", engines)
        assert "scrapling" in order
        assert "lightpanda" in order

    def test_site_registry_match(self):
        router, sr, hm = self._make_router()
        # The manager's SiteRegistry uses suffix matching with "*.domain" pattern
        sr.register_domain("*.bilibili.com", ["bb-browser", "opencli"])
        engines = {
            "bb-browser": StubEngine("bb-browser", {Capability.FETCH}),
            "opencli": StubEngine("opencli", {Capability.FETCH}),
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
        }
        order = router.resolve_fetch_order("https://www.bilibili.com/video/123", engines)
        assert order[0] == "bb-browser"
        assert order[1] == "opencli"

    def test_chinese_url_priority(self):
        router, sr, hm = self._make_router()
        engines = {
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
            "lightpanda": StubEngine("lightpanda", {Capability.FETCH}),
        }
        order = router.resolve_fetch_order("https://www.zhihu.com/q/123", engines)
        # Chinese URL should prefer lightpanda
        assert order[0] == "lightpanda"

    def test_preferred_engines_override(self):
        router, sr, hm = self._make_router()
        engines = {
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
            "lightpanda": StubEngine("lightpanda", {Capability.FETCH}),
        }
        order = router.resolve_fetch_order(
            "https://example.com", engines, preferred=["lightpanda", "scrapling"]
        )
        assert order[0] == "lightpanda"

    def test_unhealthy_engines_excluded(self):
        router, sr, hm = self._make_router()
        # Trip the circuit breaker for scrapling
        for _ in range(5):
            hm.record_failure("scrapling")
        engines = {
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
            "lightpanda": StubEngine("lightpanda", {Capability.FETCH}),
        }
        order = router.resolve_fetch_order("https://example.com", engines)
        assert "scrapling" not in order

    def test_resolve_interact_engine(self):
        router, sr, hm = self._make_router()
        engines = {
            "pinchtab": StubEngine("pinchtab", {Capability.INTERACT, Capability.FETCH}),
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
        }
        chosen = router.resolve_interact_engine("https://example.com", engines)
        assert chosen == "pinchtab"

    def test_resolve_interact_engine_preferred(self):
        router, sr, hm = self._make_router()
        engines = {
            "pinchtab": StubEngine("pinchtab", {Capability.INTERACT, Capability.FETCH}),
            "bb_browser": StubEngine("bb_browser", {Capability.INTERACT, Capability.FETCH}),
        }
        chosen = router.resolve_interact_engine("https://example.com", engines, preferred="bb_browser")
        assert chosen == "bb_browser"

    def test_resolve_interact_engine_none(self):
        router, sr, hm = self._make_router()
        engines = {
            "scrapling": StubEngine("scrapling", {Capability.FETCH}),
        }
        chosen = router.resolve_interact_engine("https://example.com", engines)
        assert chosen is None


# ── EngineManager fetch_with_fallback ────────────────────────────────

class TestFetchWithFallback:
    @pytest.mark.asyncio
    async def test_success_first_engine(self):
        mgr = EngineManager()
        mgr.register(StubEngine("scrapling", {Capability.FETCH}))
        result = await mgr.fetch_with_fallback("https://example.com")
        assert result.ok is True
        assert result.engine == "scrapling"

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        mgr = EngineManager()
        mgr.register(FailingEngine("bad"))
        mgr.register(StubEngine("good", {Capability.FETCH}))
        result = await mgr.fetch_with_fallback(
            "https://example.com", preferred_engines=["bad", "good"]
        )
        assert result.ok is True
        assert result.engine == "good"

    @pytest.mark.asyncio
    async def test_all_engines_fail(self):
        mgr = EngineManager()
        mgr.register(FailingEngine("bad1"))
        mgr.register(FailingEngine("bad2"))
        result = await mgr.fetch_with_fallback(
            "https://example.com", preferred_engines=["bad1", "bad2"]
        )
        assert result.ok is False
        assert "All engines exhausted" in result.error

    @pytest.mark.asyncio
    async def test_no_engines_registered(self):
        mgr = EngineManager()
        result = await mgr.fetch_with_fallback("https://example.com")
        assert result.ok is False
        assert "No engines available" in result.error


# ── EngineManager search_multi ───────────────────────────────────────

class TestSearchMulti:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        mgr = EngineManager()
        mgr.register(StubEngine("s1", {Capability.SEARCH, Capability.FETCH}))
        results = await mgr.search_multi("test query")
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_deduplicates_by_url(self):
        mgr = EngineManager()
        mgr.register(StubEngine("s1", {Capability.SEARCH}))
        mgr.register(StubEngine("s2", {Capability.SEARCH}))
        results = await mgr.search_multi("test", max_results=20)
        urls = [r.url for r in results]
        assert len(urls) == len(set(urls))

    @pytest.mark.asyncio
    async def test_search_no_engines(self):
        mgr = EngineManager()
        mgr.register(StubEngine("f", {Capability.FETCH}))
        results = await mgr.search_multi("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_exception(self):
        mgr = EngineManager()
        mgr.register(FailingEngine("bad"))
        results = await mgr.search_multi("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_specific_engines(self):
        mgr = EngineManager()
        mgr.register(StubEngine("s1", {Capability.SEARCH}))
        mgr.register(StubEngine("s2", {Capability.SEARCH}))
        results = await mgr.search_multi("test", engines=["s1"])
        # s2 should not have been queried
        for r in results:
            assert r.source == "s1"


# ── EngineManager interact ──────────────────────────────────────────

class TestInteract:
    @pytest.mark.asyncio
    async def test_interact_success(self):
        mgr = EngineManager()
        mgr.register(StubEngine("pinchtab", {Capability.INTERACT, Capability.FETCH}))
        result = await mgr.interact("https://example.com", [{"action": "click"}])
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_interact_no_engine(self):
        mgr = EngineManager()
        mgr.register(StubEngine("scrapling", {Capability.FETCH}))
        result = await mgr.interact("https://example.com", [])
        assert result.ok is False
        assert "No engines available" in result.error
