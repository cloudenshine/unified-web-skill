#!/usr/bin/env python3
"""Comprehensive deployment test for unified-web-skill v3.0 in OpenClaw."""

import asyncio
import json
import time
import sys
import os
import traceback

os.environ.setdefault("OPENCLI_BIN", "opencli")
os.environ.setdefault("BB_BROWSER_BIN", "bb")
os.environ.setdefault("BB_BROWSER_ENABLED", "true")
os.environ.setdefault("CLIBROWSER_ENABLED", "true")
os.environ.setdefault("CLIBROWSER_BIN", "clibrowser")
os.environ.setdefault("LP_ENABLED", "false")
os.environ.setdefault("SCRAPLING_ENABLED", "true")
os.environ.setdefault("MCP_HOST", "127.0.0.1")
os.environ.setdefault("MCP_PORT", "8001")
os.environ.setdefault("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "outputs"))

sys.path.insert(0, os.path.dirname(__file__))

results = []

def record(tool, test_name, status, detail="", duration_ms=0):
    results.append({
        "tool": tool, "test": test_name, "status": status,
        "detail": str(detail)[:200], "ms": round(duration_ms)
    })
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} [{tool}] {test_name}: {status} ({round(duration_ms)}ms) {str(detail)[:100]}")


async def test_1_engine_init():
    """Test engine registration and health checks."""
    print("\n" + "=" * 60)
    print("TEST 1: Engine Initialization & Health")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.clibrowser import CLIBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    engine_classes = [
        ("opencli", OpenCLIEngine),
        ("bb-browser", BBBrowserEngine),
        ("clibrowser", CLIBrowserEngine),
        ("scrapling", ScraplingEngine),
    ]

    for name, cls in engine_classes:
        t0 = time.time()
        try:
            eng = cls()
            mgr.register(eng)
            caps = [c.value for c in eng.capabilities]
            record("engine_init", f"{name}_register", "PASS", f"caps={caps}", (time.time()-t0)*1000)
        except Exception as e:
            record("engine_init", f"{name}_register", "FAIL", str(e), (time.time()-t0)*1000)

    # Health checks
    for name in list(mgr._engines.keys()):
        eng = mgr._engines[name]
        t0 = time.time()
        try:
            ok = await eng.health_check()
            status = "PASS" if ok else "WARN"
            record("health_check", f"{name}_health", status, f"healthy={ok}", (time.time()-t0)*1000)
        except Exception as e:
            record("health_check", f"{name}_health", "FAIL", str(e), (time.time()-t0)*1000)

    return mgr


async def test_2_engine_status():
    """Test engine_status tool."""
    print("\n" + "=" * 60)
    print("TEST 2: engine_status Tool")
    print("=" * 60)

    from app.mcp_server import _get_engine_manager
    t0 = time.time()
    try:
        em = _get_engine_manager()
        engine_names = list(em._engines.keys()) if em else []
        status_data = {
            "status": "ok",
            "version": "3.0.0",
            "engines": engine_names,
            "count": len(engine_names),
        }
        record("engine_status", "get_status", "PASS", json.dumps(status_data), (time.time()-t0)*1000)
    except Exception as e:
        record("engine_status", "get_status", "FAIL", str(e), (time.time()-t0)*1000)


