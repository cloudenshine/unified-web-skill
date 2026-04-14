"""scrapling_engine.py — Scrapling 3-tier fetch engine (HTTP → Dynamic → Stealth)."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

from .base import BaseEngine, Capability, FetchResult, SearchResult

_BLOCK_MARKERS: list[str] = [
    "captcha",
    "access denied",
    "cloudflare",
    "just a moment",
    "not a robot",
    "unusual traffic",
    "ip has been blocked",
    "challenge-running",
    "rate limit",
    "too many requests",
    "bot detection",
]

_BLOCK_STATUS: set[int] = {401, 403, 407, 429, 500, 502, 503, 504}

_CN_DOMAINS: tuple[str, ...] = (
    "weibo.com", "zhihu.com", "bilibili.com", "douban.com", "xiaohongshu.com",
    "baidu.com", "qq.com", "163.com", "sina.com", "sohu.com", "csdn.net",
    "taobao.com", "jd.com", "tmall.com", "meituan.com", "tencent.com",
)


def _is_blocked(status: int, body: str) -> bool:
    if status in _BLOCK_STATUS:
        return True
    lower = (body or "").lower()
    # Short pages (<3000 chars) may be genuine block/challenge pages.
    # Longer pages that contain "cloudflare" are simply using Cloudflare CDN —
    # checking every marker on them would produce false positives (e.g. claude.com).
    if len(lower) < 3000:
        return any(m in lower for m in _BLOCK_MARKERS)
    # For full-length pages, only flag on unambiguous hard block markers.
    hard_markers = ["captcha", "access denied", "ip has been blocked", "challenge-running"]
    return any(m in lower for m in hard_markers)


def _is_cn_domain(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").removeprefix("www.").lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in _CN_DOMAINS)


def _extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML using trafilatura with regex fallback."""
    if not html:
        return ""
    try:
        import trafilatura
        text = trafilatura.extract(html, include_comments=False, include_tables=True,
                                   no_fallback=False, favor_recall=True)
        if text and len(text) > 50:
            return text
    except Exception:
        pass
    # Fallback: simple regex stripping
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class ScraplingEngine(BaseEngine):
    """3-tier Scrapling engine: HTTP → Dynamic → Stealth."""

    def __init__(self) -> None:
        self._timeout_http = int(os.environ.get("SCRAPLING_TIMEOUT_HTTP", "8"))
        self._timeout_dynamic = int(os.environ.get("SCRAPLING_TIMEOUT_DYNAMIC", "30"))
        self._timeout_stealth = int(os.environ.get("SCRAPLING_TIMEOUT_STEALTH", "60"))
        # Fix SSL certs for curl_cffi on Windows
        if os.name == "nt" and not os.environ.get("CURL_CA_BUNDLE"):
            try:
                import certifi
                os.environ["CURL_CA_BUNDLE"] = certifi.where()
            except ImportError:
                pass
        super().__init__()

    @property
    def name(self) -> str:
        return "scrapling"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.SEARCH}

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            result = await self.fetch("https://httpbin.org/get", timeout=15, mode="http")
            return result.ok
        except Exception:
            return False

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        mode: str = opts.get("mode", "auto")
        enable_stealth: bool = opts.get("enable_stealth", True)

        if mode == "auto":
            tiers = (
                ["dynamic", "http"] if _is_cn_domain(url) else ["http", "dynamic"]
            )
            if enable_stealth:
                tiers.append("stealth")
        elif mode == "http":
            tiers = ["http"]
        elif mode == "dynamic":
            tiers = ["dynamic"]
        elif mode == "stealth":
            tiers = ["stealth"]
        else:
            tiers = ["http", "dynamic", "stealth"] if enable_stealth else ["http", "dynamic"]

        last: FetchResult | None = None
        for tier in tiers:
            result = await self._fetch_tier(url, tier)
            last = result
            if result.ok:
                return result
            self._logger.debug("tier %s failed for %s: %s", tier, url, result.error)

        return last or FetchResult(
            ok=False, url=url, engine=self.name, error="all tiers failed",
        )

    # -- tier implementations ----------------------------------------------

    async def _fetch_tier(self, url: str, tier: str) -> FetchResult:
        t0 = time.monotonic()
        engine_label = f"scrapling-{tier}"
        try:
            if tier == "http":
                return await self._tier_http(url, t0)
            elif tier == "dynamic":
                return await self._tier_dynamic(url, t0)
            elif tier == "stealth":
                return await self._tier_stealth(url, t0)
            else:
                return FetchResult(
                    ok=False, url=url, engine=engine_label,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    error=f"unknown tier: {tier}",
                )
        except Exception as exc:
            return FetchResult(
                ok=False, url=url, engine=engine_label,
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(exc),
            )

    async def _tier_http(self, url: str, t0: float) -> FetchResult:
        from scrapling import Fetcher

        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: Fetcher().get(url, timeout=self._timeout_http, stealthy_headers=True),
        )
        dur = (time.monotonic() - t0) * 1000
        html = resp.html_content or ""
        text = resp.get_all_text(" ") if hasattr(resp, "get_all_text") else ""
        if not text and html:
            text = _extract_text_from_html(html)
        status = resp.status
        blocked = _is_blocked(status, html)
        return FetchResult(
            ok=not blocked and status < 400,
            url=url, engine="scrapling-http", html=html, text=text,
            status=status, duration_ms=dur,
            error="blocked" if blocked else "",
        )

    async def _tier_dynamic(self, url: str, t0: float) -> FetchResult:
        from scrapling import DynamicFetcher

        try:
            resp = await DynamicFetcher().async_fetch(url, timeout=self._timeout_dynamic * 1000)
        except Exception as exc:
            dur = (time.monotonic() - t0) * 1000
            return FetchResult(
                ok=False, url=url, engine="scrapling-dynamic",
                duration_ms=dur, error=str(exc),
            )
        dur = (time.monotonic() - t0) * 1000
        html = resp.html_content or ""
        text = resp.get_all_text(" ") if hasattr(resp, "get_all_text") else ""
        if not text and html:
            text = _extract_text_from_html(html)
        status = resp.status
        blocked = _is_blocked(status, html)
        return FetchResult(
            ok=not blocked and status < 400,
            url=url, engine="scrapling-dynamic", html=html, text=text,
            status=status, duration_ms=dur,
            error="blocked" if blocked else "",
        )

    async def _tier_stealth(self, url: str, t0: float) -> FetchResult:
        from scrapling import StealthyFetcher

        try:
            resp = await StealthyFetcher().async_fetch(url, timeout=self._timeout_stealth * 1000)
        except Exception as exc:
            dur = (time.monotonic() - t0) * 1000
            return FetchResult(
                ok=False, url=url, engine="scrapling-stealth",
                duration_ms=dur, error=str(exc),
            )
        dur = (time.monotonic() - t0) * 1000
        html = resp.html_content or ""
        text = resp.get_all_text(" ") if hasattr(resp, "get_all_text") else ""
        if not text and html:
            text = _extract_text_from_html(html)
        status = resp.status
        blocked = _is_blocked(status, html)
        return FetchResult(
            ok=not blocked and status < 400,
            url=url, engine="scrapling-stealth", html=html, text=text,
            status=status, duration_ms=dur,
            error="blocked" if blocked else "",
        )

    # -- search via DuckDuckGo -----------------------------------------

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh",
        **opts: Any,
    ) -> list[SearchResult]:
        """Search using DuckDuckGo (ddgs library) in a thread-pool executor."""
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None, self._ddgs_search, query, max_results, language,
            )
            return results
        except Exception as exc:
            self._logger.warning("search failed: %s", exc)
            return []

    @staticmethod
    def _ddgs_search(query: str, max_results: int, language: str) -> list[SearchResult]:
        DDGS = None
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return []

        region = "cn-zh" if language == "zh" else "wt-wt"
        results: list[SearchResult] = []
        try:
            ddgs = DDGS()
            for idx, r in enumerate(ddgs.text(query, region=region, max_results=max_results)):
                results.append(SearchResult(
                    url=r.get("href", r.get("link", "")),
                    title=r.get("title", ""),
                    snippet=r.get("body", r.get("snippet", "")),
                    source="scrapling-ddgs",
                    rank=idx,
                ))
        except Exception:
            pass
        return results
