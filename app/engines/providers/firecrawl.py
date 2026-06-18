"""Firecrawl API engine — web scraping and search via api.firecrawl.dev.

Free tier: 1,000 credits/month (no credit card required).  Each scrape/crawl
costs 1 credit.  Requires FIRECRAWL_API_KEY environment variable.
See https://docs.firecrawl.dev for API reference.
"""

from __future__ import annotations

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
      - fetch: POST /v2/scrape — extract clean markdown from any URL
      - search: POST /v2/search — discover pages by natural-language query
    """

    name = "firecrawl"
    capabilities = {Capability.FETCH, Capability.SEARCH}

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ.get(API_KEY_ENV, "")
        self._base_url = os.environ.get("FIRECRAWL_BASE_URL", BASE_URL)

    # ── Engine protocol ───────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Return True if the API key is set and the endpoint is reachable."""
        if not self._api_key:
            return False
        # Firecrawl doesn't have a dedicated health endpoint — check key format
        if not self._api_key.startswith("fc-"):
            return False
        try:
            # Lightweight probe: scrape a small known URL
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._base_url}/v2/scrape",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={"url": "https://example.com"},
                )
                return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def version_info(self) -> dict[str, Any]:
        return {
            "ok": bool(self._api_key),
            "version": "firecrawl-api-v2",
            "api": self._base_url,
            "error": "" if self._api_key else "FIRECRAWL_API_KEY not set",
        }

    async def fetch(
        self,
        url: str,
        *,
        timeout: int | None = None,
        **opts: Any,
    ) -> FetchResult:
        """Fetch *url* through Firecrawl /v2/scrape, returning clean markdown."""
        if not self._api_key:
            return FetchResult(
                ok=False, url=url, engine=self.name,
                error=f"Firecrawl API key not set. Set {API_KEY_ENV} env var.",
            )

        t0 = time.monotonic()
        payload: dict[str, Any] = {"url": url, "formats": ["markdown"]}
        if opts.get("only_main"):
            payload["onlyMainContent"] = True
        if opts.get("page_options"):
            payload.update(opts["page_options"])

        try:
            async with httpx.AsyncClient(timeout=float(timeout or TIMEOUT)) as client:
                resp = await client.post(
                    f"{self._base_url}/v2/scrape",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
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
                        metadata={"firecrawl_data": result},
                    )

                error_detail = data.get("error", "unknown")
                return FetchResult(
                    ok=False, url=url, engine=self.name,
                    status=resp.status_code, duration_ms=dur,
                    error=f"Firecrawl scrape failed: {error_detail}",
                )

            body = resp.text[:300]
            return FetchResult(
                ok=False, url=url, engine=self.name,
                status=resp.status_code, duration_ms=dur,
                error=f"Firecrawl HTTP {resp.status_code}: {body}",
            )

        except httpx.TimeoutException:
            dur = (time.monotonic() - t0) * 1000.0
            return FetchResult(
                ok=False, url=url, engine=self.name,
                duration_ms=dur,
                error=f"Firecrawl timed out after {timeout or TIMEOUT}s",
            )
        except httpx.RequestError as exc:
            dur = (time.monotonic() - t0) * 1000.0
            return FetchResult(
                ok=False, url=url, engine=self.name,
                duration_ms=dur,
                error=f"Firecrawl request failed: {exc}",
            )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        **opts: Any,
    ) -> list[SearchResult]:
        """Search through Firecrawl /v2/search endpoint."""
        if not self._api_key:
            logger.warning("Firecrawl search skipped: %s not set", API_KEY_ENV)
            return []

        t0 = time.monotonic()
        timeout = opts.get("timeout", TIMEOUT)
        payload: dict[str, Any] = {
            "query": query,
            "limit": max_results,
        }
        if opts.get("scrape_results"):
            payload["scrapeOptions"] = {"formats": ["markdown"]}

        try:
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                resp = await client.post(
                    f"{self._base_url}/v2/search",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if resp.status_code == 200:
                data = resp.json()
                results: list[SearchResult] = []
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
