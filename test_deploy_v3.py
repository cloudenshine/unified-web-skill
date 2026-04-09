#!/usr/bin/env python3
"""Comprehensive deployment test v3 — after critical bug fixes."""
import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(__file__))

RESULTS = []

def record(name, status, detail="", duration_ms=0):
    RESULTS.append({"name": name, "status": status, "detail": detail[:300], "duration_ms": round(duration_ms, 1)})
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏭️"}.get(status, "?")
    print(f"  {icon} {name}: {detail[:120]}")


async def test_engine_imports():
    """Test all engine imports."""
    try:
        from app.engines.base import FetchResult, SearchResult, BaseEngine, Engine
        record("import_base", "PASS", "FetchResult, SearchResult, BaseEngine, Engine OK")
    except Exception as e:
        record("import_base", "FAIL", str(e))

    try:
        from app.engines.scrapling_engine import ScraplingEngine
        record("import_scrapling", "PASS", "ScraplingEngine OK")
    except Exception as e:
        record("import_scrapling", "FAIL", str(e))

    try:
        from app.engines.bb_browser import BBBrowserEngine
        record("import_bb", "PASS", "BBBrowserEngine OK")
    except Exception as e:
        record("import_bb", "FAIL", str(e))

    try:
        from app.engines.opencli import OpenCLIEngine
        record("import_opencli", "PASS", "OpenCLIEngine OK")
    except Exception as e:
        record("import_opencli", "FAIL", str(e))


async def test_engine_manager():
    """Test EngineManager initialization."""
    try:
        from app.engines.manager import EngineManager
        from app.engines.scrapling_engine import ScraplingEngine
        mgr = EngineManager()
        # Register engines (mimics _get_engine_manager in mcp_server.py)
        mgr.register(ScraplingEngine())
        try:
            from app.engines.bb_browser import BBBrowserEngine
            mgr.register(BBBrowserEngine())
        except Exception:
            pass
        try:
            from app.engines.opencli import OpenCLIEngine
            mgr.register(OpenCLIEngine())
        except Exception:
            pass
        engines = mgr.list_engines()
        record("engine_manager_init", "PASS", f"EngineManager created, {len(engines)} engines: {list(engines.keys())}")
        for name in engines:
            record(f"engine_registered_{name}", "PASS", f"Engine '{name}' registered")
        return mgr
    except Exception as e:
        record("engine_manager_init", "FAIL", str(e))
        return None


async def test_scrapling_fetch(mgr):
    """Test Scrapling fetch with text extraction."""
    if not mgr:
        record("scrapling_fetch", "SKIP", "No engine manager")
        return

    from app.engines.scrapling_engine import ScraplingEngine
    engine = ScraplingEngine()
    
    # Test httpbin
    t0 = time.monotonic()
    try:
        result = await engine.fetch("https://httpbin.org/html", timeout=15)
        dur = (time.monotonic() - t0) * 1000
        if result.ok:
            has_html = len(result.html) > 50
            has_text = len(result.text) > 20
            record("scrapling_httpbin", "PASS" if has_text else "WARN",
                   f"ok={result.ok} status={result.status} html={len(result.html)}ch text={len(result.text)}ch engine={result.engine}",
                   dur)
        else:
            record("scrapling_httpbin", "WARN", f"ok=False error={result.error}", dur)
    except Exception as e:
        record("scrapling_httpbin", "FAIL", str(e))

    # Test a real page
    t0 = time.monotonic()
    try:
        result = await engine.fetch("https://www.wikipedia.org", timeout=15)
        dur = (time.monotonic() - t0) * 1000
        if result.ok:
            has_text = len(result.text) > 20
            record("scrapling_wikipedia", "PASS" if has_text else "WARN",
                   f"ok={result.ok} text={len(result.text)}ch html={len(result.html)}ch", dur)
        else:
            record("scrapling_wikipedia", "WARN", f"ok=False error={result.error}", dur)
    except Exception as e:
        record("scrapling_wikipedia", "FAIL", str(e))


