"""scrapling_engine.py — Scrapling 3-tier fetch engine (HTTP → Dynamic → Stealth)."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

from .base import BaseEngine, Capability, FetchResult

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
    return any(m in lower for m in _BLOCK_MARKERS)


def _is_cn_domain(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").removeprefix("www.").lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in _CN_DOMAINS)


def _extract_text_from_html(html: str) -> str:
    """Best-effort plain text extraction from HTML without external deps."""
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class ScraplingEngine(BaseEngine):
    """3-tier Scrapling engine: HTTP → Dynamic → Stealth."""

    def __init__(self) -> None:
        self._timeout_http = int(os.environ.get("SCRAPLING_TIMEOUT_HTTP", "10"))
        self._timeout_dynamic = int(os.environ.get("SCRAPLING_TIMEOUT_DYNAMIC", "30"))
        self._timeout_stealth = int(os.environ.get("SCRAPLING_TIMEOUT_STEALTH", "60"))
        super().__init__()

    @property
    def name(self) -> str:
        return "scrapling"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH}

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
        from scrapling import AsyncFetcher

        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: AsyncFetcher(auto_match=True).get(url, timeout=self._timeout_dynamic),
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

        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: StealthyFetcher(auto_match=False).get(url, timeout=self._timeout_stealth),
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
