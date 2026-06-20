"""Perplexity Sonar API provider — reasoning-aware search with citations."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from ..base import BaseEngine, Capability, SearchResult

logger = logging.getLogger(__name__)

API_KEY_ENV = "PERPLEXITY_API_KEY"
BASE_URL = "https://api.perplexity.ai"
TIMEOUT = 30


class PerplexitySearchEngine(BaseEngine):
    """Reasoning-aware search via Perplexity Sonar API. Best for complex questions."""

    name = "perplexity-search"
    capabilities = {Capability.SEARCH}

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ.get(API_KEY_ENV, "")

    async def search(self, query: str, *, max_results: int = 10, **opts: Any) -> list[SearchResult]:
        if not self._api_key:
            logger.debug("Perplexity search skipped: %s not set", API_KEY_ENV)
            return []
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{BASE_URL}/sonar/search",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "model": opts.get("model", "sonar-pro"),
                        "max_tokens": 2000,
                    },
                )
            resp.raise_for_status()
            data = resp.json()

            results: list[SearchResult] = []
            # Perplexity returns an answer + citations
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Add the answer as the first "result"
            if answer:
                results.append(SearchResult(
                    url=f"perplexity:search:{query[:50]}",
                    title="Perplexity Sonar Answer",
                    snippet=answer[:1000],
                    source="perplexity",
                    rank=1,
                ))

            # Add citations as additional results
            citations = data.get("citations", [])
            if isinstance(citations, list):
                for i, cit in enumerate(citations[: max_results - 1], 2):
                    if isinstance(cit, str):
                        results.append(SearchResult(
                            url=cit, title=f"Citation {i-1}", snippet="", source="perplexity", rank=i,
                        ))
                    elif isinstance(cit, dict):
                        results.append(SearchResult(
                            url=cit.get("url", ""), title=cit.get("title", ""),
                            snippet=cit.get("snippet", ""), source="perplexity", rank=i,
                        ))

            return results
        except Exception as exc:
            logger.warning("Perplexity search error: %s", exc)
            return []

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def version_info(self) -> dict[str, Any]:
        return {"ok": bool(self._api_key), "version": "sonar-pro", "note": "" if self._api_key else f"Set {API_KEY_ENV}"}
