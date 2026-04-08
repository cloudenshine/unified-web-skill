"""
Discovery layer for unified-web-skill v3.0.

Handles search/discovery of URLs, intent classification,
query expansion, and the site capability registry.
"""

from .intent_classifier import IntentClassifier, QueryIntent
from .multi_source import MultiSourceDiscovery
from .query_planner import QueryPlanner
from .site_registry import SiteCapability, SiteRegistry

__all__ = [
    "MultiSourceDiscovery",
    "IntentClassifier",
    "QueryIntent",
    "QueryPlanner",
    "SiteRegistry",
    "SiteCapability",
]
