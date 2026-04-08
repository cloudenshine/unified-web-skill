"""Unified engine abstraction layer for unified-web-skill v3.0.

This package exposes the protocol, data models, base class, health
monitor, and manager needed to integrate multiple web-fetching backends
(OpenCLI, Scrapling, Lightpanda, PinchTab, bb-browser, CLIBrowser)
under a single routing interface.

Quick start::

    from app.engines import EngineManager, Capability, FetchResult

    mgr = EngineManager()
    mgr.register(my_engine)
    result = await mgr.fetch_with_fallback("https://example.com")
"""

from .base import (
    BaseEngine,
    Capability,
    Engine,
    FetchResult,
    InteractResult,
    SearchResult,
)
from .health import EngineHealthMonitor, HealthStatus
from .manager import EngineManager, SiteRegistry, SmartRouter

__all__ = [
    # base protocol & data models
    "Capability",
    "Engine",
    "BaseEngine",
    "FetchResult",
    "SearchResult",
    "InteractResult",
    # health
    "EngineHealthMonitor",
    "HealthStatus",
    # manager & routing
    "EngineManager",
    "SmartRouter",
    "SiteRegistry",
]
