"""
Unified Web Skill v3.0 — MCP Server
    "Integrates 3 web engines (OpenCLI, Scrapling, CloakBrowser)
under a unified MCP interface for AI agent data access, plus credential management.

Tools:
    1. research_and_collect  — Full research pipeline
    2. web_fetch             — Single URL fetch with auto engine routing
    3. web_cli               — Direct OpenCLI site command
    4. web_interact           — Browser interaction (click, fill, screenshot)
    5. web_search             — Multi-engine search
    6. web_crawl              — Multi-page crawl from seed URL
    7. engine_status          — Check engine health & availability
    8. credential_status     — Report credential status per platform
    9. credential_inject     — Inject cookies from Cookie-Editor JSON
   10. credential_extract    — Extract cookies from browser
   11. credential_refresh    — Clear platform credentials for re-extraction
   12. web_profile_list       — List available CloakBrowser profiles
   13. web_profile_use        — Switch active CloakBrowser profile
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from typing import Any
from urllib.parse import urljoin, urlparse

from . import __version__, config
from .credential import CredentialStore, mask_value, extract_to_store, import_from_agent_reach, CookieExtractionError
from .models import ResearchTask, ResearchResult

# MCP import with graceful fallback
try:
    from mcp.server.fastmcp import FastMCP, Context
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    Context = None  # type: ignore[assignment,misc]

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

    from .engines.cloak_browser import CloakBrowserEngine
    from .engines.manager import EngineManager
    from .engines.scrapling_engine import ScraplingEngine

    _engine_manager = EngineManager()

    # Register engines in priority order — guarded by config flags


    if config.CLOAK_BROWSER_ENABLED:
        _engine_manager.register(CloakBrowserEngine())


    if config.OPENCLI_ENABLED:
        from .engines.opencli import OpenCLIEngine
        _engine_manager.register(OpenCLIEngine())

    _engine_manager.register(ScraplingEngine())




    _logger.info(
        "EngineManager ready - %d engines: %s",
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


def _is_local_browser_url(url: str) -> bool:
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def _default_profile_for_local_interact(url: str, profile: str, intent: str) -> str:
    if profile or not _is_local_browser_url(url):
        return profile
    if intent in {"js_render", "screenshot", "login_required", "form_submit", "download"}:
        return "stable-local-windows"
    return profile



def _new_trace_id() -> str:
    return str(uuid.uuid4())


def _audit_payload(
    *,
    trace_id: str,
    provider: str = "",
    profile: str = "",
    fallback_count: int = 0,
    browser_escalations: int = 0,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "provider": provider,
        "profile": profile,
        "fallback_count": fallback_count,
        "browser_escalations": browser_escalations,
    }


def _research_response_payload(
    result: ResearchResult,
    *,
    query: str,
    duration_ms: float,
) -> dict:
    """Build the backward-compatible research response plus Phase 4 bundle."""
    from .pipeline.bundle import ResearchBundleBuilder

    return {
        "ok": True,
        "query": query,
        "records": [r.model_dump() for r in result.records],
        "stats": result.stats.model_dump(),
        "queries_used": result.queries_used,
        "output_files": result.output_files,
        "bundle": ResearchBundleBuilder().build(result),
        "trace_id": result.task.task_id,
        "audit": {
            "trace_id": result.task.task_id,
            "profile": result.task.browser_profile,
            "fallback_count": result.stats.fallback_count,
            "browser_escalations": result.stats.browser_escalations,
        },
        "duration_ms": duration_ms,
    }


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
        need_browser_verification: bool = False,
        browser_profile: str = "",
        browser_intent: str = "js_render",
        max_concurrency: int = 5,
        timeout_seconds: int = 15,
        ctx: Context = None,
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
            need_browser_verification: Escalate failed or weak pages through CloakBrowser.
            browser_profile: Approved browser profile name for browser escalation.
            browser_intent: Browser interaction intent for escalation.
            max_concurrency: Maximum concurrent fetch operations.
            timeout_seconds: Per-URL fetch timeout in seconds.

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
                need_browser_verification=need_browser_verification,
                browser_profile=browser_profile,
                browser_intent=browser_intent,
                max_concurrency=max_concurrency,
                timeout_seconds=timeout_seconds,
            )

            em = _get_engine_manager()

            # Import pipeline — may come from new pipeline/ package or legacy module
            try:
                from .pipeline.research import ResearchPipeline
            except ImportError:
                from .research_pipeline import ResearchPipeline  # type: ignore[no-redef]

            pipeline = ResearchPipeline(engine_manager=em)
            progress_cb = ctx.report_progress if ctx is not None else None
            result: ResearchResult = await pipeline.run(task, progress_cb=progress_cb)

            return _research_response_payload(
                result,
                query=query,
                duration_ms=_ms_since(t0),
            )
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
        trace_id = _new_trace_id()
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
                "trace_id": trace_id,
                "audit": _audit_payload(
                    trace_id=trace_id,
                    provider=result.engine,
                ),
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
                "trace_id": trace_id,
                "audit": _audit_payload(trace_id=trace_id),
                "duration_ms": _ms_since(t0),
                "error": str(exc),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 3 — web_cli  (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════

# Command alias mapping: harmonizes user-facing command names with what opencli
# underlying CLI actually implements (e.g. "hot" → "top" for hackernews).
_CLI_COMMAND_ALIASES: dict[str, dict[str, str]] = {
    "hackernews": {
        "hot": "top",      # "hot" is not a hackernews command; "top" is
        "best": "best",
        "new": "new",
        "ask": "ask",
        "show": "show",
        "jobs": "jobs",
        "search": "search",
        "user": "user",
    },
    "bilibili": {
        "hot": "hot",
        "search": "search",
        "ranking": "ranking",
        "comments": "comments",
        "dynamic": "dynamic",
        "feed": "feed",
        "history": "history",
        "me": "me",
        "user-videos": "user-videos",
        "subtitle": "subtitle",
        "following": "following",
        "favorite": "favorite",
        "download": "download",
    },
}

# Timeout overrides for web_cli (CLI tools need more time for Chrome CDP
# handshake / site API calls). 45s is a safe default for a single command.
_CLI_TIMEOUT = 45

if mcp is not None:

    @mcp.tool()
    async def web_cli(
        site: str,
        command: str,
        args: str = "",
    ) -> dict:
        """Execute a site-specific CLI command via OpenCLI.

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

        # Resolve command alias (hackernews "hot" → "top", etc.)
        resolved_command = (
            _CLI_COMMAND_ALIASES.get(site, {}).get(command, command)
            if command
            else command
        )

        try:
            em = _get_engine_manager()

            # Use opencli
            opencli = em.get_engine("opencli")
            if opencli is not None:
                try:
                    # Always request JSON output so we can parse it reliably;
                    # default opencli format is "table" which breaks json.loads.
                    cmd = (
                        [config.OPENCLI_BIN, site, resolved_command]
                        + parsed_args
                        + ["--format", "json"]
                    )
                    from .engines.base import BaseEngine
                    rc, stdout, stderr = await BaseEngine._run_subprocess(
                        opencli, cmd, timeout=_CLI_TIMEOUT,
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
                    _logger.debug(
                        "opencli failed for %s/%s: %s", site, command, exc,
                    )

            return {
                "ok": False,
                "site": site,
                "command": command,
                "data": None,
                "engine": "",
                    "error": "No CLI engine (opencli) available",
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
        profile: str = "",
        intent: str = "",
        require_login: bool = False,
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
            profile: Approved CloakBrowser profile for persistent identity.
            intent: Required interaction intent such as js_render / login_required / screenshot.
            require_login: Whether this interaction depends on a logged-in session.
            return_snapshot: Include a base64 screenshot in the response.
            return_text: Include extracted page text in the response.
            timeout: Interaction timeout in seconds.
            engine: Force a specific engine (empty = auto-select).

        Returns:
            dict with keys: ok, url, text, snapshot, instance_id, engine, duration_ms
        """
        t0 = time.perf_counter()
        trace_id = _new_trace_id()
        _logger.info("web_interact: url=%s engine=%s", url, engine or "auto")
        default_engine = engine
        if not default_engine and _get_engine_manager().get_engine("cloakbrowser") is not None:
            default_engine = "cloakbrowser"

        if default_engine == "cloakbrowser" and not intent:
            return {
                "ok": False,
                "url": url,
                "text": "",
                "snapshot": "",
                "instance_id": "",
                "engine": default_engine,
                "trace_id": trace_id,
                "audit": _audit_payload(
                    trace_id=trace_id,
                    provider=default_engine,
                    profile=profile or instance_id,
                ),
                "error": "intent is required for cloakbrowser interactions",
                "duration_ms": _ms_since(t0),
            }

        effective_profile = _default_profile_for_local_interact(url, profile or instance_id, intent)

        if effective_profile == "us-household-resi" and not config.RESIDENTIAL_PROXY_READY:
            return {
                "ok": False,
                "url": url,
                "text": "",
                "snapshot": "",
                "instance_id": "",
                "engine": default_engine or "",
                "trace_id": trace_id,
                "audit": _audit_payload(
                    trace_id=trace_id,
                    provider=default_engine or "",
                    profile=profile or instance_id,
                ),
                "error": "us-household-resi requires a verified residential proxy",
                "duration_ms": _ms_since(t0),
            }

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
                    "trace_id": trace_id,
                    "audit": _audit_payload(
                        trace_id=trace_id,
                        profile=profile or instance_id,
                    ),
                    "error": f"Invalid actions JSON: {exc}",
                    "duration_ms": _ms_since(t0),
                }

        try:
            em = _get_engine_manager()
            result = await em.interact(
                url,
                parsed_actions,
                engine=default_engine or None,
                timeout=timeout,
                profile=effective_profile,
                intent=intent,
                require_login=require_login,
            )

            return {
                "ok": result.ok,
                "url": result.url or url,
                "text": result.text if return_text else "",
                "snapshot": result.snapshot if return_snapshot else "",
                "instance_id": result.instance_id,
                "engine": result.engine,
                "trace_id": trace_id,
                "audit": _audit_payload(
                    trace_id=trace_id,
                    provider=result.engine,
                    profile=effective_profile or result.instance_id or instance_id,
                ),
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
                "trace_id": trace_id,
                "audit": _audit_payload(
                    trace_id=trace_id,
                    profile=effective_profile or instance_id,
                ),
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
        trace_id = _new_trace_id()
        _logger.info("web_search: query=%r engines=%s", query, engines or "all")

        try:
            em = _get_engine_manager()
            engine_list = _parse_csv(engines) or None
                        # search fallback: scrapling
            if engine_list is None:
                engine_list = ["scrapling"]

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
                "trace_id": trace_id,
                "audit": _audit_payload(
                    trace_id=trace_id,
                    provider=",".join(engines_used),
                ),
                "duration_ms": _ms_since(t0),
            }
        except Exception as exc:
            _logger.exception("web_search failed: %s", exc)
            return {
                "ok": False,
                "results": [],
                "engines_used": [],
                "total": 0,
                "trace_id": trace_id,
                "audit": _audit_payload(trace_id=trace_id),
                "error": str(exc),
                "duration_ms": _ms_since(t0),
            }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 5b — web_profile_list / web_profile_use  (NEW)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def web_profile_list(
        region: str = "",
        tag: str = "",
    ) -> dict:
        """List approved browser profiles for agent tasks."""
        t0 = time.perf_counter()
        trace_id = _new_trace_id()
        return {
            "ok": False,
            "profiles": [],
            "trace_id": trace_id,
            "audit": _audit_payload(trace_id=trace_id, provider="cloakbrowser"),
            "error": "cloak-manager service has been removed. Profile management is handled internally by CloakBrowserEngine via CLOAK_BROWSER_BASE_URL.",
            "duration_ms": _ms_since(t0),
        }

    @mcp.tool()
    async def web_profile_use(
        profile: str,
        reason: str,
    ) -> dict:
        """Bind an approved profile to the current task intent."""
        t0 = time.perf_counter()
        trace_id = _new_trace_id()
        return {
            "ok": False,
            "profile": profile,
            "trace_id": trace_id,
            "audit": _audit_payload(trace_id=trace_id, provider="cloakbrowser", profile=profile),
            "error": "cloak-manager service has been removed. Profile management is handled by CloakBrowserEngine configuration.",
            "duration_ms": _ms_since(t0),
        }


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
                "providers": await em.provider_status(),
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
# Tools 8-11 — Credential management  (NEW)
# ═══════════════════════════════════════════════════════════════════════════

if mcp is not None:

    @mcp.tool()
    async def credential_status() -> dict:
        """Report status of all credential platforms.

        Returns:
            dict with keys: ok, platforms (list of {name, keys, masked, count}),
            total_platforms, encryption (bool), file, dir
        """
        try:
            store = CredentialStore.get_instance()
            return store.doctor()
        except Exception as exc:
            _logger.exception("credential_status failed: %s", exc)
            return {"ok": False, "platforms": [], "total_platforms": 0, "error": str(exc)}


    @mcp.tool()
    async def credential_inject(
        platform: str,
        cookie_json: str,
        save: bool = True,
    ) -> dict:
        """Inject credentials for a platform from a Cookie-Editor style JSON string.

        The JSON can be either a flat ``{"name": "value", ...}`` dict or
        a list of ``{"name": "...", "value": "..."}`` objects (Cookie-Editor export format).

        Args:
            platform: Platform name (twitter, xiaohongshu, bilibili, xueqiu).
            cookie_json: JSON string with cookies (flat dict or Cookie-Editor list).
            save: Whether to persist to disk immediately (default True).

        Returns:
            dict with keys: ok, platform, keys_injected, error
        """
        try:
            import json
            data = json.loads(cookie_json)

            store = CredentialStore.get_instance()

            if isinstance(data, list):
                # Cookie-Editor format: [{"name": "...", "value": "..."}, ...]
                kv: dict[str, str] = {}
                for entry in data:
                    name = entry.get("name", "")
                    value = entry.get("value", "")
                    if name and value is not None:
                        kv[name] = value
                if not kv:
                    return {"ok": False, "platform": platform, "keys_injected": 0,
                            "error": "No valid cookie entries found in Cookie-Editor JSON"}
                store.set_platform(platform, kv)
            elif isinstance(data, dict):
                # Flat {key: value} format
                store.set_platform(platform, {str(k): str(v) for k, v in data.items()})
            else:
                return {"ok": False, "platform": platform, "keys_injected": 0,
                        "error": "JSON must be a dict or a list of Cookie-Editor objects"}

            if save:
                store.save()

            keys = list(store.get_all(platform).keys())
            return {"ok": True, "platform": platform, "keys_injected": len(keys), "keys": keys}
        except json.JSONDecodeError as exc:
            return {"ok": False, "platform": platform, "keys_injected": 0,
                    "error": f"Invalid JSON: {exc}"}
        except Exception as exc:
            _logger.exception("credential_inject failed: %s", exc)
            return {"ok": False, "platform": platform, "keys_injected": 0, "error": str(exc)}


    @mcp.tool()
    async def credential_extract(
        platform: str = "",
        from_agent_reach: bool = False,
    ) -> dict:
        """Extract cookies from browser(s) and store them as credentials.

        Args:
            platform: Specific platform to extract (empty = all known platforms).
            from_agent_reach: If True, import from ~/.agent-reach/config.yaml instead
                              of from browser cookies.

        Returns:
            dict with keys: ok, platforms (list of platform names extracted), count
        """
        try:
            if from_agent_reach:
                imported = import_from_agent_reach()
                platforms = list(imported.keys())
                return {"ok": True, "platforms": platforms, "count": len(platforms),
                        "source": "agent-reach"}
            else:
                count = extract_to_store(platform if platform else None)
                store = CredentialStore.get_instance()
                all_platforms = store.list_platforms()
                return {"ok": True, "platforms": all_platforms, "count": count,
                        "source": "browser-cookies"}
        except CookieExtractionError as exc:
            return {"ok": False, "platforms": [], "count": 0,
                    "error": str(exc), "hint": "Log into the site in your browser first"}
        except Exception as exc:
            _logger.exception("credential_extract failed: %s", exc)
            return {"ok": False, "platforms": [], "count": 0, "error": str(exc)}


    @mcp.tool()
    async def credential_refresh(
        platform: str,
    ) -> dict:
        """Mark a platform's credentials as needing refresh (extract again from browser).

        This removes the stored credentials for the given platform so the next
        extraction will fetch fresh values from the browser.

        Args:
            platform: Platform name to refresh (twitter, xiaohongshu, etc.).

        Returns:
            dict with keys: ok, platform, action
        """
        try:
            store = CredentialStore.get_instance()
            had_keys = list(store.get_all(platform).keys())
            for key in had_keys:
                store.remove(platform, key)
            store.save()
            return {
                "ok": True,
                "platform": platform,
                "action": "cleared, ready for fresh extraction",
                "removed_keys": had_keys,
            }
        except Exception as exc:
            _logger.exception("credential_refresh failed: %s", exc)
            return {"ok": False, "platform": platform, "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# /health endpoint & entry points
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Entry point for the MCP server.

    - ``--stdio`` or non-TTY stdout → stdio transport (for OpenClaw bundle-mcp).
    - ``--http`` or TTY stdout      → HTTP/SSE transport with /health endpoint.
    """
    _ensure_mcp()

    force_http = os.environ.get("FORCE_HTTP")
    if force_http or "--http" in sys.argv or sys.stdout.isatty():
        _start_http()
    else:
        _logger.info("Starting MCP server in stdio mode")
        mcp.run(transport="stdio")


def _start_http():
    """Launch the MCP server over HTTP with a /health sidecar endpoint."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def _health_endpoint(request):
        em = _get_engine_manager()
        engine_names = list(em._engines.keys()) if em else []
        cache_info = {}
        try:
            from . import cache as _cache
            cache_info = _cache.stats()
        except Exception:
            pass
        return JSONResponse({
            "status": "ok",
            "service": "unified-web-skill",
            "version": __version__,
            "engines": engine_names,
            "engine_count": len(engine_names),
            "cache": cache_info,
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









