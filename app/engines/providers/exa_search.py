"""Exa Search API provider — semantic search optimized for academic/tech content."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ..base import BaseEngine, Capability, FetchResult, SearchResult

logger = logging.getLogger(__name__)

API_KEY_ENV = "EXA_API_KEY"
BASE_URL = "https://api.exa.ai"
TIMEOUT = 30


class ExaSearchEngine(BaseEngine):
    """Semantic search via Exa API — best for research, academic, technical queries."""

    name = "exa-search"
    capabilities = {Capability.SEARCH, Capability.FETCH}

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ.get(API_KEY_ENV, "")
        self._enabled = bool(self._api_key)

    async def search(self, query: str, *, max_results: int = 10, **opts: Any) -> list[SearchResult]:
        if not self._enabled:
            logger.debug("Exa search skipped: %s not set", API_KEY_ENV)
            return []
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{BASE_URL}/v1/search",
                    headers=self._headers(),
                    json={
                        "query": query,
                        "numResults": max_results,
                        "type": opts.get("search_type", "keyword"),
                        "useAutoprompt": opts.get("autoprompt", True),
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            results: list[SearchResult] = []
            for i, item in enumerate(data.get("results", [])):
                results.append(SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    source="exa",
                    rank=i + 1,
                ))
            return results
        except Exception as exc:
            logger.warning("Exa search error: %s", exc)
            return []

    async def fetch(self, url: str, *, timeout: int | None = None, **kwargs: Any) -> FetchResult:
        if not self._enabled:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"{API_KEY_ENV} not set")
        try:
            async with httpx.AsyncClient(timeout=timeout or TIMEOUT) as client:
                resp = await client.post(
                    f"{BASE_URL}/v1/contents",
                    headers=self._headers(),
                    json={"urls": [url], "text": True},
                )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return FetchResult(ok=False, url=url, engine=self.name, error="No content returned")
                return FetchResult(ok=True, url=url, engine=self.name, text=results[0].get("text", ""), title=results[0].get("title", ""), quality_score=0.8, metadata={"source": "exa"})
        except Exception as exc:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"Exa fetch failed: {exc}")

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._api_key, "Content-Type": "application/json", "Accept": "application/json"}

    async def health_check(self) -> bool:
        return self._enabled

    async def version_info(self) -> dict[str, Any]:
        return {"ok": self._enabled, "version": "exa-api-v1", "note": "" if self._enabled else f"Set {API_KEY_ENV}"}
