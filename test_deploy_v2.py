#!/usr/bin/env python3
"""Deployment test v2 for unified-web-skill v3.0 — corrected API field names."""

import asyncio
import json
import time
import sys
import os
import traceback

os.environ.setdefault("BB_BROWSER_BIN", "bb-browser")
os.environ.setdefault("BB_BROWSER_ENABLED", "true")
os.environ.setdefault("OPENCLI_BIN", "opencli")
os.environ.setdefault("CLIBROWSER_ENABLED", "false")
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
        "detail": str(detail)[:300], "ms": round(duration_ms)
    })
    icon = "\u2705" if status == "PASS" else "\u274c" if status == "FAIL" else "\u26a0\ufe0f"
    d = str(detail)[:120]
    print(f"  {icon} [{tool}] {test_name}: {status} ({round(duration_ms)}ms) {d}")


async def test_1_engine_init():
    print("\n" + "=" * 60)
    print("TEST 1: Engine Initialization & Health")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    engine_classes = [
        ("opencli", OpenCLIEngine),
        ("bb-browser", BBBrowserEngine),
        ("scrapling", ScraplingEngine),
    ]

    for name, cls in engine_classes:
        t0 = time.time()
        try:
            eng = cls()
            mgr.register(eng)
            caps = [c.value for c in eng.capabilities]
            record("engine_init", f"{name}_register", "PASS",
                   f"caps={caps}", (time.time()-t0)*1000)
        except Exception as e:
            record("engine_init", f"{name}_register", "FAIL",
                   str(e), (time.time()-t0)*1000)

    # Health checks
    for name in list(mgr._engines.keys()):
        eng = mgr._engines[name]
        t0 = time.time()
        try:
            ok = await eng.health_check()
            s = "PASS" if ok else "WARN"
            record("health_check", f"{name}_health", s,
                   f"healthy={ok}", (time.time()-t0)*1000)
        except Exception as e:
            record("health_check", f"{name}_health", "FAIL",
                   str(e), (time.time()-t0)*1000)

    return mgr


async def test_2_engine_status_http():
    print("\n" + "=" * 60)
    print("TEST 2: engine_status via HTTP /health")
    print("=" * 60)

    import urllib.request
    t0 = time.time()
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=10)
        data = json.loads(resp.read())
        n = len(data.get("engines", []))
        record("engine_status", "http_health", "PASS",
               f"version={data.get('version')}, engines={n}: {data.get('engines')}", (time.time()-t0)*1000)
    except Exception as e:
        record("engine_status", "http_health", "FAIL", str(e), (time.time()-t0)*1000)


async def test_3_web_fetch():
    print("\n" + "=" * 60)
    print("TEST 3: web_fetch (FetchResult.text)")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    for cls in [BBBrowserEngine, OpenCLIEngine, ScraplingEngine]:
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
            # FetchResult uses .text, not .content
            content_len = len(result.text) if result and result.text else 0
            engine_used = result.engine if result else "none"
            ok_flag = result.ok if result else False
            if ok_flag and content_len > 0:
                record("web_fetch", label, "PASS",
                       f"engine={engine_used}, len={content_len}, ok={ok_flag}", (time.time()-t0)*1000)
            elif content_len > 0:
                record("web_fetch", label, "WARN",
                       f"engine={engine_used}, len={content_len}, ok={ok_flag}", (time.time()-t0)*1000)
            else:
                record("web_fetch", label, "WARN",
                       f"engine={engine_used}, empty text, ok={ok_flag}, err={result.error[:100] if result else 'no result'}",
                       (time.time()-t0)*1000)
        except Exception as e:
            record("web_fetch", label, "FAIL", str(e), (time.time()-t0)*1000)


async def test_4_ddgs_search():
    print("\n" + "=" * 60)
    print("TEST 4: DuckDuckGo Search (ddgs)")
    print("=" * 60)

    # Test ddgs directly first
    t0 = time.time()
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw = list(ddgs.text("Python asyncio tutorial", max_results=5))
        count = len(raw)
        urls = [r.get("href", r.get("link", "?")) for r in raw[:3]]
        record("ddgs_direct", "text_search", "PASS" if count > 0 else "WARN",
               f"results={count}, urls={urls}", (time.time()-t0)*1000)
    except Exception as e:
        record("ddgs_direct", "text_search", "FAIL", str(e), (time.time()-t0)*1000)


