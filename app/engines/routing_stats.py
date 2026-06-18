"""Per-domain routing statistics with EWMA latency tracking.

Tracks success rate, EWMA latency, and optional quality scores
for each (engine, domain) pair.  Used by SmartRouter to make
adaptive, data-driven engine ordering decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_EWMA_ALPHA = 0.3
_COLD_START_SCORE = 0.6
_LATENCY_INIT = 1000.0


@dataclass
class _Stats:
    attempts: int = 0
    successes: int = 0
    ewma_latency_ms: float = _LATENCY_INIT
    quality_sum: float = 0.0
    quality_count: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.attempts, 1)

    @property
    def avg_quality(self) -> float:
        if self.quality_count:
            return self.quality_sum / self.quality_count
        return 0.0


class RoutingStats:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], _Stats] = {}

    def record(
        self, engine: str, domain: str, success: bool,
        latency_ms: float, quality_score: float = 0.0,
    ) -> None:
        key = (engine, domain)
        st = self._entries.get(key)
        if st is None:
            st = _Stats()
            self._entries[key] = st
        st.attempts += 1
        if success:
            st.successes += 1
        if success:
            st.ewma_latency_ms = (
                _EWMA_ALPHA * latency_ms + (1 - _EWMA_ALPHA) * st.ewma_latency_ms
            )
        if quality_score > 0:
            st.quality_sum += quality_score
            st.quality_count += 1

    def update_quality(self, engine: str, domain: str, quality_score: float) -> None:
        if quality_score <= 0:
            return
        key = (engine, domain)
        st = self._entries.get(key)
        if st is None:
            st = _Stats()
            self._entries[key] = st
        st.quality_sum += quality_score
        st.quality_count += 1

    def score(self, engine: str, domain: str) -> float:
        key = (engine, domain)
        st = self._entries.get(key)
        if st is None:
            return _COLD_START_SCORE
        sr = st.success_rate
        lf = _LATENCY_INIT / (_LATENCY_INIT + st.ewma_latency_ms)
        qf = 1.0
        if st.quality_count:
            qf = 0.8 + 0.4 * (st.avg_quality - 0.5)
        return sr * lf * qf

    def domain_stats(self, domain: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for (eng, dom), st in self._entries.items():
            if dom == domain:
                result[eng] = {
                    "attempts": st.attempts, "successes": st.successes,
                    "success_rate": round(st.success_rate, 3),
                    "ewma_latency_ms": round(st.ewma_latency_ms, 1),
                    "avg_quality": round(st.avg_quality, 3),
                    "score": round(self.score(eng, dom), 3),
                }
        return result

    def engine_summary(self, engine: str) -> dict[str, Any]:
        ta = ts = 0
        for (eng, _), st in self._entries.items():
            if eng == engine:
                ta += st.attempts; ts += st.successes
        return {"total_attempts": ta, "total_successes": ts,
                "overall_success_rate": round(ts / max(ta, 1), 3)}

    def summary(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for (eng, dom), st in self._entries.items():
            result.setdefault(eng, {})[dom] = {
                "attempts": st.attempts, "successes": st.successes,
                "success_rate": round(st.success_rate, 3),
                "ewma_latency_ms": round(st.ewma_latency_ms, 1),
                "score": round(self.score(eng, dom), 3),
            }
        return result

    def reset(self, engine: str, domain: str = "") -> None:
        self._entries = {
            k: v for k, v in self._entries.items()
            if not (k[0] == engine and (not domain or k[1] == domain))
        }