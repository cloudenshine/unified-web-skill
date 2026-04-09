"""Engine manager, smart router, and fallback orchestration.

This is the *brain* of unified-web-skill's engine layer.  It owns the
registry of engine adapters, decides which engine to try for a given
request, and transparently falls back to the next candidate when one
engine fails.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from .base import (
    BaseEngine,
    Capability,
    Engine,
    FetchResult,
    InteractResult,
    SearchResult,
)
from .health import EngineHealthMonitor, HealthStatus
from ..discovery.site_registry import SiteRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Smart router
# ---------------------------------------------------------------------------

# Default engine priority for plain fetch (no site-registry hit)
_DEFAULT_FETCH_PRIORITY: list[str] = [
    "scrapling",       # HTTP impersonation tier (fastest)
    "lightpanda",      # CDP-based lightweight browser
    "scrapling_pw",    # Scrapling Playwright tier
    "scrapling_stealth",  # Scrapling StealthyFetcher
    "clibrowser",      # zero-dependency CLI fallback
]

# Priority for Chinese-heavy sites (when not in site registry)
_CHINESE_FETCH_PRIORITY: list[str] = [
    "lightpanda",
    "scrapling_pw",
    "scrapling_stealth",
    "scrapling",
    "clibrowser",
]

# Engines that support interactive actions
_INTERACTIVE_ENGINES: list[str] = [
    "pinchtab",
    "bb_browser",
    "lightpanda",
    "scrapling_pw",
]


class SmartRouter:
    """Determine engine priority for a given request.

    The router is a pure function container — it reads registry / health
    data but never mutates engine state.
    """

    def __init__(
        self,
        site_registry: SiteRegistry,
        health_monitor: EngineHealthMonitor,
    ) -> None:
        self._site_registry = site_registry
        self._health = health_monitor

    def _is_chinese_url(self, url: str) -> bool:
        return self._site_registry.is_chinese_domain(url)

    def resolve_fetch_order(
        self,
        url: str,
        available_engines: dict[str, Engine],
        preferred: list[str] | None = None,
    ) -> list[str]:
        """Return an ordered list of engine names to try for fetching *url*.

        Priority logic:

        1. Caller-supplied *preferred* list (if any).
        2. :class:`SiteRegistry` match for the domain.
        3. Chinese-domain heuristic (dynamic renderers first).
        4. Default global priority.

        Engines whose circuit breaker is open or that are not registered
        are silently excluded.
        """
        if preferred:
            order = list(preferred)
        else:
            site_engines = self._site_registry.get_preferred_engines(url)
            # get_preferred_engines returns a default when URL is unknown,
            # so check if it's a real registry hit by looking up the URL.
            cap = self._site_registry.lookup_by_url(url)
            if cap:
                order = site_engines
            elif self._is_chinese_url(url):
                order = list(_CHINESE_FETCH_PRIORITY)
            else:
                order = list(_DEFAULT_FETCH_PRIORITY)

        # Filter to engines that are registered, support FETCH, and healthy
        result: list[str] = []
        seen: set[str] = set()
        for name in order:
            if name in seen:
                continue
            seen.add(name)
            eng = available_engines.get(name)
            if eng is None:
                continue
            if Capability.FETCH not in eng.capabilities:
                continue
            if not self._health.is_available(name):
                logger.debug("Skipping unhealthy engine %s", name)
                continue
            result.append(name)

        # Append any remaining healthy FETCH engines not already listed
        for name, eng in available_engines.items():
            if name in seen:
                continue
            if Capability.FETCH not in eng.capabilities:
                continue
            if not self._health.is_available(name):
                continue
            result.append(name)

        return result

    def resolve_interact_engine(
        self,
        url: str,
        available_engines: dict[str, Engine],
        preferred: str | None = None,
    ) -> str | None:
        """Pick the best engine for interactive actions on *url*."""
        if preferred and preferred in available_engines:
            eng = available_engines[preferred]
            if (
                Capability.INTERACT in eng.capabilities
                and self._health.is_available(preferred)
            ):
                return preferred

        for name in _INTERACTIVE_ENGINES:
            eng = available_engines.get(name)
            if eng is None:
                continue
            if Capability.INTERACT not in eng.capabilities:
                continue
            if not self._health.is_available(name):
                continue
            return name

        return None


# ---------------------------------------------------------------------------
# EngineManager
# ---------------------------------------------------------------------------

class EngineManager:
    """Central façade: engine registration, routing, fetch-with-fallback.

    Typical lifecycle::

        mgr = EngineManager()
        mgr.register(ScraplingEngine())
        mgr.register(LightpandaEngine())
        await mgr.health_check_all()
        result = await mgr.fetch_with_fallback("https://example.com")
    """

    def __init__(self) -> None:
        self._engines: dict[str, Engine] = {}
        self._health_monitor = EngineHealthMonitor()
        self._site_registry = SiteRegistry.get_instance()
        self._router = SmartRouter(self._site_registry, self._health_monitor)

    # -- registration -------------------------------------------------------

    @property
    def site_registry(self) -> SiteRegistry:
        """Expose the site registry for external configuration."""
        return self._site_registry

    @property
    def health_monitor(self) -> EngineHealthMonitor:
        """Expose the health monitor for external inspection."""
        return self._health_monitor

    def register(self, engine: Engine) -> None:
        """Register an engine adapter.

        Overwrites any previously registered engine with the same name.
        """
        self._engines[engine.name] = engine
        logger.info(
            "Registered engine %s (capabilities: %s)",
            engine.name,
            ", ".join(c.value for c in engine.capabilities),
        )

    def unregister(self, name: str) -> None:
        """Remove an engine by name (idempotent)."""
        self._engines.pop(name, None)
        self._health_monitor.reset(name)

    def get_engine(self, name: str) -> Optional[Engine]:
        """Return the engine registered under *name*, or ``None``."""
        return self._engines.get(name)

    def get_engines_with_capability(self, cap: Capability) -> list[Engine]:
        """Return all registered engines that advertise *cap*."""
        return [e for e in self._engines.values() if cap in e.capabilities]

    def list_engines(self) -> dict[str, list[str]]:
        """Return ``{name: [capability, ...]}`` for every registered engine."""
        return {
            name: sorted(c.value for c in eng.capabilities)
            for name, eng in self._engines.items()
        }

    # -- health -------------------------------------------------------------

    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks on every registered engine concurrently.

        Returns ``{engine_name: is_healthy}`` mapping.
        """
        if not self._engines:
            return {}

        async def _check(name: str, engine: Engine) -> tuple[str, bool]:
            status = await self._health_monitor.check(engine)
            return name, status == HealthStatus.HEALTHY

        results = await asyncio.gather(
            *(_check(n, e) for n, e in self._engines.items()),
            return_exceptions=True,
        )

        out: dict[str, bool] = {}
        for item in results:
            if isinstance(item, BaseException):
                logger.error("Health check failed unexpectedly: %s", item)
                continue
            name, healthy = item
            out[name] = healthy
        return out

    # -- fetch with fallback ------------------------------------------------

    async def fetch_with_fallback(
        self,
        url: str,
        *,
        preferred_engines: list[str] | None = None,
        timeout: int = 30,
        no_cache: bool = False,
        **opts: Any,
    ) -> FetchResult:
        """Fetch *url*, trying engines in priority order with automatic fallback.

        Checks cache first (unless *no_cache* is True). On success, stores
        result in cache for future requests.

        Returns a :class:`FetchResult` — **never raises**.
        """
        # Check cache first
        if not no_cache:
            try:
                from .. import cache as _cache
                cached = _cache.get(url)
                if cached:
                    return FetchResult(
                        ok=True, url=url, html=cached.get("html", ""),
                        text=cached.get("text", ""), status=cached.get("status", 200),
                        engine=cached.get("engine", "cache"),
                        metadata={"cached": True},
                    )
            except Exception:
                pass

        order = self._router.resolve_fetch_order(
            url, self._engines, preferred=preferred_engines,
        )

        if not order:
            return FetchResult(
                ok=False,
                url=url,
                error="No engines available for FETCH",
            )

        last_error = ""
        for engine_name in order:
            engine = self._engines[engine_name]
            try:
                logger.debug("Attempting fetch via %s: %s", engine_name, url)
                result = await engine.fetch(url, timeout=timeout, **opts)

                if result.ok:
                    self._health_monitor.record_success(engine_name)
                    result.engine = result.engine or engine_name
                    # Store in cache
                    if not no_cache:
                        try:
                            from .. import cache as _cache
                            _cache.put(url, result.html, result.text,
                                       result.status, result.engine)
                        except Exception:
                            pass
                    return result

                # Engine returned ok=False — treat as soft failure
                last_error = result.error or f"{engine_name} returned ok=False"
                logger.info(
                    "Engine %s soft-failed for %s: %s",
                    engine_name, url, last_error,
                )
                self._health_monitor.record_failure(engine_name)

            except NotImplementedError:
                last_error = f"{engine_name} does not implement fetch"
                logger.debug(last_error)
            except Exception as exc:
                last_error = f"{engine_name} raised {type(exc).__name__}: {exc}"
                logger.warning("Engine %s hard-failed: %s", engine_name, exc)
                self._health_monitor.record_failure(engine_name)

        return FetchResult(
            ok=False,
            url=url,
            error=f"All engines exhausted. Last error: {last_error}",
        )

    # -- search multi -------------------------------------------------------

    async def search_multi(
        self,
        query: str,
        *,
        engines: list[str] | None = None,
        max_results: int = 10,
        language: str = "zh",
        **opts: Any,
    ) -> list[SearchResult]:
        """Search across multiple engines, merge and deduplicate results.

        If *engines* is ``None``, all registered engines with
        :attr:`Capability.SEARCH` are used.

        Results are deduplicated by URL and ordered by credibility
        (descending), then rank (ascending).
        """
        search_engines: list[Engine] = []
        if engines:
            for name in engines:
                eng = self._engines.get(name)
                if eng and Capability.SEARCH in eng.capabilities:
                    search_engines.append(eng)
        else:
            search_engines = self.get_engines_with_capability(Capability.SEARCH)

        if not search_engines:
            logger.warning("No engines with SEARCH capability available")
            return []

        async def _search(engine: Engine) -> list[SearchResult]:
            try:
                return await engine.search(
                    query,
                    max_results=max_results,
                    language=language,
                    **opts,
                )
            except NotImplementedError:
                return []
            except Exception as exc:
                logger.warning(
                    "Search failed on %s: %s", engine.name, exc,
                )
                self._health_monitor.record_failure(engine.name)
                return []

        all_results = await asyncio.gather(
            *(_search(e) for e in search_engines),
        )

        # Flatten and deduplicate by URL
        seen_urls: set[str] = set()
        merged: list[SearchResult] = []
        for batch in all_results:
            for item in batch:
                normalized = item.url.rstrip("/")
                if normalized in seen_urls:
                    continue
                seen_urls.add(normalized)
                merged.append(item)

        # Sort: higher credibility first, then lower rank
        merged.sort(key=lambda r: (-r.credibility, r.rank))
        return merged[:max_results]

    # -- interact -----------------------------------------------------------

    async def interact(
        self,
        url: str,
        actions: list[dict[str, Any]],
        *,
        engine: str | None = None,
        timeout: int = 60,
        **opts: Any,
    ) -> InteractResult:
        """Perform browser interaction using the best available engine.

        Returns an :class:`InteractResult` — **never raises**.
        """
        chosen = self._router.resolve_interact_engine(
            url, self._engines, preferred=engine,
        )

        if chosen is None:
            return InteractResult(
                ok=False,
                url=url,
                error="No engines available for INTERACT",
            )

        eng = self._engines[chosen]
        try:
            logger.debug("Interacting via %s: %s", chosen, url)
            result = await eng.interact(url, actions, timeout=timeout, **opts)
            if result.ok:
                self._health_monitor.record_success(chosen)
            else:
                self._health_monitor.record_failure(chosen)
            result.engine = result.engine or chosen
            return result
        except NotImplementedError:
            return InteractResult(
                ok=False,
                url=url,
                engine=chosen,
                error=f"{chosen} does not implement interact",
            )
        except Exception as exc:
            logger.warning("Interact failed on %s: %s", chosen, exc)
            self._health_monitor.record_failure(chosen)
            return InteractResult(
                ok=False,
                url=url,
                engine=chosen,
                error=f"{chosen} raised {type(exc).__name__}: {exc}",
            )
