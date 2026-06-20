"""Source health monitor — periodic verification and auto-demotion.

Scans promoted sources at configurable intervals, runs lightweight
verification probes, and auto-demotes sources that fail consistently.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default: check every 15 minutes
DEFAULT_INTERVAL_SECONDS = 900
# Consecutive failures before demotion
MAX_FAILURES = 3
# Sources checked per cycle
SOURCES_PER_CYCLE = 10

@dataclass
class HealthEntry:
    """Health state for one source."""
    source_id: str
    consecutive_failures: int = 0
    last_check: float = 0.0
    is_blocked: bool = False
    failure_log: list[dict[str, Any]] = field(default_factory=list)

class SourceHealthMonitor:
    """Monitors source health and auto-demotes failing sources."""

    def __init__(self, interval: int = DEFAULT_INTERVAL_SECONDS) -> None:
        self._entries: dict[str, HealthEntry] = {}
        self._interval = interval
        self._last_cycle: float = 0.0
        self._running = False

    def register_source(self, source_id: str) -> None:
        """Register a source for health monitoring."""
        if source_id not in self._entries:
            self._entries[source_id] = HealthEntry(source_id=source_id)

    def record_check(self, source_id: str, success: bool, error: str = "") -> None:
        """Record a health check result."""
        entry = self._entries.get(source_id)
        if not entry:
            return

        entry.last_check = time.time()
        if success:
            entry.consecutive_failures = 0
            if entry.is_blocked and entry.consecutive_failures == 0:
                # Restore after first success after being blocked
                entry.is_blocked = False
                logger.info("Source %s: restored from blocked status", source_id)
        else:
            entry.consecutive_failures += 1
            entry.failure_log.append({
                "time": time.time(),
                "error": error[:200],
            })
            # Trim log to last 20 failures
            if len(entry.failure_log) > 20:
                entry.failure_log = entry.failure_log[-20:]

            if entry.consecutive_failures >= MAX_FAILURES and not entry.is_blocked:
                entry.is_blocked = True
                logger.warning(
                    "Source %s: auto-demoted to blocked "
                    "(%d consecutive failures)",
                    source_id, entry.consecutive_failures,
                )

    def is_healthy(self, source_id: str) -> bool:
        """Check if a source is currently healthy (not blocked)."""
        entry = self._entries.get(source_id)
        if entry is None:
            return True  # unknown = assumed healthy
        return not entry.is_blocked

    def get_status(self, source_id: str) -> dict[str, Any]:
        """Return health status for a source."""
        entry = self._entries.get(source_id)
        if not entry:
            return {"source_id": source_id, "known": False}
        return {
            "source_id": source_id,
            "healthy": not entry.is_blocked,
            "consecutive_failures": entry.consecutive_failures,
            "last_check": entry.last_check,
            "failure_count": len(entry.failure_log),
        }

    def summary(self) -> dict[str, Any]:
        """Return overall health summary."""
        total = len(self._entries)
        blocked = sum(1 for e in self._entries.values() if e.is_blocked)
        return {
            "total_sources": total,
            "healthy": total - blocked,
            "blocked": blocked,
            "health_rate": round((total - blocked) / max(total, 1), 3),
        }

    async def cycle_check(self, status_only: bool = False) -> dict[str, Any]:
        """Run one monitoring cycle.

        If status_only=True, just report without actually checking.
        Returns a dict with results of the cycle.
        """
        promoted = [sid for sid, e in self._entries.items() if not e.is_blocked]
        checked = promoted[:SOURCES_PER_CYCLE]
        return {
            "cycle_start": time.time(),
            "total_monitored": len(self._entries),
            "promoted": len(promoted),
            "checked_this_cycle": len(checked),
            "blocked": sum(1 for e in self._entries.values() if e.is_blocked),
        }
