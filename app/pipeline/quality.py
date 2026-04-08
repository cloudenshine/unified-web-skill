"""
Content quality validation and deduplication.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

_logger = logging.getLogger(__name__)


class QualityGate:
    """Validates content quality and deduplicates records."""

    def validate(
        self,
        extracted: dict,
        *,
        min_length: int = 100,
        min_credibility: float = 0.3,
        time_window_days: int = 0,
    ) -> tuple[bool, str]:
        """Validate extracted content against quality thresholds.

        Returns (passed: bool, reason: str).
        """
        text = extracted.get("text", "")

        # Length check
        clean_text = re.sub(r"\s+", " ", text).strip()
        if len(clean_text) < min_length:
            return False, f"text too short ({len(clean_text)} < {min_length})"

        # Empty / boilerplate check
        if self._is_boilerplate(clean_text):
            return False, "content appears to be boilerplate"

        # Date freshness check
        if time_window_days > 0:
            date_str = extracted.get("date")
            if date_str:
                too_old, reason = self._check_freshness(date_str, time_window_days)
                if too_old:
                    return False, reason

        return True, "ok"

    def deduplicate(self, records: list) -> tuple[list, int]:
        """Remove duplicate records by content_hash.

        Returns (unique_records, duplicate_count).
        """
        seen: set[str] = set()
        unique: list = []
        for r in records:
            h = r.content_hash
            if h and h in seen:
                continue
            if h:
                seen.add(h)
            unique.append(r)
        return unique, len(records) - len(unique)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_boilerplate(text: str) -> bool:
        """Detect common boilerplate / error pages."""
        lower = text.lower()
        boilerplate_markers = [
            "access denied",
            "page not found",
            "404 not found",
            "403 forbidden",
            "enable javascript",
            "please enable cookies",
            "checking your browser",
            "just a moment",
            "attention required",
        ]
        # If the entire text is dominated by a boilerplate phrase
        for marker in boilerplate_markers:
            if marker in lower and len(text) < 500:
                return True
        return False

    @staticmethod
    def _check_freshness(date_str: str, max_age_days: int) -> tuple[bool, str]:
        """Check whether a date string is within the allowed time window.

        Returns (is_too_old: bool, reason: str).
        """
        try:
            # Parse ISO-8601 date (YYYY-MM-DD or full timestamp)
            clean = date_str.strip()
            if "T" in clean:
                # Full ISO timestamp — handle timezone
                clean = clean.replace("Z", "+00:00")
                # Remove trailing timezone name if present
                clean = re.sub(r"\s+\w+/\w+$", "", clean)
                dt = datetime.fromisoformat(clean)
            else:
                # Date only
                dt = datetime.strptime(clean[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)

            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            if dt < cutoff:
                age_days = (datetime.now(timezone.utc) - dt).days
                return True, f"content too old ({age_days} days > {max_age_days})"

        except (ValueError, TypeError) as exc:
            _logger.debug("could not parse date '%s': %s", date_str, exc)
            # If we can't parse the date, don't reject — let it through

        return False, "ok"
