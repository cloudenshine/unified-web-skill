"""
Unified Web Skill v3.0 — MCP Server
Integrates 6 web engines (OpenCLI, Scrapling, Lightpanda, PinchTab, bb-browser, CLIBrowser)
under a unified MCP interface for AI agent data access.

Tools:
    1. research_and_collect  — Full research pipeline
    2. web_fetch             — Single URL fetch with auto engine routing
    3. web_cli               — Direct OpenCLI / bb-browser site command
    4. web_interact           — Browser interaction (click, fill, screenshot)
    5. web_search             — Multi-engine search
    6. web_crawl              — Multi-page crawl from seed URL
    7. engine_status          — Check engine health & availability
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import Any
from urllib.parse import urljoin, urlparse

from . import config
from .models import ResearchTask, ResearchResult

# MCP import with graceful fallback
try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Global engine manager (lazy singleton)
# ---------------------------------------------------------------------------

_engine_manager = None


def _get_engine_manager():
    """Return (and lazily initialize) the global EngineManager."""
    global _engine_manager
    if _engine_manager is not None:
        return _engine_manager

    from .engines.manager import EngineManager
    from .engines.scrapling_engine import ScraplingEngine

    _engine_manager = EngineManager()

    # Register engines in priority order — guarded by config flags
    if config.BB_BROWSER_ENABLED:
        from .engines.bb_browser import BBBrowserEngine
        _engine_manager.register(BBBrowserEngine())

    if config.OPENCLI_ENABLED:
        from .engines.opencli import OpenCLIEngine
        _engine_manager.register(OpenCLIEngine())

    _engine_manager.register(ScraplingEngine())

    if config.LP_ENABLED:
        from .engines.lightpanda import LightpandaEngine
        _engine_manager.register(LightpandaEngine())

    if config.PINCHTAB_BASE_URL:
        from .engines.pinchtab import PinchTabEngine
        _engine_manager.register(PinchTabEngine())

    if config.CLIBROWSER_ENABLED:
        from .engines.clibrowser import CLIBrowserEngine
        _engine_manager.register(CLIBrowserEngine())

    _logger.info(
        "EngineManager ready — %d engines: %s",
        len(_engine_manager._engines),
        list(_engine_manager._engines.keys()),
    )
    return _engine_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ms_since(t0: float) -> float:
    """Milliseconds elapsed since *t0* (a ``time.perf_counter()`` value)."""
    return round((time.perf_counter() - t0) * 1000, 1)


def _parse_csv(raw: str) -> list[str]:
    """Split a comma-separated string, stripping whitespace and empties."""
    return [s.strip() for s in raw.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# FastMCP app
# ---------------------------------------------------------------------------

if not HAS_MCP:
    _logger.warning(
        "mcp package not installed — MCP server will not be available. "
        "Install with:  pip install mcp"
    )

mcp = FastMCP("unified-web-skill", host=config.MCP_HOST, port=config.MCP_PORT) if HAS_MCP else None


def _ensure_mcp():
    """Raise early if mcp is unavailable."""
    if mcp is None:
        raise RuntimeError(
            "FastMCP is not available. Install the mcp package: pip install mcp"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Tool 1 — research_and_collect  (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def research_and_collect(
        query: str,
        language: str = "zh",
        max_sources: int = 30,
        max_pages: int = 20,
        max_queries: int = 8,
        trusted_mode: bool = False,
        output_format: str = "json",
        min_text_length: int = 100,
        min_credibility: float = 0.3,
        time_window_days: int = 0,
        include_domains: str = "",
        exclude_domains: str = "",
        preferred_engines: str = "",
        search_engines: str = "",
        enable_stealth: bool = False,
        max_concurrency: int = 5,
    ) -> dict:
        """Complete research pipeline: query expansion → multi-source discovery → concurrent fetch → quality validation → structured output.

        Args:
            query: Research topic or question.
            language: Target language code (zh / en).
            max_sources: Maximum number of sources to discover.
            max_pages: Maximum pages to fetch content from.
            max_queries: Maximum expanded search queries to generate.
            trusted_mode: If True, only fetch from high-credibility sources.
            output_format: Output format — json | ndjson | md.
            min_text_length: Minimum extracted text length to accept a page.
            min_credibility: Minimum credibility score (0.0–1.0).
            time_window_days: Only include content from the last N days (0 = no filter).
            include_domains: Comma-separated domain allowlist.
            exclude_domains: Comma-separated domain blocklist.
            preferred_engines: Comma-separated engine names to prefer.
            search_engines: Comma-separated search engine names to use.
            enable_stealth: Use stealth/anti-detection fetching.
            max_concurrency: Maximum concurrent fetch operations.

        Returns:
            dict with keys: ok, query, records, stats, queries_used, output_files
        """
        t0 = time.perf_counter()
        _logger.info("research_and_collect: query=%r language=%s", query, language)

        try:
            task = ResearchTask(
                query=query,
                language=language,
                max_sources=max_sources,
                max_pages=max_pages,
                max_queries=max_queries,
                trusted_mode=trusted_mode,
                output_format=output_format,
                min_text_length=min_text_length,
                min_credibility=min_credibility,
                time_window_days=time_window_days,
                include_domains=_parse_csv(include_domains),
                exclude_domains=_parse_csv(exclude_domains),
                preferred_engines=_parse_csv(preferred_engines),
                search_engines=_parse_csv(search_engines),
                enable_stealth=enable_stealth,
                max_concurrency=max_concurrency,
            )

            em = _get_engine_manager()

            # Import pipeline — may come from new pipeline/ package or legacy module
            try:
                from .pipeline.research import ResearchPipeline
            except ImportError:
                from .research_pipeline import ResearchPipeline  # type: ignore[no-redef]

            pipeline = ResearchPipeline(engine_manager=em)
            result: ResearchResult = await pipeline.run(task)

            return {
                "ok": True,
                "query": query,
                "records": [r.model_dump() for r in result.records],
                "stats": result.stats.model_dump(),
                "queries_used": result.queries_used,
                "output_files": result.output_files,
                "duration_ms": _ms_since(t0),
            }
        except Exception as exc:
            _logger.exception("research_and_collect failed: %s", exc)
            return {"ok": False, "error": str(exc), "duration_ms": _ms_since(t0)}


# ═══════════════════════════════════════════════════════════════════════════
# Tool 2 — web_fetch  (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def web_fetch(
        url: str,
        task: str = "",
        mode: str = "auto",
        prefer_text: bool = True,
        timeout: int = 30,
        engine: str = "",
    ) -> dict:
        """Fetch a single URL with automatic engine routing and fallback.

        Args:
            url: The URL to fetch.
            task: Optional description of why this page is being fetched.
            mode: Routing hint — auto | http | dynamic | stealth.
            prefer_text: If True, return extracted text; otherwise raw HTML.
            timeout: Fetch timeout in seconds.
            engine: Force a specific engine by name (empty = auto-route).

        Returns:
            dict with keys: ok, url, text, html, title, engine, mode, duration_ms
        """
        t0 = time.perf_counter()
        _logger.info("web_fetch: url=%s engine=%s mode=%s", url, engine or "auto", mode)

        try:
            em = _get_engine_manager()
            preferred = [engine] if engine else None
            result = await em.fetch_with_fallback(
                url,
                preferred_engines=preferred,
                timeout=timeout,
                mode=mode,
            )

            text = result.text if prefer_text else ""
            html = "" if prefer_text else result.html

            return {
                "ok": result.ok,
                "url": result.url,
                "text": text or result.text,
                "html": html or result.html,
                "title": result.title,
                "engine": result.engine,
                "mode": mode,
                "duration_ms": result.duration_ms or _ms_since(t0),
                "error": result.error if not result.ok else "",
            }
        except Exception as exc:
            _logger.exception("web_fetch failed: %s", exc)
            return {
                "ok": False,
                "url": url,
                "text": "",
                "html": "",
                "title": "",
                "engine": "",
                "mode": mode,
                "duration_ms": _ms_since(t0),
                "error": str(exc),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 3 — web_cli  (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def web_cli(
        site: str,
        command: str,
        args: str = "",
    ) -> dict:
        """Execute a site-specific CLI command via bb-browser or OpenCLI.

        Supported sites include bilibili, zhihu, hackernews, reddit, twitter,
        xiaohongshu, youtube, github, arxiv, weibo, douban, and more.

        Args:
            site: Site adapter name (e.g. "bilibili", "zhihu").
            command: Command to execute (e.g. "hot", "search", "trending").
            args: Comma-separated arguments for the command.

        Returns:
            dict with keys: ok, site, command, data, engine
        """
        t0 = time.perf_counter()
        _logger.info("web_cli: site=%s command=%s", site, command)

        parsed_args = _parse_csv(args)

        try:
            em = _get_engine_manager()

            # Try bb-browser first (richer adapter coverage)
            bb = em.get_engine("bb_browser")
            if bb is not None:
                try:
                    route = f"{site}/{command}"
                    cmd = [config.BB_BROWSER_BIN, route] + parsed_args
                    from .engines.base import BaseEngine
                    rc, stdout, stderr = await BaseEngine._run_subprocess(
                        bb, cmd, timeout=config.BB_BROWSER_TIMEOUT,
                    )
                    if rc == 0 and stdout.strip():
                        try:
                            data = json.loads(stdout)
                        except json.JSONDecodeError:
                            data = stdout.strip()
                        return {
                            "ok": True,
                            "site": site,
                            "command": command,
                            "data": data,
                            "engine": "bb_browser",
                            "duration_ms": _ms_since(t0),
                        }
                except Exception as exc:
                    _logger.debug("bb-browser failed for %s/%s: %s", site, command, exc)

            # Fallback to opencli
            opencli = em.get_engine("opencli")
            if opencli is not None:
                try:
                    cmd = [config.OPENCLI_BIN, site, command] + parsed_args
                    from .engines.base import BaseEngine
                    rc, stdout, stderr = await BaseEngine._run_subprocess(
                        opencli, cmd, timeout=config.OPENCLI_TIMEOUT,
                    )
                    if rc == 0 and stdout.strip():
                        try:
                            data = json.loads(stdout)
                        except json.JSONDecodeError:
                            data = stdout.strip()
                        return {
                            "ok": True,
                            "site": site,
                            "command": command,
                            "data": data,
                            "engine": "opencli",
                            "duration_ms": _ms_since(t0),
                        }
                    else:
                        return {
                            "ok": False,
                            "site": site,
                            "command": command,
                            "data": None,
                            "engine": "opencli",
                            "error": stderr.strip() or f"exit code {rc}",
                            "duration_ms": _ms_since(t0),
                        }
                except Exception as exc:
                    _logger.debug("opencli failed for %s/%s: %s", site, command, exc)

            return {
                "ok": False,
                "site": site,
                "command": command,
                "data": None,
                "engine": "",
                "error": "No CLI engine (bb-browser / opencli) available",
                "duration_ms": _ms_since(t0),
            }

        except Exception as exc:
            _logger.exception("web_cli failed: %s", exc)
            return {
                "ok": False,
                "site": site,
                "command": command,
                "data": None,
                "engine": "",
                "error": str(exc),
                "duration_ms": _ms_since(t0),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 4 — web_interact  (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def web_interact(
        url: str = "",
        task: str = "",
        actions: str = "",
        instance_id: str = "",
        return_snapshot: bool = True,
        return_text: bool = True,
        timeout: int = 60,
        engine: str = "",
    ) -> dict:
        """Perform browser interactions: click, fill forms, scroll, screenshot, extract text.

        Args:
            url: Target URL to interact with.
            task: High-level description of the interaction goal.
            actions: JSON-encoded list of action objects, e.g. '[{"action":"click","selector":"#btn"}]'.
            instance_id: Reuse an existing browser session by ID.
            return_snapshot: Include a base64 screenshot in the response.
            return_text: Include extracted page text in the response.
            timeout: Interaction timeout in seconds.
            engine: Force a specific engine (empty = auto-select).

        Returns:
            dict with keys: ok, url, text, snapshot, instance_id, engine, duration_ms
        """
        t0 = time.perf_counter()
        _logger.info("web_interact: url=%s engine=%s", url, engine or "auto")

        # Parse actions from JSON string
        parsed_actions: list[dict[str, Any]] = []
        if actions:
            try:
                parsed_actions = json.loads(actions)
                if not isinstance(parsed_actions, list):
                    parsed_actions = [parsed_actions]
            except json.JSONDecodeError as exc:
                return {
                    "ok": False,
                    "url": url,
                    "text": "",
                    "snapshot": "",
                    "instance_id": "",
                    "engine": "",
                    "error": f"Invalid actions JSON: {exc}",
                    "duration_ms": _ms_since(t0),
                }

        try:
            em = _get_engine_manager()
            result = await em.interact(
                url,
                parsed_actions,
                engine=engine or None,
                timeout=timeout,
            )

            return {
                "ok": result.ok,
                "url": result.url or url,
                "text": result.text if return_text else "",
                "snapshot": result.snapshot if return_snapshot else "",
                "instance_id": result.instance_id,
                "engine": result.engine,
                "duration_ms": result.duration_ms or _ms_since(t0),
                "error": result.error if not result.ok else "",
            }
        except Exception as exc:
            _logger.exception("web_interact failed: %s", exc)
            return {
                "ok": False,
                "url": url,
                "text": "",
                "snapshot": "",
                "instance_id": "",
                "engine": "",
                "error": str(exc),
                "duration_ms": _ms_since(t0),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 5 — web_search  (NEW)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def web_search(
        query: str,
        max_results: int = 10,
        language: str = "zh",
        engines: str = "",
        intent: str = "",
    ) -> dict:
        """Search the web across multiple engines, returning merged and deduplicated results.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.
            language: Target language code (zh / en).
            engines: Comma-separated engine names to use (empty = all search-capable engines).
            intent: Optional search intent hint for routing (e.g. "news", "academic", "social").

        Returns:
            dict with keys: ok, results (list of {url, title, snippet, source, rank, credibility}), engines_used
        """
        t0 = time.perf_counter()
        _logger.info("web_search: query=%r engines=%s", query, engines or "all")

        try:
            em = _get_engine_manager()
            engine_list = _parse_csv(engines) or None

            results = await em.search_multi(
                query,
                engines=engine_list,
                max_results=max_results,
                language=language,
            )

            engines_used = sorted({r.source for r in results if r.source})

            return {
                "ok": True,
                "results": [
                    {
                        "url": r.url,
                        "title": r.title,
                        "snippet": r.snippet,
                        "source": r.source,
                        "rank": r.rank,
                        "credibility": r.credibility,
                    }
                    for r in results
                ],
                "engines_used": engines_used,
                "total": len(results),
                "duration_ms": _ms_since(t0),
            }
        except Exception as exc:
            _logger.exception("web_search failed: %s", exc)
            return {
                "ok": False,
                "results": [],
                "engines_used": [],
                "total": 0,
                "error": str(exc),
                "duration_ms": _ms_since(t0),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 6 — web_crawl  (NEW)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def web_crawl(
        url: str,
        max_pages: int = 10,
        max_depth: int = 2,
        same_domain_only: bool = True,
        extract_links: bool = True,
        timeout: int = 30,
    ) -> dict:
        """Crawl multiple pages starting from a seed URL by following links.

        Args:
            url: Seed URL to start crawling from.
            max_pages: Maximum number of pages to crawl.
            max_depth: Maximum link-following depth from the seed.
            same_domain_only: If True, only follow links on the same domain.
            extract_links: If True, extract and follow discovered links.
            timeout: Per-page fetch timeout in seconds.

        Returns:
            dict with keys: ok, pages (list of {url, title, text, depth}), total_pages, duration_s
        """
        t0 = time.perf_counter()
        _logger.info("web_crawl: url=%s max_pages=%d depth=%d", url, max_pages, max_depth)

        try:
            em = _get_engine_manager()
            seed_domain = urlparse(url).hostname or ""

            # BFS crawl state
            visited: set[str] = set()
            pages: list[dict[str, Any]] = []
            # Queue entries: (url, depth)
            queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
            await queue.put((url, 0))

            while not queue.empty() and len(pages) < max_pages:
                current_url, depth = await queue.get()

                # Normalize and deduplicate
                normalized = current_url.rstrip("/")
                if normalized in visited:
                    continue
                visited.add(normalized)

                # Fetch the page
                result = await em.fetch_with_fallback(
                    current_url,
                    timeout=timeout,
                )

                if not result.ok:
                    _logger.debug("Crawl skip (fetch failed): %s", current_url)
                    continue

                page_entry: dict[str, Any] = {
                    "url": current_url,
                    "title": result.title,
                    "text": result.text,
                    "depth": depth,
                }
                pages.append(page_entry)
                _logger.debug(
                    "Crawled [%d/%d] depth=%d: %s",
                    len(pages), max_pages, depth, current_url,
                )

                # Extract and enqueue links if within depth limit
                if extract_links and depth < max_depth and len(pages) < max_pages:
                    html_content = result.html or result.text
                    discovered_links = _extract_links(html_content, current_url)

                    for link in discovered_links:
                        link_normalized = link.rstrip("/")
                        if link_normalized in visited:
                            continue

                        if same_domain_only:
                            link_domain = urlparse(link).hostname or ""
                            if link_domain != seed_domain:
                                continue

                        # Skip non-HTTP, anchors, and common non-content extensions
                        parsed = urlparse(link)
                        if parsed.scheme not in ("http", "https", ""):
                            continue
                        ext = os.path.splitext(parsed.path)[1].lower()
                        if ext in (".jpg", ".jpeg", ".png", ".gif", ".svg", ".css",
                                   ".js", ".ico", ".woff", ".woff2", ".ttf", ".pdf",
                                   ".zip", ".tar", ".gz", ".mp3", ".mp4", ".avi"):
                            continue

                        await queue.put((link, depth + 1))

            duration_s = round(time.perf_counter() - t0, 2)
            return {
                "ok": True,
                "pages": pages,
                "total_pages": len(pages),
                "duration_s": duration_s,
            }

        except Exception as exc:
            _logger.exception("web_crawl failed: %s", exc)
            duration_s = round(time.perf_counter() - t0, 2)
            return {
                "ok": False,
                "pages": [],
                "total_pages": 0,
                "duration_s": duration_s,
                "error": str(exc),
            }


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract absolute URLs from HTML content using regex (no lxml dependency)."""
    if not html:
        return []

    links: list[str] = []
    seen: set[str] = set()

    # Match href attributes in anchor tags
    for match in re.finditer(r'<a\s[^>]*href=["\']([^"\'#][^"\']*)["\']', html, re.IGNORECASE):
        raw = match.group(1).strip()
        if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        absolute = urljoin(base_url, raw)
        # Strip fragments
        absolute = absolute.split("#")[0]
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    return links


