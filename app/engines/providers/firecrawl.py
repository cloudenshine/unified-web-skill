"""Firecrawl API engine - web scraping and search via api.firecrawl.dev.

Free tier: 1,000 credits/month (no credit card required).
**No API key required** for the free tier - Firecrawl supports keyless
operation. Set FIRECRAWL_API_KEY env var for higher rate limits / paid tier.
See https://docs.firecrawl.dev for API reference.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any

import httpx

from ..base import BaseEngine, Capability, FetchResult, SearchResult

logger = logging.getLogger(__name__)

API_KEY_ENV = "FIRECRAWL_API_KEY"
BASE_URL = "https://api.firecrawl.dev"
TIMEOUT = 60


class FirecrawlEngine(BaseEngine):
    """Engine wrapping Firecrawl API for content extraction and web search.

    Provides:
      - fetch: POST /v2/scrape - extract clean markdown from any URL
      - search: POST /v2/search - discover pages by natural-language query

    Free tier works without an API key (keyless mode). Set FIRECRAWL_API_KEY
    for higher rate limits.
    """

    name = "firecrawl"
    capabilities = {Capability.FETCH, Capability.SEARCH}

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ.get(API_KEY_ENV, "")
        self._base_url = os.environ.get("FIRECRAWL_BASE_URL", BASE_URL)
        self._use_keyless = not bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        """Build request headers. Omit Authorization in keyless mode."""
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = "Bearer " + self._api_key
        return h

    async def health_check(self) -> bool:
        """Return True if the endpoint is reachable (keyless or keyed)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._base_url + "/v2/scrape",
                    headers=self._headers(),
                    json={"url": "https://example.com"},
                )
                return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def version_info(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": "firecrawl-api-v2",
            "api": self._base_url,
            "keyless": self._use_keyless,
            "note": "" if self._api_key else "Free tier (no API key). Set FIRECRAWL_API_KEY for higher limits.",
        }

    async def fetch(
        self,
        url: str,
        *,
        timeout: int | None = None,
        **opts: Any,
    ) -> FetchResult:
        """Fetch url through Firecrawl /v2/scrape, returning clean markdown."""
        t0 = time.monotonic()
        payload = {"url": url, "formats": ["markdown"]}
        if opts.get("only_main"):
            payload["onlyMainContent"] = True
        if opts.get("page_options"):
            payload.update(opts["page_options"])

        try:
            async with httpx.AsyncClient(timeout=float(timeout or TIMEOUT)) as client:
                resp = await client.post(
                    self._base_url + "/v2/scrape",
                    headers=self._headers(),
                    json=payload,
                )
            dur = (time.monotonic() - t0) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    result = data.get("data", {})
                    text = result.get("markdown", "")
                    title = result.get("metadata", {}).get("title", "")
                    return FetchResult(
                        ok=True,
                        url=url,
                        engine=self.name,
                        text=text,
                        title=title,
                        status=200,
                        duration_ms=dur,
                        quality_score=0.85,
                        content_hash=hashlib.sha256(text.encode()).hexdigest()[:12],
                        metadata={"firecrawl_data": result},
                    )
                error_detail = data.get("error", "unknown")
                return FetchResult(
                    ok=False, url=url, engine=self.name,
                    status=resp.status_code, duration_ms=dur,
                    error="Firecrawl scrape failed: " + str(error_detail),
                )

            body = resp.text[:300]
            return FetchResult(
                ok=False, url=url, engine=self.name,
                status=resp.status_code, duration_ms=dur,
                error="Firecrawl HTTP " + str(resp.status_code) + ": " + body,
            )

        except httpx.TimeoutException:
            dur = (time.monotonic() - t0) * 1000.0
            return FetchResult(
                ok=False, url=url, engine=self.name,
                duration_ms=dur,
                error="Firecrawl timed out after " + str(timeout or TIMEOUT) + "s",
            )
        except httpx.RequestError as exc:
            dur = (time.monotonic() - t0) * 1000.0
            return FetchResult(
                ok=False, url=url, engine=self.name,
                duration_ms=dur,
                error="Firecrawl request failed: " + str(exc),
            )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        **opts: Any,
    ) -> list[SearchResult]:
        """Search through Firecrawl /v2/search endpoint."""
        timeout = opts.get("timeout", TIMEOUT)
        payload = {"query": query, "limit": max_results}
        if opts.get("scrape_results"):
            payload["scrapeOptions"] = {"formats": ["markdown"]}

        try:
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                resp = await client.post(
                    self._base_url + "/v2/search",
                    headers=self._headers(),
                    json=payload,
                )

            if resp.status_code == 200:
                data = resp.json()
                results = []
                if data.get("success"):
                    for item in data.get("data", []):
                        results.append(SearchResult(
                            url=item.get("url", ""),
                            title=item.get("title", ""),
                            snippet=item.get("description", ""),
                            source="firecrawl",
                            rank=len(results) + 1,
                        ))
                return results

            logger.warning("Firecrawl search returned HTTP %d: %s",
                           resp.status_code, resp.text[:200])
            return []

        except Exception as exc:
            logger.warning("Firecrawl search error: %s", exc)
            return []
