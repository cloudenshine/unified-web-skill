"""Tests for app.discovery.site_registry — SiteRegistry and SiteCapability."""

import pytest
from app.discovery.site_registry import SiteRegistry, SiteCapability
from app.discovery.source_matrix import SourceMatrix


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure each test gets a fresh singleton."""
    SiteRegistry.reset_instance()
    yield
    SiteRegistry.reset_instance()


class TestSiteRegistryBuiltin:
    def test_load_builtin_count(self):
        reg = SiteRegistry()
        count = reg.load_builtin()
        assert count >= 100, f"Expected 100+ sites, got {count}"

    def test_site_count_property(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.site_count >= 100

    def test_low_friction_promoted_sources_are_registered(self):
        reg = SiteRegistry()
        reg.load_builtin()
        matrix = SourceMatrix.load_builtin()

        promoted_sources = [
            source
            for source in matrix.all_sources()
            if source.promotion_status == "promoted"
            and source.access_type in {"api", "rss", "static_html"}
        ]

        assert len(promoted_sources) >= 50
        for source in promoted_sources:
            cap = reg[source.site_id]
            assert source.preferred_provider in cap.engines
            assert cap.auth_required is False
            assert cap.default_fetch_mode == "http"

    def test_promoted_structured_adapters_include_matrix_preferred_provider(self):
        reg = SiteRegistry()
        reg.load_builtin()
        matrix = SourceMatrix.load_builtin()

        promoted_adapters = [
            source
            for source in matrix.all_sources()
            if source.promotion_status == "promoted"
            and source.access_type == "structured_adapter"
        ]

        assert promoted_adapters
        for source in promoted_adapters:
            cap = reg[source.site_id]
            assert source.preferred_provider in cap.engines

    def test_browser_verified_static_sources_are_registered_with_browser_first(self):
        reg = SiteRegistry()
        reg.load_builtin()

        for site_id in {"stackoverflow", "reuters"}:
            cap = reg[site_id]
            assert cap.engines[0] == "scrapling"
            assert "scrapling" in cap.engines

    def test_duckduckgo_browser_matrix_source_registered_with_browser(self):
        reg = SiteRegistry()
        reg.load_builtin()

        cap = reg["duckduckgo"]

        assert cap.engines[0] == "scrapling"
        assert "scrapling" in cap.engines

    def test_arxiv_browser_structured_source_registered_with_browser_first(self):
        reg = SiteRegistry()
        reg.load_builtin()

        cap = reg["arxiv"]

        assert cap.engines[0] == "opencli"
        assert "opencli" in cap.engines
        assert "scrapling" in cap.engines


class TestLookupByDomain:
    def test_exact_domain(self):
        reg = SiteRegistry()
        reg.load_builtin()
        cap = reg.lookup_by_domain("bilibili.com")
        assert cap is not None
        assert cap.site_id == "bilibili"
        assert cap.display_name == "哔哩哔哩"

    def test_subdomain_match(self):
        reg = SiteRegistry()
        reg.load_builtin()
        cap = reg.lookup_by_domain("www.bilibili.com")
        assert cap is not None
        assert cap.site_id == "bilibili"

    def test_unknown_domain(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.lookup_by_domain("notasite.xyz") is None

    def test_case_insensitive(self):
        reg = SiteRegistry()
        reg.load_builtin()
        cap = reg.lookup_by_domain("ZHIHU.COM")
        assert cap is not None
        assert cap.site_id == "zhihu"


class TestLookupByUrl:
    def test_full_url(self):
        reg = SiteRegistry()
        reg.load_builtin()
        cap = reg.lookup_by_url("https://www.bilibili.com/video/BV123")
        assert cap is not None
        assert cap.site_id == "bilibili"

    def test_url_with_path(self):
        reg = SiteRegistry()
        reg.load_builtin()
        cap = reg.lookup_by_url("https://github.com/user/repo")
        assert cap is not None
        assert cap.site_id == "github"

    def test_unknown_url(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.lookup_by_url("https://random-site-xyz.com/page") is None


class TestGetSitesByCountry:
    def test_chinese_sites(self):
        reg = SiteRegistry()
        reg.load_builtin()
        cn_sites = reg.get_sites_by_country("cn")
        assert len(cn_sites) >= 15  # many Chinese sites
        for s in cn_sites:
            assert s.country == "cn"

    def test_global_sites(self):
        reg = SiteRegistry()
        reg.load_builtin()
        global_sites = reg.get_sites_by_country("global")
        assert len(global_sites) >= 10

    def test_nonexistent_country(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.get_sites_by_country("mars") == []


class TestGetSitesByContentType:
    def test_video_sites(self):
        reg = SiteRegistry()
        reg.load_builtin()
        video = reg.get_sites_by_content_type("video")
        ids = {s.site_id for s in video}
        assert "bilibili" in ids
        assert "youtube" in ids

    def test_code_sites(self):
        reg = SiteRegistry()
        reg.load_builtin()
        code = reg.get_sites_by_content_type("code")
        ids = {s.site_id for s in code}
        assert "github" in ids


class TestGetPreferredEngines:
    def test_known_site(self):
        reg = SiteRegistry()
        reg.load_builtin()
        engines = reg.get_preferred_engines("https://bilibili.com/video/123")
        assert len(engines) >= 1
        assert "opencli" in engines or "opencli" in engines

    def test_unknown_site_fallback(self):
        reg = SiteRegistry()
        reg.load_builtin()
        engines = reg.get_preferred_engines("https://unknown-site.xyz")
        assert engines == ["scrapling", "http"]


class TestSiteCapabilityFields:
    def test_site_capability_creation(self):
        cap = SiteCapability(
            site_id="test",
            display_name="Test Site",
            domains=["test.com"],
            engines=["scrapling"],
        )
        assert cap.site_id == "test"
        assert cap.auth_required is False
        assert cap.country == "global"
        assert cap.content_type == "article"

    def test_auth_fields(self):
        cap = SiteCapability(
            site_id="auth_site",
            display_name="Auth Site",
            domains=["auth.com"],
            engines=["opencli"],
            auth_required=True,
            auth_engine="opencli",
        )
        assert cap.auth_required is True
        assert cap.auth_engine == "opencli"


class TestSearchEngines:
    def test_get_search_engines(self):
        reg = SiteRegistry()
        reg.load_builtin()
        search = reg.get_search_engines()
        ids = {s.site_id for s in search}
        # Sites with 'search' command
        assert "google" in ids or "baidu" in ids


class TestSingleton:
    def test_singleton_pattern(self):
        inst1 = SiteRegistry.get_instance()
        inst2 = SiteRegistry.get_instance()
        assert inst1 is inst2

    def test_reset_creates_new(self):
        inst1 = SiteRegistry.get_instance()
        SiteRegistry.reset_instance()
        inst2 = SiteRegistry.get_instance()
        assert inst1 is not inst2


class TestContains:
    def test_contains_registered_site(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert "bilibili" in reg

    def test_not_contains_unknown(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert "nonexistent" not in reg


class TestNeedsAuth:
    def test_auth_required_site(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.needs_auth("https://weibo.com/timeline") is True

    def test_no_auth_site(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.needs_auth("https://github.com/user/repo") is False