# ═══════════════════════════════════════════════════════════════════════════
# Tool 7 — engine_status  (NEW)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def engine_status() -> dict:
        """Check health and availability of all registered web engines.

        Returns:
            dict with keys: engines (list of {name, available, capabilities})
        """
        t0 = time.perf_counter()
        _logger.info("engine_status: checking all engines")

        try:
            em = _get_engine_manager()

            # Run health checks
            health_map = await em.health_check_all()
            engine_info = em.list_engines()

            engines_list = []
            for name, caps in engine_info.items():
                engines_list.append({
                    "name": name,
                    "available": health_map.get(name, False),
                    "capabilities": caps,
                })

            return {
                "ok": True,
                "engines": engines_list,
                "total": len(engines_list),
                "duration_ms": _ms_since(t0),
            }
        except Exception as exc:
            _logger.exception("engine_status failed: %s", exc)
            return {
                "ok": False,
                "engines": [],
                "total": 0,
                "error": str(exc),
                "duration_ms": _ms_since(t0),
            }


# ═══════════════════════════════════════════════════════════════════════════
# /health endpoint & entry points
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Entry point for the MCP server.

    - ``--stdio`` or non-TTY stdout → stdio transport (for OpenClaw bundle-mcp).
    - ``--http`` or TTY stdout      → HTTP/SSE transport with /health endpoint.
    """
    _ensure_mcp()

    if "--stdio" in sys.argv or not sys.stdout.isatty():
        _logger.info("Starting MCP server in stdio mode")
        mcp.run(transport="stdio")
    else:
        _start_http()


def _start_http():
    """Launch the MCP server over HTTP with a /health sidecar endpoint."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def _health_endpoint(request):
        em = _get_engine_manager()
        engine_names = list(em._engines.keys()) if em else []
        return JSONResponse({
            "status": "ok",
            "service": "unified-web-skill",
            "version": "3.0.0",
            "engines": engine_names,
        })

    # Build the MCP ASGI app
    try:
        mcp_app = mcp.sse_app()
    except AttributeError:
        try:
            mcp_app = mcp.streamable_http_app()
        except AttributeError:
            mcp_app = mcp.get_asgi_app()  # type: ignore[union-attr]

    # Combine /health with the MCP app
    health_app = Starlette(
        routes=[Route("/health", _health_endpoint, methods=["GET"])],
    )

    from starlette.routing import Mount
    health_app.routes.append(Mount("/", app=mcp_app))

    _logger.info("Starting MCP server on %s:%s (HTTP/SSE)", config.MCP_HOST, config.MCP_PORT)
    uvicorn.run(
        health_app,
        host=config.MCP_HOST,
        port=config.MCP_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