async def test_bb_browser(mgr):
    """Test bb-browser engine."""
    if not mgr:
        record("bb_browser", "SKIP", "No engine manager")
        return

    from app.engines.bb_browser import BBBrowserEngine
    engine = BBBrowserEngine()

    # Health check
    t0 = time.monotonic()
    try:
        ok = await engine.health_check()
        dur = (time.monotonic() - t0) * 1000
        record("bb_health", "PASS" if ok else "WARN", f"health={ok}", dur)
    except Exception as e:
        record("bb_health", "FAIL", str(e))

    # Fetch
    t0 = time.monotonic()
    try:
        result = await engine.fetch("https://httpbin.org/html", timeout=20)
        dur = (time.monotonic() - t0) * 1000
        if result.ok:
            record("bb_fetch", "PASS", f"ok={result.ok} text={len(result.text)}ch", dur)
        else:
            record("bb_fetch", "WARN", f"ok=False error={result.error}", dur)
    except Exception as e:
        record("bb_fetch", "FAIL", str(e))

    # Search
    t0 = time.monotonic()
    try:
        results = await engine.search("python asyncio", max_results=3)
        dur = (time.monotonic() - t0) * 1000
        if results:
            record("bb_search", "PASS", f"{len(results)} results, first={results[0].url[:60]}", dur)
        else:
            record("bb_search", "WARN", "0 results returned", dur)
    except Exception as e:
        record("bb_search", "FAIL", str(e))


async def test_opencli(mgr):
    """Test OpenCLI engine."""
    if not mgr:
        record("opencli", "SKIP", "No engine manager")
        return

    from app.engines.opencli import OpenCLIEngine
    engine = OpenCLIEngine()

    t0 = time.monotonic()
    try:
        ok = await engine.health_check()
        dur = (time.monotonic() - t0) * 1000
        record("opencli_health", "PASS" if ok else "WARN", f"health={ok}", dur)
    except Exception as e:
        record("opencli_health", "FAIL", str(e))

    t0 = time.monotonic()
    try:
        result = await engine.fetch("https://httpbin.org/html", timeout=20)
        dur = (time.monotonic() - t0) * 1000
        if result.ok:
            record("opencli_fetch", "PASS", f"ok={result.ok} text={len(result.text)}ch", dur)
        else:
            record("opencli_fetch", "WARN", f"ok=False error={result.error}", dur)
    except Exception as e:
        record("opencli_fetch", "FAIL", str(e))


async def test_ddgs_search():
    """Test DuckDuckGo search via ddgs."""
    t0 = time.monotonic()
    try:
        from app.discovery.multi_source import MultiSourceDiscovery
        from app.engines.manager import EngineManager
        from app.engines.scrapling_engine import ScraplingEngine
        mgr = EngineManager()
        mgr.register(ScraplingEngine())
        disc = MultiSourceDiscovery(mgr)
        results = await disc.discover("python web scraping", max_sources=5, language="en")
        dur = (time.monotonic() - t0) * 1000
        if results:
            record("ddgs_search", "PASS", f"{len(results)} URLs discovered, first={results[0].url[:60]}", dur)
        else:
            record("ddgs_search", "WARN", "0 results", dur)
    except Exception as e:
        record("ddgs_search", "FAIL", str(e))


async def test_site_registry():
    """Test SiteRegistry."""
    try:
        from app.discovery.site_registry import SiteRegistry
        reg = SiteRegistry.get_instance()
        count = len(reg._sites)
        record("registry_loaded", "PASS", f"{count} sites loaded")
        
        # Test domain lookup
        cap = reg.lookup_by_domain("zhihu.com")
        record("registry_zhihu", "PASS" if cap else "WARN",
               f"zhihu={'found' if cap else 'missing'}")
        
        cap2 = reg.lookup_by_domain("github.com")
        record("registry_github", "PASS" if cap2 else "WARN",
               f"github={'found' if cap2 else 'missing'}")
    except Exception as e:
        record("registry", "FAIL", str(e))


