"""
Multi-source URL discovery.

Searches across multiple search engines simultaneously, merges results,
deduplicates, and ranks by relevance and credibility.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from ..engines.base import SearchResult
from .intent_classifier import IntentClassifier, QueryIntent
from .query_planner import QueryPlanner
from .site_registry import SiteRegistry

_logger = logging.getLogger(__name__)


class MultiSourceDiscovery:
    """Discovers URLs by searching across multiple search engines.

    Orchestrates intent classification, query expansion, parallel search
    dispatch, and result merging.
    """

    def __init__(
        self,
        engine_manager: Any = None,
        site_registry: SiteRegistry | None = None,
        classifier: IntentClassifier | None = None,
    ) -> None:
        self._engine_manager = engine_manager
        self._registry = site_registry or SiteRegistry.get_instance()
        self._classifier = classifier or IntentClassifier()
        self._planner = QueryPlanner(classifier=self._classifier)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def discover(
        self,
        query: str,
        *,
        max_sources: int = 30,
        language: str = "zh",
        engines: list[str] | None = None,
        **opts: Any,
    ) -> list[SearchResult]:
        """Discover URLs from multiple search engines.

        Strategy
        --------
        1. Classify intent.
        2. Select search engines based on intent + language.
        3. Expand query.
        4. Search across selected engines in parallel.
        5. Merge, deduplicate, and rank results.

        Parameters
        ----------
        query:
            Raw search string.
        max_sources:
            Maximum total results to return.
        language:
            ``"zh"``, ``"en"``, ``"auto"``.
        engines:
            Explicit list of engine names to use (overrides auto-selection).
        **opts:
            Forwarded to individual search backends.

        Returns
        -------
        list[SearchResult]
            Deduplicated, ranked results.
        """
        if not query.strip():
            return []

        # 1. Classify
        intent = self._classifier.classify(query, language=language)
        _logger.info("query=%r  intent=%s  language=%s", query, intent.value, language)

        # 2. Select engines
        if engines is None:
            engines = self._classifier.get_recommended_sources(intent, language=language)
        _logger.debug("selected engines: %s", engines)

        # 3. Expand query
        expanded = self._planner.expand(query, language=language, intent=intent, max_queries=4)
        _logger.debug("expanded queries: %s", expanded)

        # 4. Search in parallel
        per_engine = max(max_sources // max(len(engines), 1), 5)
        tasks: list[asyncio.Task[list[SearchResult]]] = []

        for engine_name in engines:
            for q in expanded[:2]:  # use first 2 variants per engine
                task = asyncio.create_task(
                    self._dispatch_search(engine_name, q, per_engine, language),
                    name=f"search:{engine_name}:{q[:30]}",
                )
                tasks.append(task)

        all_results: list[list[SearchResult]] = []
        for coro in asyncio.as_completed(tasks):
            try:
                batch = await coro
                all_results.append(batch)
            except Exception as exc:
                _logger.warning("search task failed: %s", exc)

        # 5. Merge + rank
        merged = await self._merge_results(all_results)
        ranked = self._rank_results(merged, query)
        return ranked[:max_sources]

    # ------------------------------------------------------------------
    # Engine dispatch
    # ------------------------------------------------------------------

    async def _dispatch_search(
        self, engine: str, query: str, max_results: int, language: str
    ) -> list[SearchResult]:
        """Route a search to the appropriate backend."""
        if self._engine_manager is not None:
            try:
                # Check if the named engine exists; if not, use any SEARCH-capable engine
                em_engine = self._engine_manager.get_engine(engine) if hasattr(self._engine_manager, 'get_engine') else None
                engine_list = [engine] if em_engine else None
                raw = await self._engine_manager.search_multi(
                    query=query, engines=engine_list, max_results=max_results, language=language
                )
                if raw:
                    return [
                        SearchResult(
                            url=r.url,
                            title=r.title,
                            snippet=r.snippet,
                            source=engine,
                            rank=idx,
                        )
                        for idx, r in enumerate(raw)
                        if r.url
                    ]
            except Exception as exc:
                _logger.warning("engine_manager.search(%s) failed: %s", engine, exc)

        # Universal fallback: always try DuckDuckGo when the named engine yields nothing
        return await self._search_duckduckgo(query, max_results=max_results, language=language)

    async def _search_duckduckgo(
        self, query: str, max_results: int = 10, language: str = "zh"
    ) -> list[SearchResult]:
        """Fallback: use ``duckduckgo-search`` library directly.

        Runs the synchronous DDGS call in a thread-pool executor so we
        don't block the event loop.
        """
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None, self._ddgs_text, query, max_results, language
            )
            return results
        except Exception as exc:
            _logger.warning("duckduckgo fallback failed for %r: %s", query, exc)
            return []

    @staticmethod
    def _ddgs_text(query: str, max_results: int, language: str) -> list[SearchResult]:
        """Synchronous wrapper around ``ddgs.DDGS`` (or legacy ``duckduckgo_search``)."""
        DDGS = None
        try:
            from ddgs import DDGS  # type: ignore[import-untyped]
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # type: ignore[import-untyped]
            except ImportError:
                _logger.debug("neither ddgs nor duckduckgo-search installed; skipping")
                return []

        region = "cn-zh" if language == "zh" else "wt-wt"
        results: list[SearchResult] = []
        try:
            ddgs = DDGS()
            for idx, r in enumerate(ddgs.text(query, region=region, max_results=max_results)):
                results.append(
                    SearchResult(
                        url=r.get("href", r.get("link", "")),
                        title=r.get("title", ""),
                        snippet=r.get("body", r.get("snippet", "")),
                        source="duckduckgo",
                        rank=idx,
                    )
                )
        except Exception as exc:
            _logger.warning("DDGS.text() error: %s", exc)
        return results

    # ------------------------------------------------------------------
    # Merge & Rank
    # ------------------------------------------------------------------

    async def _merge_results(
        self, results: list[list[SearchResult]]
    ) -> list[SearchResult]:
        """Merge and deduplicate results from multiple engines.

        When the same URL appears from different engines, keep the one with
        the best (lowest) rank and note all source engines in metadata.
        """
        seen: dict[str, SearchResult] = {}

        for batch in results:
            for sr in batch:
                if not sr.url:
                    continue

                key = sr.url_hash
                if key in seen:
                    existing = seen[key]
                    existing.score += 1.0  # boost for appearing in multiple sources
                    engines_set: set[str] = set(
                        existing.metadata.get("all_engines", [existing.source])
                    )
                    engines_set.add(sr.source)
                    existing.metadata["all_engines"] = sorted(engines_set)
                else:
                    sr.score = 1.0
                    sr.metadata["all_engines"] = [sr.source]
                    seen[key] = sr

        return list(seen.values())

    def _rank_results(
        self, results: list[SearchResult], query: str
    ) -> list[SearchResult]:
        """Rank merged results by relevance and credibility.

        Scoring factors
        ---------------
        * Multi-source bonus: already accumulated in ``score`` during merge.
        * Rank position: lower rank (appeared earlier) → higher score.
        * Title / snippet match: bonus if query terms appear literally.
        * Domain credibility: known sites get a small boost.
        """
        query_lower = query.lower()
        query_terms = [t for t in query_lower.split() if len(t) > 1]

        for sr in results:
            # Position score: earlier results score higher
            position_score = max(0, 10 - sr.rank) * 0.3
            sr.score += position_score

            # Title keyword match
            title_lower = sr.title.lower()
            title_hits = sum(1 for t in query_terms if t in title_lower)
            sr.score += title_hits * 0.5

            # Snippet keyword match
            snippet_lower = sr.snippet.lower()
            snippet_hits = sum(1 for t in query_terms if t in snippet_lower)
            sr.score += snippet_hits * 0.2

            # Known-site credibility boost
            cap = self._registry.lookup_by_url(sr.url)
            if cap is not None:
                sr.score += 0.5
                sr.content_type = cap.content_type

        results.sort(key=lambda r: r.score, reverse=True)
        return results
