"""Source leaderboard — quality ranking and performance tracking.

Aggregates verification results, latency data, and stability scores into
a ranked source leaderboard. Integrates with RoutingStats for live data.

ponytail: in-memory ranking, persists to JSON on save(). Upgrade path:
add SQLite backend for historical trend analysis.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class SourceScore:
    """Quality score for a single source."""
    source_id: str
    site_id: str
    display_name: str
    region: str
    category: str
    difficulty: str
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    stability_score: float = 1.0  # 0.0-1.0
    content_quality: float = 0.5  # 0.0-1.0
    overall_score: float = 0.5
    verified_count: int = 0
    last_verified: float = 0.0
    failure_modes: list[str] = field(default_factory=list)

class SourceLeaderboard:
    """Ranks sources by quality metrics."""

    def __init__(self) -> None:
        self._scores: dict[str, SourceScore] = {}
        self._last_updated: float = 0.0

    def update_from_verification(
        self,
        source_id: str,
        success: bool,
        latency_ms: float,
        quality_score: float = 0.5,
    ) -> None:
        """Update score from a single verification run."""
        if source_id not in self._scores:
            return

        score = self._scores[source_id]
        score.verified_count += 1
        score.last_verified = time.time()

        # EWMA success rate (alpha=0.3)
        alpha = 0.3
        current_sr = 1.0 if success else 0.0
        score.success_rate = alpha * current_sr + (1 - alpha) * score.success_rate

        # EWMA latency
        if latency_ms > 0:
            score.avg_latency_ms = alpha * latency_ms + (1 - alpha) * score.avg_latency_ms

        # Stability: fewer failures = higher stability
        score.stability_score = score.success_rate

        # Content quality (from agent feedback)
        score.content_quality = alpha * quality_score + (1 - alpha) * score.content_quality

        # Overall: weighted composite
        score.overall_score = (
            score.success_rate * 0.4
            + max(0, 1.0 - score.avg_latency_ms / 5000) * 0.25
            + score.stability_score * 0.2
            + score.content_quality * 0.15
        )

    def add_source(self, source_id: str, site_id: str, display_name: str,
                   region: str = "global", category: str = "other",
                   difficulty: str = "medium") -> None:
        """Register a source for tracking."""
        if source_id not in self._scores:
            self._scores[source_id] = SourceScore(
                source_id=source_id, site_id=site_id,
                display_name=display_name, region=region,
                category=category, difficulty=difficulty,
            )

    def get_ranking(self, category: str = "",
                    region: str = "",
                    min_verified: int = 0,
                    top_n: int = 50) -> list[SourceScore]:
        """Return top N sources sorted by overall_score.

        Optionally filter by category, region, or minimum verifications.
        """
        scores = list(self._scores.values())
        if category:
            scores = [s for s in scores if s.category == category]
        if region:
            scores = [s for s in scores if s.region == region]
        if min_verified > 0:
            scores = [s for s in scores if s.verified_count >= min_verified]
        scores.sort(key=lambda s: s.overall_score, reverse=True)
        return scores[:top_n]

    def get_source(self, source_id: str) -> SourceScore | None:
        return self._scores.get(source_id)

    def summary(self) -> dict[str, Any]:
        """Return leaderboard summary for diagnostics."""
        all_scores = list(self._scores.values())
        if not all_scores:
            return {"total_sources": 0}
        avg_score = sum(s.overall_score for s in all_scores) / len(all_scores)
        return {
            "total_sources": len(all_scores),
            "avg_overall_score": round(avg_score, 3),
            "top_source": max(all_scores, key=lambda s: s.overall_score).source_id,
            "bottom_source": min(all_scores, key=lambda s: s.overall_score).source_id,
        }

    def save(self, path: str) -> None:
        """Persist leaderboard to JSON."""
        data = []
        for score in sorted(self._scores.values(), key=lambda s: s.overall_score, reverse=True):
            data.append({
                "source_id": score.source_id,
                "site_id": score.site_id,
                "display_name": score.display_name,
                "region": score.region,
                "category": score.category,
                "difficulty": score.difficulty,
                "success_rate": round(score.success_rate, 3),
                "avg_latency_ms": round(score.avg_latency_ms, 1),
                "stability_score": round(score.stability_score, 3),
                "content_quality": round(score.content_quality, 3),
                "overall_score": round(score.overall_score, 3),
                "verified_count": score.verified_count,
                "last_verified": score.last_verified,
            })
        Path(path).write_text(json.dumps(data, indent=2))
        logger.info("Saved leaderboard: %d sources to %s", len(data), path)

    def load(self, path: str) -> None:
        """Load leaderboard from JSON."""
        if not Path(path).exists():
            return
        data = json.loads(Path(path).read_text())
        for item in data:
            score = SourceScore(
                source_id=item["source_id"], site_id=item["site_id"],
                display_name=item["display_name"], region=item["region"],
                category=item["category"], difficulty=item["difficulty"],
                success_rate=item["success_rate"],
                avg_latency_ms=item["avg_latency_ms"],
                stability_score=item["stability_score"],
                content_quality=item["content_quality"],
                overall_score=item["overall_score"],
                verified_count=item["verified_count"],
                last_verified=item["last_verified"],
            )
            self._scores[score.source_id] = score
        logger.info("Loaded leaderboard: %d sources from %s", len(data), path)