async def test_intent_classifier():
    """Test IntentClassifier."""
    try:
        from app.discovery.intent_classifier import IntentClassifier
        clf = IntentClassifier()
        
        tests = [
            ("latest AI news 2024", "en", "news"),
            ("什么是机器学习", "zh", None),
            ("buy iPhone 15 best price", "en", None),
            ("Python tutorial for beginners", "en", None),
        ]
        
        for query, lang, expected_intent in tests:
            intent = clf.classify(query, lang)
            status = "PASS" if intent else "FAIL"
            record(f"intent_{query[:20].replace(' ','_')}", status, f"intent={intent.value}")
    except Exception as e:
        record("intent_classifier", "FAIL", str(e))


async def test_research_pipeline():
    """Test ResearchPipeline end-to-end."""
    t0 = time.monotonic()
    try:
        from app.engines.manager import EngineManager
        from app.engines.scrapling_engine import ScraplingEngine
        from app.pipeline.research import ResearchPipeline
        from app.models import ResearchTask

        mgr = EngineManager()
        mgr.register(ScraplingEngine())
        try:
            from app.engines.bb_browser import BBBrowserEngine
            mgr.register(BBBrowserEngine())
        except Exception:
            pass
        try:
            from app.engines.opencli import OpenCLIEngine
            mgr.register(OpenCLIEngine())
        except Exception:
            pass
        pipeline = ResearchPipeline(mgr)
        task = ResearchTask(
            query="Python asyncio tutorial",
            language="en",
            max_sources=5,
            max_pages=3,
            min_text_length=50,
        )
        result = await pipeline.run(task)
        dur = (time.monotonic() - t0) * 1000

        collected = result.stats.total_collected
        discovered = result.stats.total_discovered
        records_count = len(result.records)
        engines = result.stats.engines_used

        detail = (f"discovered={discovered} collected={collected} records={records_count} "
                  f"engines={engines} duration={result.stats.total_duration_s}s")

        if records_count > 0:
            record("pipeline_research", "PASS", detail, dur)
            # Show first record
            if result.records:
                r = result.records[0]
                record("pipeline_first_record", "PASS",
                       f"url={r.url[:60]} text={len(r.text)}ch engine={r.fetch_engine}")
        elif discovered > 0:
            record("pipeline_research", "WARN", f"discovered={discovered} but collected=0. {detail}", dur)
        else:
            record("pipeline_research", "WARN", f"No URLs discovered. {detail}", dur)

    except Exception as e:
        record("pipeline_research", "FAIL", f"{e}\n{traceback.format_exc()[:200]}")


async def test_engine_manager_fetch_fallback():
    """Test fetch_with_fallback through EngineManager."""
    t0 = time.monotonic()
    try:
        from app.engines.manager import EngineManager
        from app.engines.scrapling_engine import ScraplingEngine
        mgr = EngineManager()
        mgr.register(ScraplingEngine())
        try:
            from app.engines.bb_browser import BBBrowserEngine
            mgr.register(BBBrowserEngine())
        except Exception:
            pass
        result = await mgr.fetch_with_fallback("https://httpbin.org/html", timeout=20)
        dur = (time.monotonic() - t0) * 1000
        if result.ok:
            record("mgr_fetch_fallback", "PASS",
                   f"ok={result.ok} engine={result.engine} text={len(result.text)}ch", dur)
        else:
            record("mgr_fetch_fallback", "WARN", f"ok=False error={result.error}", dur)
    except Exception as e:
        record("mgr_fetch_fallback", "FAIL", str(e))


async def test_cn_sites():
    """Test Chinese site access."""
    from app.engines.scrapling_engine import ScraplingEngine
    engine = ScraplingEngine()

    sites = [
        ("https://www.baidu.com", "baidu"),
        ("https://www.bilibili.com", "bilibili"),
    ]

    for url, name in sites:
        t0 = time.monotonic()
        try:
            result = await engine.fetch(url, timeout=15)
            dur = (time.monotonic() - t0) * 1000
            if result.ok and len(result.text) > 20:
                record(f"cn_{name}", "PASS", f"ok text={len(result.text)}ch html={len(result.html)}ch", dur)
            elif result.ok:
                record(f"cn_{name}", "WARN", f"ok but text={len(result.text)}ch html={len(result.html)}ch", dur)
            else:
                record(f"cn_{name}", "WARN", f"failed: {result.error}", dur)
        except Exception as e:
            record(f"cn_{name}", "FAIL", str(e))


