"""
unified-web-skill v2 — Ring-based MCP Server
=============================================

Architecture (inner to outer):
  Ring 0: httpx HTTP fetch — always available, zero binary deps
  Ring 1: Playwright browser — available if installed + browsers
  Ring 2: bb-browser/opencli CLI — available if binaries found (full paths)
  Ring 3: Research pipeline — builds on R0+R1

Tools:
  fetch       — Fetch any URL (auto ring selection)
  search      — Web search (DuckDuckGo/Bing, no API key)
  browse      — JS-capable browser fetch (Ring 1)
  interact    — Browser interaction: click, fill, scroll, screenshot
  site        — Structured site commands (Ring 2: bb-browser/opencli)
  crawl       — BFS crawl from seed URL
  research    — Full multi-source research pipeline
  status      — Capability status report
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
_log = logging.getLogger("web-skill-v2")

# ── MCP import ─────────────────────────────────────────────────────────────
try:
    from mcp.server.fastmcp import FastMCP, Context
    _HAS_MCP = True
except ImportError:
    _log.error("mcp package not installed — run: pip install mcp")
    _HAS_MCP = False
    Context = None  # type: ignore

if not _HAS_MCP:
    sys.exit(1)

# ── Ring imports ───────────────────────────────────────────────────────────
from core.probe import CAPS
from core.rings import r0_http, r1_browser, r2_cli, r3_pipeline
from core import storage

_log.info(
    "Capabilities: R0=%s R1=%s R2=%s R3=%s | bb-browser=%s opencli=%s",
    CAPS.ring0, CAPS.ring1, CAPS.ring2, CAPS.ring3,
    CAPS.bb_browser_path or "not found",
    CAPS.opencli_path or "not found",
)

# ── MCP server ─────────────────────────────────────────────────────────────
_MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
_MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))  # 8001 to avoid conflict with v1
mcp = FastMCP("unified-web-skill-v2", host=_MCP_HOST, port=_MCP_PORT)


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 1: fetch — Universal URL fetch (R0 + R1 fallback)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def fetch(
    url: str,
    mode: str = "auto",
    timeout: int = 20,
    screenshot: bool = False,
    extra_headers: str = "",
) -> dict:
    """Fetch any URL and return title, text content, and optionally HTML.

    Args:
        url: Target URL. Supports http, https. Any website, no restrictions.
        mode: auto | http | browser.
              auto = try http first, use browser for JS-heavy sites;
              http = Ring 0 only (fast, low footprint);
              browser = Ring 1 Playwright (JS rendering, bypasses some bot checks).
        timeout: Request timeout in seconds (default 20).
        screenshot: If True and mode=browser, include base64 JPEG screenshot.
        extra_headers: JSON string of additional request headers.

    Returns:
        {ok, url, title, text, html, engine, duration_ms, error}
    """
    t0 = time.perf_counter()
    hdrs: dict = {}
    if extra_headers:
        try:
            hdrs = json.loads(extra_headers)
        except Exception:
            pass

    _log.info("fetch: %s mode=%s", url, mode)

    # Determine JS-heavy heuristic
    js_domains = ["bilibili", "zhihu", "xiaohongshu", "douyin", "weibo",
                  "twitter", "x.com", "instagram", "facebook", "tiktok",
                  "notion.so", "figma.com"]
    is_js_heavy = any(d in url for d in js_domains)

    use_browser = (
        mode == "browser" or
        (mode == "auto" and is_js_heavy and CAPS.ring1)
    )

    if use_browser and CAPS.ring1:
        r = await r1_browser.fetch(url, timeout=timeout, screenshot=screenshot,
                                   extra_headers=hdrs or None)
        if r.ok:
            return {**r.to_dict(), "engine": "r1_browser", "duration_ms": _ms(t0)}
        # Fallback to R0
        _log.info("Browser fetch failed (%s), falling back to HTTP", r.error)

    r = await r0_http.fetch(url, timeout=timeout, headers=hdrs or None)
    return {**r.to_dict(), "duration_ms": _ms(t0)}


# ══════════════════════════════════════════════════════════════════════════════
# Tool 2: search — Web search (DuckDuckGo/Bing, no API key)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def search(
    query: str,
    max_results: int = 10,
    language: str = "zh",
) -> dict:
    """Search the web and return a list of results with URL, title, and snippet.

    Args:
        query: Search query. Supports any language, operators (site:, filetype:, etc).
        max_results: Maximum results to return (default 10, max 30).
        language: zh (Chinese) or en (English). Affects search region and ranking.

    Returns:
        {ok, results: [{url, title, snippet, rank, source}], total, duration_ms}
    """
    t0 = time.perf_counter()
    _log.info("search: %r lang=%s", query, language)
    max_results = min(max_results, 30)
    results = await r0_http.search(query, max_results=max_results, language=language)
    return {
        "ok": True,
        "results": [r.to_dict() for r in results],
        "total": len(results),
        "duration_ms": _ms(t0),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tool 3: browse — Browser fetch (Ring 1, JS support)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def browse(
    url: str,
    timeout: int = 30,
    screenshot: bool = False,
    wait_for: str = "networkidle",
    js_eval: str = "",
    cookies: str = "",
    stealth: bool = True,
) -> dict:
    """Fetch a URL using a real Chromium browser with stealth anti-detection.

    Uses patchright (Cloudflare/bot-detection bypass) when stealth=True.
    Supports cookie injection for login-required pages.

    Args:
        url: Target URL.
        timeout: Page load timeout in seconds (default 30).
        screenshot: Include a JPEG screenshot (base64) in the result.
        wait_for: networkidle | domcontentloaded | load
        js_eval: Optional JS expression to evaluate; result prepended to text.
        cookies: Cookie file path OR JSON array string of cookie dicts.
                 Format: [{"name":"token","value":"xxx","domain":".example.com"}]
        stealth: Use patchright stealth mode (default True). Bypasses Cloudflare.

    Returns:
        {ok, url, title, text, html, screenshot_b64, engine, error, duration_ms}
    """
    t0 = time.perf_counter()
    if not CAPS.ring1:
        return {
            "ok": False, "url": url, "title": "", "text": "", "html": "",
            "screenshot_b64": "", "error": "Ring 1 offline (no browser)",
            "duration_ms": _ms(t0),
        }
    r = await r1_browser.fetch(
        url, timeout=timeout, screenshot=screenshot,
        wait_for=wait_for, js_eval=js_eval,
        cookies=cookies or None, stealth=stealth,
    )
    return {**r.to_dict(), "duration_ms": _ms(t0)}


# ══════════════════════════════════════════════════════════════════════════════
# Tool 4: interact — Browser automation
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def interact(
    url: str,
    actions: str,
    timeout: int = 60,
    screenshot: bool = True,
    cookies: str = "",
    stealth: bool = True,
) -> dict:
    """Control a real Chromium browser: click, fill forms, scroll, evaluate JS.

    Args:
        url: Starting URL.
        actions: JSON array of action objects:
            {"action": "click",    "selector": "#btn"}
            {"action": "fill",     "selector": "input[name=q]", "value": "hello"}
            {"action": "type",     "selector": "textarea",       "value": "text"}
            {"action": "scroll",   "value": "800"}
            {"action": "wait",     "wait_ms": 1000}
            {"action": "navigate", "value": "https://example.com"}
            {"action": "evaluate", "value": "document.title"}
            {"action": "wait_for", "selector": ".result-list"}
            {"action": "press",    "selector": "input", "value": "Enter"}
        timeout: Total timeout in seconds (default 60).
        screenshot: Include screenshot of final page state.
        cookies: Cookie file path or JSON array string (for login sessions).
        stealth: Use patchright stealth (default True).

    Returns:
        {ok, url, title, text, screenshot_b64, engine, error, duration_ms}
    """
    t0 = time.perf_counter()
    if not CAPS.ring1:
        return {"ok": False, "url": url, "error": "Playwright not available",
                "duration_ms": _ms(t0)}

    try:
        parsed_actions = json.loads(actions) if isinstance(actions, str) else actions
        if not isinstance(parsed_actions, list):
            parsed_actions = [parsed_actions]
    except Exception as exc:
        return {"ok": False, "url": url, "error": f"Invalid actions JSON: {exc}",
                "duration_ms": _ms(t0)}

    r = await r1_browser.interact(
        url, parsed_actions, timeout=timeout, screenshot=screenshot,
        cookies=cookies or None, stealth=stealth,
    )
    return {**r.to_dict(), "duration_ms": _ms(t0)}


# ══════════════════════════════════════════════════════════════════════════════
# R0 HTTP fallbacks for site commands not covered by CLI tools
# ══════════════════════════════════════════════════════════════════════════════

import re as _re

async def _github_trending(lang: str = "", since: str = "daily", limit: int = 25) -> list[dict]:
    """Scrape GitHub trending via R0 HTTP."""
    url = "https://github.com/trending"
    if lang:
        url += f"/{lang.lower()}"
    url += f"?since={since}"
    result = await r0_http.fetch(url, timeout=15, extract_text_content=False)
    if not result.ok:
        return []
    html = result.html
    repos: list[dict] = []
    # Match repo articles: <article class="Box-row">
    for art in _re.findall(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', html, _re.DOTALL):
        # Repo path: <a href="/owner/repo"
        path_m = _re.search(r'<h2[^>]*>\s*<a[^>]+href="/([^/"]+/[^/"]+)"', art)
        if not path_m:
            continue
        repo_path = path_m.group(1).strip()
        # Description
        desc_m = _re.search(r'<p[^>]*class="[^"]*color-fg-muted[^"]*"[^>]*>\s*(.*?)\s*</p>', art, _re.DOTALL)
        desc = _re.sub(r'\s+', ' ', desc_m.group(1)).strip() if desc_m else ""
        # Language
        lang_m = _re.search(r'itemprop="programmingLanguage"[^>]*>\s*(.*?)\s*<', art)
        repo_lang = lang_m.group(1).strip() if lang_m else ""
        # Stars
        stars_m = _re.search(r'aria-label="star".*?</svg>\s*([\d,]+)', art, _re.DOTALL)
        stars = stars_m.group(1).replace(",", "").strip() if stars_m else "0"
        repos.append({
            "repo": repo_path,
            "url": f"https://github.com/{repo_path}",
            "description": desc,
            "language": repo_lang,
            "stars": stars,
        })
        if len(repos) >= limit:
            break
    return repos


async def _hackernews_hot(limit: int = 30) -> list[dict]:
    """Fetch HN top stories via official API (R0 HTTP)."""
    top = await r0_http.fetch("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
    if not top.ok:
        return []
    try:
        ids = json.loads(top.text)[:limit]
    except Exception:
        return []
    import asyncio as _asyncio

    async def _item(iid: int) -> dict | None:
        r = await r0_http.fetch(f"https://hacker-news.firebaseio.com/v0/item/{iid}.json", timeout=8)
        if not r.ok:
            return None
        try:
            return json.loads(r.text)
        except Exception:
            return None

    items = await _asyncio.gather(*[_item(i) for i in ids])
    stories = []
    for it in items:
        if it and it.get("type") == "story":
            stories.append({
                "id": it.get("id"),
                "title": it.get("title", ""),
                "url": it.get("url", f"https://news.ycombinator.com/item?id={it.get('id')}"),
                "score": it.get("score", 0),
                "by": it.get("by", ""),
                "descendants": it.get("descendants", 0),
            })
    return stories


_R0_SITE_HANDLERS: dict[str, dict[str, Any]] = {
    "github": {"hot": _github_trending, "trending": _github_trending},
    "hackernews": {"hot": _hackernews_hot, "top": _hackernews_hot},
    "hn": {"hot": _hackernews_hot, "top": _hackernews_hot},
}


async def _site_r0_fallback(name: str, command: str, args: list[str], t0: float) -> dict | None:
    """Return R0-scraped result if we have a handler; None otherwise."""
    handlers = _R0_SITE_HANDLERS.get(name.lower(), {})
    handler = handlers.get(command.lower())
    if handler is None:
        return None
    try:
        # Parse limit from args (e.g., "limit=10" or positional int)
        limit = 25
        lang = ""
        for a in args:
            if a.startswith("limit="):
                limit = int(a.split("=", 1)[1])
            elif a.isdigit():
                limit = int(a)
            elif not a.startswith("since=") and not a.isdigit():
                lang = a
        import inspect
        sig = inspect.signature(handler)
        kw: dict[str, Any] = {}
        if "limit" in sig.parameters:
            kw["limit"] = limit
        if "lang" in sig.parameters:
            kw["lang"] = lang
        data = await handler(**kw)
        return {
            "ok": True, "site": name, "command": command,
            "data": data, "engine": "r0_http",
            "error": "", "duration_ms": _ms(t0),
        }
    except Exception as exc:
        return {
            "ok": False, "site": name, "command": command,
            "data": None, "engine": "r0_http",
            "error": str(exc), "duration_ms": _ms(t0),
        }


# ══════════════════════════════════════════════════════════════════════════════
# Tool 5: site — Structured site commands (Ring 2)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def site(
    name: str,
    command: str,
    args: str = "",
) -> dict:
    """Execute structured commands on social/content sites via bb-browser or opencli.

    Returns structured JSON data (e.g., hot posts, search results, user feeds).

    Sites: bilibili, zhihu, hackernews, reddit, twitter, xiaohongshu,
           youtube, github, arxiv, weibo, douban, and 100+ more.

    Args:
        name: Site name (e.g., "bilibili", "hackernews").
        command: Command to run (e.g., "hot", "trending", "search").
        args: Comma-separated arguments (e.g., "keyword,limit=10").

    Returns:
        {ok, site, command, data, engine, error, duration_ms}
    """
    t0 = time.perf_counter()
    parsed_args = [a.strip() for a in args.split(",") if a.strip()] if args else []

    # R0 HTTP fallbacks for sites not covered by CLI tools
    r0_result = await _site_r0_fallback(name, command, parsed_args, t0)
    if r0_result is not None:
        return r0_result

    if not CAPS.ring2:
        return {
            "ok": False, "site": name, "command": command, "data": None,
            "engine": "", "error": "Ring 2 offline — bb-browser and opencli not found",
            "duration_ms": _ms(t0),
        }

    r = await r2_cli.site_command(name, command, parsed_args)
    # If CLI failed, retry with R0 HTTP generic fetch
    if not r.ok:
        return {**r.to_dict(), "duration_ms": _ms(t0)}
    return {**r.to_dict(), "duration_ms": _ms(t0)}


# ══════════════════════════════════════════════════════════════════════════════
# Tool 6: crawl — BFS web crawl
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def crawl(
    url: str,
    max_pages: int = 10,
    max_depth: int = 2,
    same_domain: bool = True,
    timeout: int = 15,
    save: bool = False,
    format: str = "json",
) -> dict:
    """Crawl a website starting from a seed URL by following links (BFS).

    Args:
        url: Seed URL to start from.
        max_pages: Maximum pages to crawl (default 10, max 50).
        max_depth: Maximum link depth from seed (default 2).
        same_domain: Only follow links on the same domain (default True).
        timeout: Per-page timeout in seconds.
        save: If True, save crawl output to disk.
        format: Output format if save=True — json | md | ndjson.

    Returns:
        {ok, pages: [{url, title, text, depth}], total_pages, duration_s, output_files}
    """
    t0 = time.perf_counter()
    max_pages = min(max_pages, 50)
    seed_domain = urlparse(url).hostname or ""
    visited: set[str] = set()
    pages: list[dict] = []
    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    await queue.put((url, 0))

    while not queue.empty() and len(pages) < max_pages:
        current, depth = await queue.get()
        norm = current.rstrip("/")
        if norm in visited:
            continue
        visited.add(norm)

        r = await r0_http.fetch(current, timeout=timeout)
        if not r.ok:
            continue

        entry = {"url": current, "title": r.title, "text": r.text[:3000], "depth": depth}
        pages.append(entry)

        if depth < max_depth and len(pages) < max_pages:
            links = r0_http.extract_links(r.html, current)
            for link in links:
                if link.rstrip("/") in visited:
                    continue
                if same_domain and (urlparse(link).hostname or "") != seed_domain:
                    continue
                await queue.put((link, depth + 1))

    duration_s = round(time.perf_counter() - t0, 2)
    output_files: list[str] = []

    if save and pages:
        output_files = storage.save(
            pages, format=format, prefix="crawl",
            query=f"crawl:{urlparse(url).hostname}"
        )

    return {
        "ok": True,
        "pages": pages,
        "total_pages": len(pages),
        "duration_s": duration_s,
        "output_files": output_files,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Tool 7: research — Full pipeline (Ring 3)
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def research(
    query: str,
    language: str = "zh",
    max_sources: int = 15,
    max_pages: int = 10,
    max_queries: int = 4,
    max_concurrency: int = 5,
    timeout: int = 15,
    min_quality: float = 0.1,
    min_text_length: int = 100,
    include_domains: str = "",
    exclude_domains: str = "",
    format: str = "json,md",
    ctx: Context = None,
) -> dict:
    """Full research pipeline: expand → search → fetch → quality filter → save.

    Automatically expands query into multiple sub-queries, searches across
    engines, fetches pages concurrently, deduplicates, and saves structured output.

    Args:
        query: Research topic or question (any language).
        language: zh | en — affects query expansion and search region.
        max_sources: Max URLs to discover (default 15).
        max_pages: Max pages to actually fetch content from (default 10).
        max_queries: Max sub-queries to generate (default 4).
        max_concurrency: Parallel fetch workers (default 5).
        timeout: Per-page timeout in seconds (default 15).
        min_quality: Minimum quality score 0.0-1.0 (default 0.1).
        min_text_length: Minimum text length to accept a page (default 100).
        include_domains: Comma-separated domain allowlist (empty = all).
        exclude_domains: Comma-separated domain blocklist.
        format: Output formats — comma-separated: json, md, ndjson.

    Returns:
        {ok, query, records, total, queries_used, duration_s, output_files, engines_used}
    """
    t0 = time.perf_counter()
    _log.info("research: %r lang=%s", query, language)

    progress_msgs: list[str] = []

    def _progress(msg: str) -> None:
        progress_msgs.append(msg)
        _log.info("[research] %s", msg)
        if ctx is not None:
            try:
                asyncio.get_event_loop().call_soon_threadsafe(
                    lambda: None  # progress_cb is async in newer MCP
                )
            except Exception:
                pass

    try:
        inc = [d.strip() for d in include_domains.split(",") if d.strip()] or None
        exc = [d.strip() for d in exclude_domains.split(",") if d.strip()] or None

        output = await r3_pipeline.run(
            query,
            language=language,
            max_sources=max_sources,
            max_pages=max_pages,
            max_queries=max_queries,
            max_concurrency=max_concurrency,
            timeout=timeout,
            min_quality=min_quality,
            min_text_length=min_text_length,
            include_domains=inc,
            exclude_domains=exc,
            progress_cb=_progress,
        )

        # Save outputs
        output_files: list[str] = []
        if output.records:
            records_dicts = [r.to_dict() for r in output.records]
            output_files = storage.save(
                records_dicts,
                format=format,
                prefix="research",
                query=query,
            )

        return {
            "ok": True,
            "query": query,
            "records": [r.to_dict() for r in output.records],
            "total": len(output.records),
            "queries_used": output.queries_used,
            "duration_s": output.duration_s,
            "output_files": output_files,
            "engines_used": sorted(set(output.engines_used)),
            "progress": progress_msgs,
        }

    except Exception as exc:
        _log.exception("research failed: %s", exc)
        return {
            "ok": False, "query": query, "records": [], "total": 0,
            "error": str(exc),
            "duration_s": round(time.perf_counter() - t0, 2),
        }


# ══════════════════════════════════════════════════════════════════════════════
# Tool 8: status — Capability status report
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def status() -> dict:
    """Report the current capability status of all rings.

    Returns which rings are online, what's available, and troubleshooting info.
    """
    caps = CAPS.summary()
    rings = {
        "ring0_http": {
            "online": CAPS.ring0,
            "description": "HTTP fetch via httpx (always available)",
            "engines": ["httpx"],
        },
        "ring1_browser": {
            "online": CAPS.ring1,
            "description": "Playwright Chromium browser (JS, screenshots)",
            "engines": ["playwright"],
            "note": "" if CAPS.ring1 else "Install: playwright install chromium",
        },
        "ring2_cli": {
            "online": CAPS.ring2,
            "description": "Structured site commands (social/content platforms)",
            "engines": {
                "bb-browser": CAPS.bb_browser_path or "not found",
                "opencli": CAPS.opencli_path or "not found",
            },
            "note": "" if CAPS.ring2 else "Ensure bb-browser/opencli are in PATH or set BB_BROWSER_BIN/OPENCLI_BIN env vars",
        },
        "ring3_pipeline": {
            "online": CAPS.ring3,
            "description": "Multi-source research pipeline (builds on R0+R1)",
        },
    }
    return {
        "ok": True,
        "version": "v2",
        "rings": rings,
        "capabilities": caps,
    }


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    stdio_mode = "--stdio" in sys.argv or not sys.stdout.isatty()
    if stdio_mode:
        _log.info("Starting unified-web-skill v2 in stdio mode")
        mcp.run(transport="stdio")
    else:
        _log.info("Starting unified-web-skill v2 on %s:%d", _MCP_HOST, _MCP_PORT)
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
