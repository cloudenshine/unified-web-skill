"""
Research Pipeline v3 — Full research workflow orchestrator.

Flow:
1. Intent classification
2. Query expansion (intent-aware)
3. Multi-source URL discovery (parallel search across engines)
4. Smart routing (SiteRegistry + heuristics)
5. Concurrent fetching with fallback (EngineManager)
6. Content extraction + quality validation
7. Deduplication + ranking
8. Structured persistence
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Optional
from urllib.parse import urlparse

from ..models import ResearchTask, ResearchRecord, ResearchResult, ResearchStats
from ..engines.manager import EngineManager
from ..engines.base import FetchResult, Capability
from ..discovery.multi_source import MultiSourceDiscovery
from ..discovery.intent_classifier import IntentClassifier
from ..discovery.query_planner import QueryPlanner
from ..discovery.site_registry import SiteRegistry
from ..utils.rate_limiter import DomainRateLimiter
from ..utils.scoring import score_credibility
from .extractor import ContentExtractor
from .quality import QualityGate
from .storage import ResultStorage

_logger = logging.getLogger(__name__)


class ResearchPipeline:
    """Complete research pipeline from query to structured output."""

    def __init__(self, engine_manager: EngineManager | None = None):
        self._engine_manager = engine_manager or EngineManager()
        self._discovery = MultiSourceDiscovery(engine_manager=self._engine_manager)
        self._classifier = IntentClassifier()
        self._planner = QueryPlanner(classifier=self._classifier)
        self._extractor = ContentExtractor()
        self._quality = QualityGate()
        self._storage = ResultStorage()
        self._rate_limiter = DomainRateLimiter()
        self._registry = SiteRegistry.get_instance()

    # Type alias for the progress callback (e.g. Context.report_progress)
    ProgressCb = Callable[..., Coroutine[Any, Any, None]]

    async def run(
        self,
        task: ResearchTask,
        progress_cb: Optional[ProgressCb] = None,
    ) -> ResearchResult:
        """Execute complete research pipeline."""
        start = time.monotonic()
        stats = ResearchStats()
        records: list[ResearchRecord] = []

        # Helper: report progress to MCP client so it resets its 60s timeout.
        _step = 0
        _total_steps = 5  # intent + expand + discover + fetch + save

        async def _progress(step_label: str) -> None:
            nonlocal _step
            _step += 1
            if progress_cb is not None:
                try:
                    await progress_cb(_step, _total_steps)
                except Exception:
                    pass  # never let progress reporting break the pipeline
            _logger.info("Progress %d/%d: %s", _step, _total_steps, step_label)

        _logger.info("Starting research: query='%s', lang=%s", task.query, task.language)

        try:
            # Step 1: Classify intent
            intent = self._classifier.classify(task.query, task.language)
            _logger.info("Intent: %s", intent.value)
            await _progress("intent classified")

            # Step 2: Expand queries (intent-aware)
            queries = self._planner.expand(
                task.query,
                language=task.language,
                max_queries=task.max_queries,
                intent=intent,
            )
            _logger.info("Expanded to %d queries", len(queries))
            await _progress("queries expanded")

            # Step 3: Discover URLs via multi-source search
            candidates = await self._discovery.discover(
                task.query,
                max_sources=task.max_sources,
                language=task.language,
                engines=task.search_engines or None,
            )
            stats.total_discovered = len(candidates)
            stats.search_engines_used = list(set(c.source for c in candidates))
            _logger.info(
                "Discovered %d candidates from %d engines",
                len(candidates),
                len(stats.search_engines_used),
            )
            await _progress("URLs discovered")

            # Step 4: Apply domain filters
            candidates = self._apply_filters(candidates, task)

            # Step 5: Concurrent fetch with EngineManager fallback
            sem = asyncio.Semaphore(task.max_concurrency)
            _fetch_done = 0

            async def _fetch_one(url: str, credibility: float) -> Optional[ResearchRecord]:
                nonlocal _fetch_done
                async with sem:
                    try:
                        # Rate limit per domain
                        domain = self._extract_domain(url)
                        await self._rate_limiter.acquire(domain)

                        # Fetch via EngineManager (handles routing + fallback)
                        result = await self._engine_manager.fetch_with_fallback(
                            url,
                            preferred_engines=task.preferred_engines or None,
                            timeout=task.timeout_seconds,
                        )

                        if not result.ok:
                            stats.skipped_blocked += 1
                            _logger.debug("Fetch failed for %s: %s", url, result.error)
                            return None

                        # Extract content
                        extracted = self._extractor.extract(result)

                        # Quality gate
                        passed, reason = self._quality.validate(
                            extracted,
                            min_length=task.min_text_length,
                            min_credibility=task.min_credibility,
                            time_window_days=task.time_window_days,
                        )
                        if not passed:
                            stats.skipped_quality += 1
                            _logger.debug("Quality gate failed for %s: %s", url, reason)
                            return None

                        # Build record
                        record = ResearchRecord(
                            url=url,
                            title=extracted.get("title", result.title or ""),
                            text=extracted.get("text", result.text or ""),
                            summary=extracted.get("summary", ""),
                            published_at=extracted.get("date"),
                            language=extracted.get("language", task.language),
                            content_hash=extracted.get("content_hash", ""),
                            fetch_engine=result.engine,
                            fetch_mode=result.route,
                            fetch_duration_ms=result.duration_ms,
                            credibility=credibility,
                            source_type="search",
                            tool_chain=[result.engine] if result.engine else [],
                        )

                        stats.engines_used[result.engine] = stats.engines_used.get(result.engine, 0) + 1
                        return record

                    except Exception as exc:
                        _logger.warning("Unexpected error fetching %s: %s", url, exc)
                        return None
                    finally:
                        # Report per-page progress to keep MCP timeout alive
                        _fetch_done += 1
                        if progress_cb is not None:
                            try:
                                await progress_cb(_fetch_done, _total_fetch)
                            except Exception:
                                pass

            # Calculate credibility scores for candidates
            candidate_list = [
                (c.url, score_credibility(c.url, trusted_mode=task.trusted_mode))
                for c in candidates[:task.max_pages]
            ]
            _total_fetch = len(candidate_list)

            # Update total steps for progress reporting
            _total_steps = _total_fetch + 2  # fetch pages + dedup + save
            _step = 0  # reset for fetch phase

            # Execute concurrent fetches
            tasks_list = [_fetch_one(url, cred) for url, cred in candidate_list]
            results = await asyncio.gather(*tasks_list, return_exceptions=True)

            # Collect successful results
            for r in results:
                if isinstance(r, ResearchRecord):
                    records.append(r)
                elif isinstance(r, Exception):
                    _logger.warning("Fetch task exception: %s", r)

            # Step 6: Deduplicate
            records, dup_count = self._quality.deduplicate(records)
            stats.skipped_duplicate = dup_count
            stats.total_collected = len(records)
            stats.total_skipped = stats.skipped_quality + stats.skipped_duplicate + stats.skipped_blocked

            # Step 7: Calculate stats
            if records:
                durations = [r.fetch_duration_ms for r in records if r.fetch_duration_ms > 0]
                stats.avg_fetch_ms = round(sum(durations) / len(durations), 2) if durations else 0

            await _progress("fetch & quality complete")

        except Exception as exc:
            _logger.error("Pipeline error: %s", exc, exc_info=True)

        stats.total_duration_s = round(time.monotonic() - start, 2)

        # Step 8: Save results
        result = ResearchResult(
            task=task,
            records=records,
            stats=stats,
            queries_used=queries if "queries" in dir() else [task.query],
        )

        try:
            output_files = await self._storage.save(result, task.output_format, task.output_dir)
            result.output_files = output_files
        except Exception as exc:
            _logger.error("Storage error: %s", exc)

        await _progress("results saved")
        _logger.info("Research complete: %d records in %ss", len(records), stats.total_duration_s)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_filters(self, candidates: list, task: ResearchTask) -> list:
        """Apply include/exclude domain filters from the task."""
        if not task.include_domains and not task.exclude_domains:
            return candidates

        include_set = {d.lower() for d in task.include_domains} if task.include_domains else None
        exclude_set = {d.lower() for d in task.exclude_domains} if task.exclude_domains else set()

        filtered: list = []
        for c in candidates:
            domain = self._extract_domain(c.url).lower()
            if not domain:
                continue

            # Exclude check
            if any(domain.endswith(ex) for ex in exclude_set):
                continue

            # Include check (if specified, domain must match)
            if include_set is not None:
                if not any(domain.endswith(inc) for inc in include_set):
                    continue

            filtered.append(c)

        if len(filtered) != len(candidates):
            _logger.info(
                "Domain filters: %d → %d candidates",
                len(candidates),
                len(filtered),
            )

        return filtered

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract hostname from a URL, returning empty string on failure."""
        if not url:
            return ""
        try:
            if "://" not in url:
                url = "http://" + url
            return urlparse(url).hostname or ""
        except Exception:
            return ""