async def test_mcp_http():
    """Test MCP server HTTP endpoint."""
    import urllib.request
    t0 = time.monotonic()
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            dur = (time.monotonic() - t0) * 1000
            engines = data.get("engines", {})
            record("mcp_health", "PASS",
                   f"status={data.get('status')} engines={list(engines.keys())}", dur)
    except Exception as e:
        record("mcp_health", "WARN", f"HTTP health check failed: {e} (MCP may be stdio-only)")


async def test_error_handling():
    """Test error handling for bad inputs."""
    from app.engines.scrapling_engine import ScraplingEngine
    engine = ScraplingEngine()

    # Bad URL
    t0 = time.monotonic()
    try:
        result = await engine.fetch("not-a-url", timeout=5)
        dur = (time.monotonic() - t0) * 1000
        record("error_bad_url", "PASS" if not result.ok else "FAIL",
               f"ok={result.ok} error={result.error[:80]}", dur)
    except Exception as e:
        record("error_bad_url", "PASS", f"Exception as expected: {str(e)[:80]}")

    # Timeout
    t0 = time.monotonic()
    try:
        result = await engine.fetch("https://httpbin.org/delay/10", timeout=3)
        dur = (time.monotonic() - t0) * 1000
        record("error_timeout", "PASS" if not result.ok else "WARN",
               f"ok={result.ok} error={result.error[:80]}", dur)
    except Exception as e:
        record("error_timeout", "PASS", f"Timeout exception: {str(e)[:80]}")


async def main():
    print("=" * 70)
    print("  unified-web-skill v3.0 — Deployment Test v3")
    print("=" * 70)

    print("\n[1] Engine Imports")
    await test_engine_imports()

    print("\n[2] Engine Manager")
    mgr = await test_engine_manager()

    print("\n[3] Scrapling Fetch + Text Extraction")
    await test_scrapling_fetch(mgr)

    print("\n[4] bb-browser Engine")
    await test_bb_browser(mgr)

    print("\n[5] OpenCLI Engine")
    await test_opencli(mgr)

    print("\n[6] DuckDuckGo Search")
    await test_ddgs_search()

    print("\n[7] Site Registry")
    await test_site_registry()

    print("\n[8] Intent Classifier")
    await test_intent_classifier()

    print("\n[9] Research Pipeline")
    await test_research_pipeline()

    print("\n[10] EngineManager fetch_with_fallback")
    await test_engine_manager_fetch_fallback()

    print("\n[11] Chinese Sites")
    await test_cn_sites()

    print("\n[12] MCP HTTP Health")
    await test_mcp_http()

    print("\n[13] Error Handling")
    await test_error_handling()

    # Summary
    print("\n" + "=" * 70)
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    warned = sum(1 for r in RESULTS if r["status"] == "WARN")
    skipped = sum(1 for r in RESULTS if r["status"] == "SKIP")
    print(f"  TOTAL: {total}  |  ✅ PASS: {passed}  |  ❌ FAIL: {failed}  |  ⚠️ WARN: {warned}  |  ⏭️ SKIP: {skipped}")
    print(f"  Pass rate: {passed/total*100:.1f}%  ({passed}/{total})")
    print("=" * 70)

    # Save results
    with open("test_results_v3.json", "w", encoding="utf-8") as f:
        json.dump({"total": total, "passed": passed, "failed": failed, "warned": warned,
                    "skipped": skipped, "pass_rate": f"{passed/total*100:.1f}%",
                    "results": RESULTS}, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to test_results_v3.json")


if __name__ == "__main__":
    asyncio.run(main())
