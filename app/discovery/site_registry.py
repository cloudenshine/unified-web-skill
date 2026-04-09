"""
Site capability registry — single source of truth for all known websites.

Maps domains → engines, commands, auth requirements, content types.
Replaces all scattered hardcoded domain lists throughout the old codebase.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)


@dataclass
class SiteCapability:
    """Describes a single website and how to interact with it."""

    site_id: str                                # e.g. "bilibili"
    display_name: str                           # e.g. "哔哩哔哩"
    domains: list[str]                          # e.g. ["bilibili.com", "b23.tv"]
    engines: list[str]                          # priority: ["bb-browser", "opencli", "scrapling"]
    commands: dict[str, str] = field(default_factory=dict)
    auth_required: bool = False
    auth_engine: str = ""                       # "pinchtab" | "bb-browser"
    content_type: str = "article"               # video|article|social|news|paper|code|finance|shopping|search|jobs
    country: str = "global"                     # cn|global|us|jp
    default_fetch_mode: str = "auto"            # http|dynamic|stealth|auto
    notes: str = ""


class SiteRegistry:
    """Singleton registry of all known sites and their capabilities.

    Usage::

        registry = SiteRegistry.get_instance()
        registry.load_builtin()

        cap = registry.lookup_by_url("https://www.bilibili.com/video/BV123")
        print(cap.engines)  # ["bb-browser", "opencli"]
    """

    _instance: Optional[SiteRegistry] = None

    def __init__(self) -> None:
        self._sites: dict[str, SiteCapability] = {}
        self._domain_index: dict[str, str] = {}  # domain → site_id
        self._loaded = False

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> SiteRegistry:
        """Return the global singleton, creating and loading builtins if needed."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load_builtin()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (useful in tests)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_from_file(self, path: str | Path) -> int:
        """Load site definitions from a JSON file.

        The file should contain a list of objects, each matching the
        :class:`SiteCapability` field names.

        Returns
        -------
        int
            Number of sites loaded.
        """
        p = Path(path)
        if not p.exists():
            _logger.warning("site registry file not found: %s", p)
            return 0

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _logger.error("failed to parse site registry file %s: %s", p, exc)
            return 0

        count = 0
        for entry in data:
            try:
                site = SiteCapability(**entry)
                self.register(site)
                count += 1
            except TypeError as exc:
                _logger.warning("skipping invalid site entry: %s", exc)
        self._loaded = True
        _logger.info("loaded %d sites from %s", count, p)
        return count

    def load_builtin(self) -> int:
        """Load the built-in site catalogue from ``sites.json``.

        This is the single source of truth that replaces every scattered
        domain list in the old codebase.

        Returns
        -------
        int
            Number of sites registered.
        """
        return self.load_from_file(Path(__file__).parent / "sites.json")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, site: SiteCapability) -> None:
        """Register (or overwrite) a site capability."""
        self._sites[site.site_id] = site
        for domain in site.domains:
            self._domain_index[domain.lower()] = site.site_id

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def lookup_by_domain(self, domain: str) -> Optional[SiteCapability]:
        """Find a site by domain, supporting subdomain matching.

        Tries an exact hit first, then progressively strips sub-domains.
        For example ``www.bilibili.com`` → ``bilibili.com``.
        """
        domain = domain.lower().rstrip(".")

        # Exact match
        if domain in self._domain_index:
            return self._sites[self._domain_index[domain]]

        # Suffix / parent-domain match
        parts = domain.split(".")
        for i in range(1, len(parts)):
            candidate = ".".join(parts[i:])
            if candidate in self._domain_index:
                return self._sites[self._domain_index[candidate]]

        return None

    def lookup_by_url(self, url: str) -> Optional[SiteCapability]:
        """Extract the domain from *url* and look it up."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or parsed.path.split("/")[0]
        except Exception:
            return None
        if not host:
            return None
        return self.lookup_by_domain(host)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_search_engines(self) -> list[SiteCapability]:
        """Return sites that expose a ``search`` command."""
        return [s for s in self._sites.values() if "search" in s.commands]

    def get_sites_by_country(self, country: str) -> list[SiteCapability]:
        """Filter sites by ``country`` field (e.g. ``"cn"``)."""
        return [s for s in self._sites.values() if s.country == country]

    def get_sites_by_content_type(self, content_type: str) -> list[SiteCapability]:
        """Filter sites by ``content_type`` (e.g. ``"video"``)."""
        return [s for s in self._sites.values() if s.content_type == content_type]

    def get_preferred_engines(self, url: str) -> list[str]:
        """Return the engine priority list for *url*.

        Falls back to ``["scrapling", "http"]`` when the site is unknown.
        """
        cap = self.lookup_by_url(url)
        if cap:
            return list(cap.engines)
        return ["scrapling", "http"]

    def is_chinese_domain(self, url: str) -> bool:
        """``True`` if the URL belongs to a Chinese (``cn``) site."""
        cap = self.lookup_by_url(url)
        return cap is not None and cap.country == "cn"

    def needs_auth(self, url: str) -> bool:
        """``True`` if the site behind *url* requires authentication."""
        cap = self.lookup_by_url(url)
        return cap is not None and cap.auth_required

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @property
    def site_count(self) -> int:
        """Number of registered sites."""
        return len(self._sites)

    def all_sites(self) -> list[SiteCapability]:
        """Return every registered site."""
        return list(self._sites.values())

    def __contains__(self, site_id: str) -> bool:
        return site_id in self._sites

    def __getitem__(self, site_id: str) -> SiteCapability:
        return self._sites[site_id]

