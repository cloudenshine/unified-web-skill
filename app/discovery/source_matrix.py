"""Global source coverage matrix for benchmark and promotion planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


VALID_ACCESS_TYPES = {
    "api",
    "rss",
    "static_html",
    "structured_adapter",
    "dynamic_browser",
    "interactive_session",
    "boundary",
}

VALID_PROVIDERS = {
    "scrapling",
    "opencli",
}

VALID_COST_TIERS = {"low", "medium", "high"}
VALID_STABILITY_TIERS = {"stable", "variable", "fragile"}
VALID_PROMOTION_STATUSES = {
    "matrix_only",
    "verified_candidate",
    "promoted",
    "blocked",
}
VALID_FAILURE_MODES = {
    "timeout",
    "blocked",
    "auth_required",
    "captcha",
    "empty_content",
    "adapter_changed",
    "parser_changed",
    "dynamic_required",
    "rate_limited",
}


@dataclass(frozen=True)
class SourceEntry:
    """Representative source tracked by the global coverage matrix."""

    source_id: str
    site_id: str
    display_name: str
    category: str
    region: str
    languages: list[str]
    difficulty: str
    verification_url: str
    expected_provider: str
    requires_auth: bool
    status: str
    access_type: str
    preferred_provider: str
    fallback_providers: list[str]
    cost_tier: str
    stability_tier: str
    promotion_status: str
    failure_modes: list[str]
    notes: str = ""


class SourceMatrix:
    """Load and query global coverage matrix entries."""

    def __init__(self, sources: list[SourceEntry]) -> None:
        self._sources = sources

    @classmethod
    def load_builtin(cls) -> SourceMatrix:
        """Load the built-in global source seed matrix."""
        path = Path(__file__).parent / "global_sources.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls([SourceEntry(**entry) for entry in data])

    def all_sources(self) -> list[SourceEntry]:
        """Return every source entry."""
        return list(self._sources)

    def verified_sources(self) -> list[SourceEntry]:
        """Return entries whose status is verified."""
        return [source for source in self._sources if source.status == "verified"]

    def sources_by_category(self, category: str) -> list[SourceEntry]:
        """Return entries for one source category."""
        return [source for source in self._sources if source.category == category]

    def coverage_summary(self) -> dict[str, set[str] | int]:
        """Return high-level coverage dimensions."""
        languages = {
            language
            for source in self._sources
            for language in source.languages
        }
        return {
            "total": len(self._sources),
            "categories": {source.category for source in self._sources},
            "regions": {source.region for source in self._sources},
            "languages": languages,
            "difficulties": {source.difficulty for source in self._sources},
        }