async def test_5_multi_source_discovery():
    print("\n" + "=" * 60)
    print("TEST 5: MultiSourceDiscovery")
    print("=" * 60)

    from app.discovery.multi_source import MultiSourceDiscovery
    from app.engines.manager import EngineManager
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.opencli import OpenCLIEngine

    mgr = EngineManager()
    for cls in [BBBrowserEngine, OpenCLIEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    disc = MultiSourceDiscovery(engine_manager=mgr)

    queries = [
        ("Python asyncio tutorial", "en"),
        ("AI最新技术趋势", "zh"),
    ]

    for query, lang in queries:
        t0 = time.time()
        try:
            search_results = await disc.discover(query, language=lang, max_sources=5)
            count = len(search_results)
            urls = [r.url for r in search_results[:3]] if search_results else []
            record("discovery", f"discover_{query[:15]}", "PASS" if count > 0 else "WARN",
                   f"found={count}, urls={urls}", (time.time()-t0)*1000)
        except Exception as e:
            record("discovery", f"discover_{query[:15]}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_6_intent_classifier():
    print("\n" + "=" * 60)
    print("TEST 6: IntentClassifier")
    print("=" * 60)

    from app.discovery.intent_classifier import IntentClassifier

    clf = IntentClassifier()
    test_cases = [
        ("Python异步编程教程", "informational"),
        ("今天的科技新闻", "news"),
        ("iPhone 16 价格对比", "transactional"),
        ("GitHub热门项目", "code"),
        ("如何使用Docker部署", "informational"),
    ]

    for query, expected in test_cases:
        t0 = time.time()
        try:
            intent = clf.classify(query)
            ok = intent.value == expected
            record("intent", f"classify_{query[:10]}", "PASS" if ok else "WARN",
                   f"got={intent.value}, expected={expected}", (time.time()-t0)*1000)
        except Exception as e:
            record("intent", f"classify_{query[:10]}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_7_site_registry():
    print("\n" + "=" * 60)
    print("TEST 7: SiteRegistry")
    print("=" * 60)

    from app.discovery.site_registry import SiteRegistry

    reg = SiteRegistry.get_instance()
    t0 = time.time()
    # Check how many sites are registered
    all_caps = reg._sites if hasattr(reg, "_sites") else []
    total = len(all_caps)
    record("site_registry", "load_registry", "PASS" if total > 0 else "WARN",
           f"total_sites={total}", (time.time()-t0)*1000)

    # Test lookups by domain
    test_domains = [
        "zhihu.com", "weibo.com", "github.com", "twitter.com",
        "reddit.com", "youtube.com", "bilibili.com", "arxiv.org",
    ]

    for domain in test_domains:
        t0 = time.time()
        try:
            entry = reg.lookup_by_domain(domain)
            if entry:
                pref = entry.preferred_engines if hasattr(entry, "preferred_engines") else "?"
                record("site_registry", f"lookup_{domain}", "PASS",
                       f"found, engines={pref}", (time.time()-t0)*1000)
            else:
                record("site_registry", f"lookup_{domain}", "WARN",
                       "not in registry", (time.time()-t0)*1000)
        except Exception as e:
            record("site_registry", f"lookup_{domain}", "FAIL", str(e), (time.time()-t0)*1000)


async def test_8_bb_browser_fetch():
    print("\n" + "=" * 60)
    print("TEST 8: bb-browser Engine Direct Tests")
    print("=" * 60)

    from app.engines.bb_browser import BBBrowserEngine

    bb = BBBrowserEngine()

    # Health check
    t0 = time.time()
    try:
        ok = await bb.health_check()
        record("bb-browser", "health_check", "PASS" if ok else "WARN",
               f"healthy={ok}", (time.time()-t0)*1000)
    except Exception as e:
        record("bb-browser", "health_check", "FAIL", str(e), (time.time()-t0)*1000)

    # Fetch example.com
    t0 = time.time()
    try:
        result = await bb.fetch("https://example.com")
        tlen = len(result.text) if result.text else 0
        record("bb-browser", "fetch_example", "PASS" if result.ok and tlen > 0 else "WARN",
               f"ok={result.ok}, text_len={tlen}, err={result.error[:80]}", (time.time()-t0)*1000)
    except Exception as e:
        record("bb-browser", "fetch_example", "FAIL", str(e), (time.time()-t0)*1000)

    # Search via baidu
    t0 = time.time()
    try:
        results = await bb.search("Python教程", max_results=3)
        count = len(results)
        record("bb-browser", "search_baidu", "PASS" if count > 0 else "WARN",
               f"results={count}", (time.time()-t0)*1000)
    except Exception as e:
        record("bb-browser", "search_baidu", "FAIL", str(e), (time.time()-t0)*1000)


async def test_9_opencli_engine():
    print("\n" + "=" * 60)
    print("TEST 9: OpenCLI Engine Direct Tests")
    print("=" * 60)

    from app.engines.opencli import OpenCLIEngine

    oc = OpenCLIEngine()

    # Health check
    t0 = time.time()
    try:
        ok = await oc.health_check()
        record("opencli", "health_check", "PASS" if ok else "WARN",
               f"healthy={ok}", (time.time()-t0)*1000)
    except Exception as e:
        record("opencli", "health_check", "FAIL", str(e), (time.time()-t0)*1000)

    # Fetch github.com
    t0 = time.time()
    try:
        result = await oc.fetch("https://github.com/trending")
        tlen = len(result.text) if result.text else 0
        record("opencli", "fetch_github", "PASS" if result.ok and tlen > 0 else "WARN",
               f"ok={result.ok}, text_len={tlen}, err={result.error[:80]}", (time.time()-t0)*1000)
    except Exception as e:
        record("opencli", "fetch_github", "FAIL", str(e), (time.time()-t0)*1000)

    # Search
    t0 = time.time()
    try:
        results = await oc.search("github trending repos", max_results=5)
        count = len(results)
        record("opencli", "search_github", "PASS" if count > 0 else "WARN",
               f"results={count}", (time.time()-t0)*1000)
    except Exception as e:
        record("opencli", "search_github", "FAIL", str(e), (time.time()-t0)*1000)


async def test_10_scrapling_engine():
    print("\n" + "=" * 60)
    print("TEST 10: Scrapling Engine")
    print("=" * 60)

    from app.engines.scrapling_engine import ScraplingEngine

    sc = ScraplingEngine()

    # Health check
    t0 = time.time()
    try:
        ok = await sc.health_check()
        record("scrapling", "health_check", "PASS" if ok else "WARN",
               f"healthy={ok}", (time.time()-t0)*1000)
    except Exception as e:
        record("scrapling", "health_check", "FAIL", str(e), (time.time()-t0)*1000)

    # Fetch
    t0 = time.time()
    try:
        result = await sc.fetch("https://example.com")
        tlen = len(result.text) if result.text else 0
        record("scrapling", "fetch_example", "PASS" if result.ok and tlen > 0 else "WARN",
               f"ok={result.ok}, text_len={tlen}", (time.time()-t0)*1000)
    except Exception as e:
        record("scrapling", "fetch_example", "FAIL", str(e), (time.time()-t0)*1000)


async def test_11_research_pipeline():
    print("\n" + "=" * 60)
    print("TEST 11: ResearchPipeline (full pipeline)")
    print("=" * 60)

    from app.pipeline.research import ResearchPipeline
    from app.models import ResearchTask
    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    for cls in [BBBrowserEngine, OpenCLIEngine, ScraplingEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    pipeline = ResearchPipeline(engine_manager=mgr)

    task = ResearchTask(
        query="What is Python asyncio",
        language="en",
        max_sources=5,
        max_pages=3,
    )

    t0 = time.time()
    try:
        result = await pipeline.run(task)
        # ResearchResult fields
        total = result.total if hasattr(result, "total") else 0
        success = result.success_count if hasattr(result, "success_count") else 0
        record("pipeline", "research_asyncio", "PASS" if total > 0 else "WARN",
               f"total={total}, success={success}", (time.time()-t0)*1000)
    except Exception as e:
        record("pipeline", "research_asyncio", "FAIL", str(e), (time.time()-t0)*1000)


async def test_12_cn_sites():
    print("\n" + "=" * 60)
    print("TEST 12: Chinese Site Coverage")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.opencli import OpenCLIEngine
    from app.engines.bb_browser import BBBrowserEngine
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    for cls in [BBBrowserEngine, OpenCLIEngine, ScraplingEngine]:
        try:
            mgr.register(cls())
        except:
            pass

    cn_sites = [
        ("https://www.zhihu.com/hot", "zhihu_hot"),
        ("https://www.bilibili.com", "bilibili_main"),
    ]

    for url, label in cn_sites:
        t0 = time.time()
        try:
            result = await mgr.fetch_with_fallback(url)
            tlen = len(result.text) if result and result.text else 0
            engine_used = result.engine if result else "none"
            ok = result.ok if result else False
            record("cn_sites", label, "PASS" if ok and tlen > 100 else "WARN",
                   f"engine={engine_used}, len={tlen}, ok={ok}", (time.time()-t0)*1000)
        except Exception as e:
            record("cn_sites", label, "FAIL", str(e), (time.time()-t0)*1000)


async def test_13_error_handling():
    print("\n" + "=" * 60)
    print("TEST 13: Error Handling & Edge Cases")
    print("=" * 60)

    from app.engines.manager import EngineManager
    from app.engines.scrapling_engine import ScraplingEngine

    mgr = EngineManager()
    try:
        mgr.register(ScraplingEngine())
    except:
        pass

    cases = [
        ("https://nonexistent-domain-xyz123456.com", "nonexistent_domain"),
        ("https://httpbin.org/status/404", "http_404"),
        ("not-a-url", "invalid_url"),
    ]

    for url, label in cases:
        t0 = time.time()
        try:
            result = await mgr.fetch_with_fallback(url)
            # Graceful handling = PASS (didn't crash)
            record("errors", label, "PASS",
                   f"ok={result.ok if result else '?'}, err={result.error[:80] if result else 'no result'}",
                   (time.time()-t0)*1000)
        except Exception as e:
            etype = type(e).__name__
            # Known error types = still graceful
            record("errors", label, "PASS" if etype in ("WebSkillError", "FetchError", "ValueError") else "WARN",
                   f"raised {etype}: {str(e)[:80]}", (time.time()-t0)*1000)


async def main():
    print("=" * 60)
    print("  UNIFIED-WEB-SKILL v3.0 — DEPLOYMENT TEST v2")
    print("  OpenClaw Integration Testing")
    print("=" * 60)

    tests = [
        test_1_engine_init,
        test_2_engine_status_http,
        test_3_web_fetch,
        test_4_ddgs_search,
        test_5_multi_source_discovery,
        test_6_intent_classifier,
        test_7_site_registry,
        test_8_bb_browser_fetch,
        test_9_opencli_engine,
        test_10_scrapling_engine,
        test_11_research_pipeline,
        test_12_cn_sites,
        test_13_error_handling,
    ]

    for test_fn in tests:
        try:
            await test_fn()
        except Exception as e:
            print(f"\n  SUITE ERROR in {test_fn.__name__}: {e}")
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
    print(f"  PASS:   {pass_count}")
    print(f"  WARN:   {warn_count}")
    print(f"  FAIL:   {fail_count}")
    pct = 100*pass_count/total if total else 0
    print(f"\n  Success Rate: {pass_count}/{total} ({pct:.1f}%)")

    # By tool
    print("\n  --- By Tool ---")
    tools_seen = []
    for r in results:
        if r["tool"] not in tools_seen:
            tools_seen.append(r["tool"])
    for tool in tools_seen:
        tr = [r for r in results if r["tool"] == tool]
        p = sum(1 for r in tr if r["status"] == "PASS")
        w = sum(1 for r in tr if r["status"] == "WARN")
        f = sum(1 for r in tr if r["status"] == "FAIL")
        total_t = len(tr)
        avg_ms = sum(r["ms"] for r in tr) / total_t if total_t else 0
        print(f"  {tool:20s}: {p}P / {w}W / {f}F  (avg {avg_ms:.0f}ms)")

    # Save results
    out_file = os.path.join(os.path.dirname(__file__), "test_results_v2.json")
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to: {out_file}")

    return pass_count, warn_count, fail_count, total


if __name__ == "__main__":
    asyncio.run(main())
