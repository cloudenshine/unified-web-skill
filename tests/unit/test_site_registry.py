"""Tests for app.discovery.site_registry — SiteRegistry and SiteCapability."""

import pytest
from app.discovery.site_registry import SiteRegistry, SiteCapability


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
        assert count >= 60, f"Expected 60+ sites, got {count}"

    def test_site_count_property(self):
        reg = SiteRegistry()
        reg.load_builtin()
        assert reg.site_count >= 60


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
        assert "bb-browser" in engines or "opencli" in engines

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
            engines=["bb-browser"],
            auth_required=True,
            auth_engine="bb-browser",
        )
        assert cap.auth_required is True
        assert cap.auth_engine == "bb-browser"


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