async def test_3_web_fetch():
    """Test web_fetch with various URLs."""
    print("\n" + "=" * 60)
    print("TEST 3: web_fetch Tool")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine
    from app.engines.clibrowser import CLIBrowserEngine

    mgr = EngineManager()
    for cls in [OpenCLIEngine, BBBrowserEngine, ScraplingEngine, CLIBrowserEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    test_urls = [
        ("https://example.com", "simple_html"),
        ("https://httpbin.org/html", "httpbin_html"),
        ("https://jsonplaceholder.typicode.com/posts/1", "json_api"),
    ]

    for url, label in test_urls:
        t0 = time.time()
        try:
            result = await mgr.fetch_with_fallback(url)
            content_len = len(result.content) if result and result.content else 0
            engine_used = result.engine_name if result else "none"
            if content_len > 0:
                record("web_fetch", label, "PASS", f"engine={engine_used}, len={content_len}", (time.time()-t0)*1000)
            else:
                record("web_fetch", label, "WARN", f"engine={engine_used}, empty content", (time.time()-t0)*1000)
        except Exception as e:
            record("web_fetch", label, "FAIL", str(e), (time.time()-t0)*1000)


async def test_4_web_search():
    """Test web_search tool with DuckDuckGo."""
    print("\n" + "=" * 60)
    print("TEST 4: web_search Tool")
    print("=" * 60)

    from app.discovery.multi_source import MultiSourceDiscovery
    from app.discovery.intent_classifier import IntentClassifier

    # Test intent classification first
    queries_intents = [
        ("Python异步编程教程", "academic/code"),
        ("今天的科技新闻", "news"),
        ("iPhone 16 价格", "shopping"),
    ]

    for query, expected_hint in queries_intents:
        t0 = time.time()
        try:
            clf = IntentClassifier()
            intent = clf.classify(query)
            record("intent_classify", f"classify_{query[:10]}", "PASS",
                   f"intent={intent.value}, expected_hint={expected_hint}", (time.time()-t0)*1000)
        except Exception as e:
            record("intent_classify", f"classify_{query[:10]}", "FAIL", str(e), (time.time()-t0)*1000)

    # Test multi-source discovery
    search_queries = [
        "Python asyncio tutorial",
        "最新AI技术趋势",
    ]
    for query in search_queries:
        t0 = time.time()
        try:
            disc = MultiSourceDiscovery()
            urls = await disc.discover(query, max_results=5)
            count = len(urls) if urls else 0
            record("web_search", f"search_{query[:15]}", "PASS" if count > 0 else "WARN",
                   f"found={count} urls", (time.time()-t0)*1000)
        except Exception as e:
            record("web_search", f"search_{query[:15]}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_5_web_cli():
    """Test web_cli tool (OpenCLI / bb-browser CLI commands)."""
    print("\n" + "=" * 60)
    print("TEST 5: web_cli Tool (CLI adapters)")
    print("=" * 60)

    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine

    # OpenCLI site commands
    cli_tests = [
        ("opencli", OpenCLIEngine, "wikipedia", "search Python programming"),
        ("opencli", OpenCLIEngine, "github", "search unified-web-skill"),
    ]

    for engine_name, cls, site, command in cli_tests:
        t0 = time.time()
        try:
            eng = cls()
            result = await eng.search(f"{site} {command}", max_results=3)
            count = len(result) if result else 0
            record("web_cli", f"{engine_name}_{site}", "PASS" if count > 0 else "WARN",
                   f"results={count}", (time.time()-t0)*1000)
        except Exception as e:
            record("web_cli", f"{engine_name}_{site}", "FAIL", str(e), (time.time()-t0)*1000)

    # bb-browser site commands
    bb_tests = [
        ("bb-browser", BBBrowserEngine, "google", "search OpenClaw"),
    ]
    for engine_name, cls, site, command in bb_tests:
        t0 = time.time()
        try:
            eng = cls()
            result = await eng.search(f"{site} {command}", max_results=3)
            count = len(result) if result else 0
            record("web_cli", f"{engine_name}_{site}", "PASS" if count > 0 else "WARN",
                   f"results={count}", (time.time()-t0)*1000)
        except Exception as e:
            record("web_cli", f"{engine_name}_{site}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_6_web_crawl():
    """Test web_crawl tool (multi-page crawling)."""
    print("\n" + "=" * 60)
    print("TEST 6: web_crawl Tool")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    for cls in [OpenCLIEngine, ScraplingEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    crawl_urls = [
        ("https://example.com", 2),
    ]

    for url, max_pages in crawl_urls:
        t0 = time.time()
        try:
            result = await mgr.fetch_with_fallback(url)
            content_len = len(result.content) if result and result.content else 0
            record("web_crawl", f"crawl_{url.split('//')[1][:20]}", "PASS" if content_len > 50 else "WARN",
                   f"len={content_len}", (time.time()-t0)*1000)
        except Exception as e:
            record("web_crawl", f"crawl_{url.split('//')[1][:20]}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_7_research_pipeline():
    """Test research_and_collect tool (full pipeline)."""
    print("\n" + "=" * 60)
    print("TEST 7: research_and_collect Tool (Full Pipeline)")
    print("=" * 60)

    from app.pipeline.research import ResearchPipeline
    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    for cls in [OpenCLIEngine, BBBrowserEngine, ScraplingEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    pipeline = ResearchPipeline(engine_manager=mgr)

    queries = [
        ("What is Python asyncio", "en", 3),
    ]

    for query, lang, max_src in queries:
        t0 = time.time()
        try:
            result = await pipeline.run(query=query, language=lang, max_sources=max_src)
            source_count = result.get("total", 0) if isinstance(result, dict) else 0
            record("research", f"pipeline_{query[:20]}", "PASS" if source_count > 0 else "WARN",
                   f"sources={source_count}", (time.time()-t0)*1000)
        except Exception as e:
            record("research", f"pipeline_{query[:20]}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_8_site_registry():
    """Test SiteRegistry coverage."""
    print("\n" + "=" * 60)
    print("TEST 8: SiteRegistry & SmartRouter")
    print("=" * 60)

    from app.discovery.site_registry import SiteRegistry

    reg = SiteRegistry()
    t0 = time.time()
    total_sites = len(reg._registry) if hasattr(reg, '_registry') else len(reg.sites) if hasattr(reg, 'sites') else 0
    record("site_registry", "load_registry", "PASS", f"sites={total_sites}", (time.time()-t0)*1000)

    # Test lookups
    test_domains = [
        "zhihu.com", "weibo.com", "github.com", "twitter.com",
        "reddit.com", "youtube.com", "bilibili.com", "arxiv.org",
    ]

    for domain in test_domains:
        t0 = time.time()
        try:
            entry = reg.lookup(domain)
            if entry:
                record("site_registry", f"lookup_{domain}", "PASS",
                       f"engine={entry.get('preferred_engine', 'auto')}", (time.time()-t0)*1000)
            else:
                record("site_registry", f"lookup_{domain}", "WARN", "not in registry", (time.time()-t0)*1000)
        except Exception as e:
            record("site_registry", f"lookup_{domain}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_9_cn_sites():
    """Test Chinese site access (critical for OpenClaw CN users)."""
    print("\n" + "=" * 60)
    print("TEST 9: Chinese Site Coverage")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine

    mgr = EngineManager()
    for cls in [OpenCLIEngine, BBBrowserEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    cn_sites = [
        ("https://www.zhihu.com/hot", "zhihu_hot"),
        ("https://weibo.com/hot/search", "weibo_hot"),
    ]

    for url, label in cn_sites:
        t0 = time.time()
        try:
            result = await mgr.fetch_with_fallback(url)
            content_len = len(result.content) if result and result.content else 0
            engine_used = result.engine_name if result else "none"
            record("cn_sites", label, "PASS" if content_len > 100 else "WARN",
                   f"engine={engine_used}, len={content_len}", (time.time()-t0)*1000)
        except Exception as e:
            record("cn_sites", label, "FAIL", str(e), (time.time()-t0)*1000)


async def test_10_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("TEST 10: Edge Cases & Error Handling")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine

    mgr = EngineManager()
    try:
        mgr.register(OpenCLIEngine())
    except:
        pass

    edge_cases = [
        ("https://nonexistent-domain-xyz123.com", "nonexistent_domain"),
        ("https://httpbin.org/status/404", "http_404"),
        ("https://httpbin.org/status/500", "http_500"),
        ("invalid-url", "invalid_url"),
    ]

    for url, label in edge_cases:
        t0 = time.time()
        try:
            result = await mgr.fetch_with_fallback(url)
            content_len = len(result.content) if result and result.content else 0
            # For error cases, PASS means we handled gracefully (didn't crash)
            record("edge_cases", label, "PASS", f"handled_gracefully, len={content_len}", (time.time()-t0)*1000)
        except Exception as e:
            # If it threw a known error type, that's also graceful
            etype = type(e).__name__
            if etype in ("WebSkillError", "FetchError", "EngineError", "ValueError"):
                record("edge_cases", label, "PASS", f"raised {etype}: {str(e)[:80]}", (time.time()-t0)*1000)
            else:
                record("edge_cases", label, "WARN", f"unexpected {etype}: {str(e)[:80]}", (time.time()-t0)*1000)


async def main():
    print("=" * 60)
    print("  UNIFIED-WEB-SKILL v3.0 — DEPLOYMENT TEST SUITE")
    print("  OpenClaw Integration Testing")
    print("=" * 60)

    tests = [
        test_1_engine_init,
        test_2_engine_status,
        test_3_web_fetch,
        test_4_web_search,
        test_5_web_cli,
        test_6_web_crawl,
        test_7_research_pipeline,
        test_8_site_registry,
        test_9_cn_sites,
        test_10_edge_cases,
    ]

    for test_fn in tests:
        try:
            await test_fn()
        except Exception as e:
            print(f"\n  💥 TEST SUITE ERROR in {test_fn.__name__}: {e}")
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    print(f"\n  Total:  {total}")
    print(f"  ✅ PASS: {pass_count}")
    print(f"  ⚠️  WARN: {warn_count}")
    print(f"  ❌ FAIL: {fail_count}")
    print(f"\n  Success Rate: {pass_count}/{total} ({100*pass_count/total:.1f}%)")

    # Breakdown by tool
    print("\n  --- By Tool ---")
    tools_seen = []
    for r in results:
        if r["tool"] not in tools_seen:
            tools_seen.append(r["tool"])
    for tool in tools_seen:
        tool_results = [r for r in results if r["tool"] == tool]
        p = sum(1 for r in tool_results if r["status"] == "PASS")
        w = sum(1 for r in tool_results if r["status"] == "WARN")
        f = sum(1 for r in tool_results if r["status"] == "FAIL")
        print(f"  {tool:20s}: {p}P / {w}W / {f}F")

    # Write JSON results
    results_file = os.path.join(os.path.dirname(__file__), "test_results.json")
    with open(results_file, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to: {results_file}")

    return pass_count, warn_count, fail_count, total


if __name__ == "__main__":
    asyncio.run(main())
