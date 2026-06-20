"""Tavily Search API provider — AI-optimized real-time web search."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ..base import BaseEngine, Capability, FetchResult, SearchResult

logger = logging.getLogger(__name__)

API_KEY_ENV = "TAVILY_API_KEY"
BASE_URL = "https://api.tavily.com"
TIMEOUT = 30


class TavilySearchEngine(BaseEngine):
    """AI-optimized web search via Tavily API. Best for real-time information."""

    name = "tavily-search"
    capabilities = {Capability.SEARCH}

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ.get(API_KEY_ENV, "")

    async def search(self, query: str, *, max_results: int = 10, **opts: Any) -> list[SearchResult]:
        if not self._api_key:
            logger.debug("Tavily search skipped: %s not set", API_KEY_ENV)
            return []
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{BASE_URL}/search",
                    json={"api_key": self._api_key, "query": query, "max_results": max_results},
                )
            resp.raise_for_status()
            data = resp.json()
            results: list[SearchResult] = []
            for i, item in enumerate(data.get("results", [])):
                results.append(SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                    source="tavily",
                    rank=i + 1,
                ))
            return results
        except Exception as exc:
            logger.warning("Tavily search error: %s", exc)
            return []

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def version_info(self) -> dict[str, Any]:
        return {"ok": bool(self._api_key), "version": "tavily-v1", "note": "" if self._api_key else f"Set {API_KEY_ENV}"}
