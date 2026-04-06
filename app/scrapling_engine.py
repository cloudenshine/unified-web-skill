"""scrapling_engine.py — Scrapling HTTP engine (Lightpanda/Stealth stubs)"""
import asyncio
import time
from dataclasses import dataclass
from typing import Any

from .heuristics import is_blocked_status, body_blocked, auto_route


@dataclass
class FetchResult:
    ok: bool
    url: str
    status: int
    html: str
    engine: str
    route: str
    duration_ms: float
    error: str = ""
    data: dict | None = None


async def _fetch_http(url: str, timeout: int = 30) -> FetchResult:
    """HTTP tier: FetcherSession with impersonation"""
    t0 = time.monotonic()
    try:
        from scrapling.fetchers import Fetcher
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: Fetcher().get(url, timeout=timeout, stealthy_headers=True)
        )
        dur = (time.monotonic() - t0) * 1000
        html = response.html_content or ""
        status = response.status
        blocked = is_blocked_status(status) or body_blocked(html)
        return FetchResult(
            ok=not blocked and status < 400,
            url=url, status=status, html=html,
            engine="scrapling-http", route="http", duration_ms=dur,
            error="blocked" if blocked else ""
        )
    except Exception as e:
        dur = (time.monotonic() - t0) * 1000
        return FetchResult(ok=False, url=url, status=0, html="",
                           engine="scrapling-http", route="http",
                           duration_ms=dur, error=str(e))


async def _fetch_dynamic(url: str, cdp_url: str = "ws://lightpanda:9222",
                         timeout: int = 30) -> FetchResult:
    """Dynamic tier: DynamicSession via Lightpanda CDP (stub when LP unavailable)"""
    t0 = time.monotonic()
    try:
        from scrapling.fetchers import AsyncFetcher
        # Try DynamicSession — requires Lightpanda running
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: AsyncFetcher(auto_match=False).get(
                url, timeout=timeout,
                extra_headers={"X-Fetch-Mode": "dynamic"}
            )
        )
        dur = (time.monotonic() - t0) * 1000
        html = response.html_content or ""
        status = response.status
        return FetchResult(
            ok=status < 400,
            url=url, status=status, html=html,
            engine="scrapling-dynamic", route="dynamic", duration_ms=dur
        )
    except Exception as e:
        dur = (time.monotonic() - t0) * 1000
        return FetchResult(ok=False, url=url, status=0, html="",
                           engine="scrapling-dynamic", route="dynamic",
                           duration_ms=dur, error=f"dynamic_unavailable:{e}")


async def _fetch_stealth(url: str, timeout: int = 60) -> FetchResult:
    """Stealth tier: StealthyFetcher (Playwright-based, slowest)"""
    t0 = time.monotonic()
    try:
        from scrapling.fetchers import StealthyFetcher
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: StealthyFetcher(auto_match=False).get(url, timeout=timeout)
        )
        dur = (time.monotonic() - t0) * 1000
        html = response.html_content or ""
        status = response.status
        return FetchResult(
            ok=status < 400,
            url=url, status=status, html=html,
            engine="scrapling-stealth", route="stealth", duration_ms=dur
        )
    except Exception as e:
        dur = (time.monotonic() - t0) * 1000
        return FetchResult(ok=False, url=url, status=0, html="",
                           engine="scrapling-stealth", route="stealth",
                           duration_ms=dur, error=f"stealth_unavailable:{e}")


async def fetch_with_fallback(
    url: str,
    task_text: str = "",
    first: str = "auto",
    timeout: int = 30,
    enable_stealth: bool = False,
) -> FetchResult:
    """
    Multi-tier fetch: HTTP → Dynamic → Stealth
    Returns first successful result.
    """
    if first == "auto":
        first = auto_route(url, task_text)
        if first == "pinchtab":
            first = "http"  # pinchtab not available here, fallback to http

    tiers: list[str] = []
    if first == "http":
        tiers = ["http", "dynamic"] + (["stealth"] if enable_stealth else [])
    elif first == "dynamic":
        tiers = ["dynamic", "http"] + (["stealth"] if enable_stealth else [])
    else:
        tiers = ["http"]

    last_result = None
    for tier in tiers:
        if tier == "http":
            result = await _fetch_http(url, timeout=timeout)
        elif tier == "dynamic":
            result = await _fetch_dynamic(url, timeout=timeout)
        elif tier == "stealth":
            result = await _fetch_stealth(url, timeout=timeout)
        else:
            continue

        last_result = result
        if result.ok:
            return result
        # If blocked/error, try next tier

    return last_result or FetchResult(
        ok=False, url=url, status=0, html="",
        engine="none", route="none", duration_ms=0, error="all_tiers_failed"
    )
