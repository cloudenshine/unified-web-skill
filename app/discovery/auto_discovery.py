"""Auto source discovery — expand coverage from seed URLs.

Uses DuckDuckGo search to find related sources, validates them with a
quick health check, and outputs structured metadata for human review.

ponytail: uses DDGS for discovery (rate-limited, no API key needed).
Ceiling: ~50-100 results per query. Upgrade path: add Google Programmable
Search or Bing API for higher throughput.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredSource:
    """A candidate source discovered from search queries."""
    url: str
    domain: str
    title: str = ""
    snippet: str = ""
    category: str = "other"
    region: str = "global"
    language: str = "en"
    source_query: str = ""
    confidence: float = 0.5  # 0.0-1.0

@dataclass
class DiscoveryResult:
    """Result of a discovery run."""
    query: str
    sources: list[DiscoveredSource] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

# Known domains to skip (already in our registry)
KNOWN_DOMAINS: set[str] = set()

def load_known_domains(sites_path: str) -> None:
    """Load known domains from sites.json to avoid duplicates."""
    global KNOWN_DOMAINS
    try:
        with open(sites_path, "r") as f:
            sites = json.load(f)
        for site in sites:
            for domain in site.get("domains", []):
                KNOWN_DOMAINS.add(domain.lower())
        logger.info("Loaded %d known domains from %s", len(KNOWN_DOMAINS), sites_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Could not load known domains: %s", exc)


# ── Discovery strategies ────────────────────────────────────────────

def discover_from_ddg(
    query: str,
    max_results: int = 15,
    category: str = "other",
    region: str = "global",
    language: str = "en",
) -> DiscoveryResult:
    """Discover sources from DuckDuckGo search results.

    ponytail: synchronous DDGS call. For large-scale discovery, use
    the async DDGS wrapper or a dedicated search API.
    """
    result = DiscoveryResult(query=query)

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        result.errors.append("duckduckgo_search not installed (pip install duckduckgo-search)")
        return result

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        result.errors.append(f"DDGS query failed: {exc}")
        return result

    if not raw_results:
        result.errors.append(f"No results for query: {query}")
        return result

    for item in raw_results:
        url = item.get("href", "") or item.get("link", "")
        if not url:
            continue

        domain = _extract_domain(url)
        if not domain or domain in KNOWN_DOMAINS:
            continue

        # Basic quality filter
        if _is_low_quality(url, item.get("title", "")):
            continue

        source = DiscoveredSource(
            url=url,
            domain=domain,
            title=item.get("title", ""),
            snippet=item.get("body", "") or item.get("snippet", ""),
            category=category,
            region=region,
            language=language,
            source_query=query,
            confidence=0.5,
        )
        result.sources.append(source)

    logger.info("Discovery '%s': found %d new source(s)", query, len(result.sources))
    return result


def discover_for_category(
    category: str,
    max_per_query: int = 10,
) -> list[DiscoveryResult]:
    """Run multiple discovery queries for a category."""
    seed_queries = _category_seeds(category)
    results: list[DiscoveryResult] = []
    for query in seed_queries:
        r = discover_from_ddg(query, max_results=max_per_query, category=category)
        if r.sources:
            results.append(r)
    return results


# ── Output ──────────────────────────────────────────────────────────

def to_global_source_entry(source: DiscoveredSource) -> dict[str, Any]:
    """Convert a DiscoveredSource to a global_sources.json entry draft."""
    expected_provider = "scrapling"
    access_type = "static_html"

    # Heuristic: if the snippet mentions API or the domain looks like an API
    if "api" in source.domain or "api" in source.url:
        expected_provider = "firecrawl"
        access_type = "api"

    return {
        "source_id": f"discovered_{re.sub(r'[^a-z0-9]', '_', source.domain)}",
        "site_id": f"discovered_{re.sub(r'[^a-z0-9]', '_', source.domain)}",
        "display_name": source.title[:60] if source.title else source.domain,
        "category": source.category,
        "region": source.region,
        "languages": [source.language],
        "difficulty": "easy",
        "verification_url": source.url,
        "expected_provider": expected_provider,
        "requires_auth": False,
        "status": "seeded",
        "notes": f"Auto-discovered via: {source.source_query}",
        "access_type": access_type,
        "preferred_provider": expected_provider,
        "fallback_providers": [],
        "cost_tier": "low",
        "stability_tier": "variable",
        "promotion_status": "matrix_only",
        "failure_modes": ["timeout", "empty_content"],
    }


def save_discovered(results: list[DiscoveryResult], output_path: str) -> int:
    """Save discovered sources (deduplicated) to a JSON file for review."""
    seen_domains: set[str] = set()
    entries: list[dict[str, Any]] = []

    for result in results:
        for source in result.sources:
            if source.domain in seen_domains:
                continue
            seen_domains.add(source.domain)
            entries.append(to_global_source_entry(source))

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d discovered source(s) to %s", len(entries), output_path)
    return len(entries)


# ── Helpers ─────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    """Extract clean domain from URL, stripping www."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain
    except Exception:
        return ""

def _is_low_quality(url: str, title: str) -> bool:
    """Filter out low-quality URLs: social media, spam, aggregators."""
    low_quality_domains = {
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "reddit.com", "pinterest.com", "tumblr.com",
        "youtube.com", "tiktok.com",
        "amazon.com", "ebay.com", "aliexpress.com",
        "wikipedia.org",  # already covered
    }
    domain = _extract_domain(url)
    if domain in low_quality_domains:
        return True
    # Skip URLs that are just social media posts
    if not title or len(title) < 5:
        return True
    return False

def _category_seeds(category: str) -> list[str]:
    """Return seed search queries for a content category."""
    seeds: dict[str, list[str]] = {
        "news": [
            "top international news websites",
            "leading newspapers by country",
            "news aggregator sites list",
        ],
        "tech": [
            "technology news websites",
            "developer blogs and tech publications",
            "programming community sites",
        ],
        "academic": [
            "open access academic journals",
            "research paper repositories",
            "scientific publication databases",
        ],
        "docs": [
            "programming language documentation sites",
            "API documentation and developer guides",
            "technical documentation resources",
        ],
        "social": [
            "forum and community websites",
            "question and answer sites",
            "discussion platforms list",
        ],
        "government": [
            "open government data portals",
            "official government websites",
            "public sector information sites",
        ],
        "finance": [
            "financial news and market data",
            "economic indicators websites",
            "stock market analysis sites",
        ],
    }
    return seeds.get(category, [f"best {category} websites list"])
