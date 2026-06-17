"""Unified engine abstraction layer for unified-web-skill v3.0.

This package exposes the protocol, data models, base class, health
monitor, and manager needed to integrate multiple web-fetching backends
(OpenCLI, Scrapling, and CloakBrowser) under a single routing interface.
"""

from .base import (
    BaseEngine,
    Capability,
    Engine,
    FetchResult,
    InteractResult,
    SearchResult,
)
from .cloak_browser import CloakBrowserEngine
from .health import EngineHealthMonitor, HealthStatus
from .manager import EngineManager, SmartRouter
from ..discovery.site_registry import SiteRegistry

__all__ = [
    "Capability",
    "Engine",
    "BaseEngine",
    "FetchResult",
    "SearchResult",
    "InteractResult",
    "EngineHealthMonitor",
    "HealthStatus",
    "EngineManager",
    "SmartRouter",
    "SiteRegistry",
    "CloakBrowserEngine",
]


