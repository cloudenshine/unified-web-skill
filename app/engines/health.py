"""Health-check utilities with circuit-breaker pattern.

Provides :class:`EngineHealthMonitor` which tracks per-engine availability,
records successes / failures, and opens a *circuit breaker* after consecutive
failures so the router can skip unhealthy engines without waiting for their
(likely-to-timeout) health probe.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import Engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CHECK_INTERVAL: int = 300        # seconds between periodic checks
_FAILURE_THRESHOLD: int = 3               # consecutive failures to trip breaker
_CIRCUIT_OPEN_DURATION: float = 60.0      # seconds the circuit stays open
_HALF_OPEN_PROBE_LIMIT: int = 1           # probes allowed in half-open state


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------

class HealthStatus(enum.Enum):
    """Possible health states for an engine."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class _EngineState:
    """Internal bookkeeping for a single engine's health."""

    status: HealthStatus = HealthStatus.UNKNOWN
    failure_count: int = 0
    success_count: int = 0
    last_check: float = 0.0
    circuit_open_until: float = 0.0
    last_error: str = ""


# ---------------------------------------------------------------------------
# EngineHealthMonitor
# ---------------------------------------------------------------------------

class EngineHealthMonitor:
    """Periodic health monitoring with circuit-breaker pattern.

    The monitor keeps per-engine state so that the :class:`EngineManager`
    can quickly decide whether an engine should be attempted.

    **Circuit-breaker states:**

    * **Closed** — engine is presumed healthy; every failure increments a
      counter.
    * **Open** — engine has exceeded the failure threshold; all requests
      are short-circuited until ``circuit_open_until`` expires.
    * **Half-open** — the open period has elapsed; the next single probe
      is allowed through.  On success the circuit closes; on failure it
      re-opens.

    Parameters
    ----------
    check_interval:
        Minimum seconds between automatic health-check calls for an engine.
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    circuit_open_duration:
        Seconds the circuit remains open before transitioning to half-open.
    """

    def __init__(
        self,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
        failure_threshold: int = _FAILURE_THRESHOLD,
        circuit_open_duration: float = _CIRCUIT_OPEN_DURATION,
    ) -> None:
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.circuit_open_duration = circuit_open_duration

        self._states: dict[str, _EngineState] = {}

    # -- internal helpers ---------------------------------------------------

    def _state(self, engine_name: str) -> _EngineState:
        """Get or create the state entry for *engine_name*."""
        if engine_name not in self._states:
            self._states[engine_name] = _EngineState()
        return self._states[engine_name]

    # -- public API ---------------------------------------------------------

    async def check(self, engine: "Engine") -> HealthStatus:
        """Run a health check for *engine* and update internal state.

        Respects the circuit-breaker: if the circuit is open the check is
        skipped and :attr:`HealthStatus.UNHEALTHY` is returned immediately.
        """
        name = engine.name
        state = self._state(name)
        now = time.monotonic()

        # Circuit open → skip probe
        if state.circuit_open_until > now:
            logger.debug(
                "Circuit open for %s — skipping health check (%.1fs remaining)",
                name,
                state.circuit_open_until - now,
            )
            return HealthStatus.UNHEALTHY

        # Throttle: don't re-check too frequently
        if (
            state.status != HealthStatus.UNKNOWN
            and (now - state.last_check) < self.check_interval
        ):
            return state.status

        try:
            healthy = await engine.health_check()
        except Exception as exc:
            logger.warning("Health check raised for %s: %s", name, exc)
            healthy = False
            state.last_error = str(exc)

        state.last_check = now

        if healthy:
            self.record_success(name)
        else:
            self.record_failure(name)

        return state.status

    def is_available(self, engine_name: str) -> bool:
        """Return ``True`` if the engine is considered reachable.

        An engine is *available* when its circuit is not open and its last
        known status is not :attr:`HealthStatus.UNHEALTHY`.
        """
        state = self._state(engine_name)
        now = time.monotonic()

        if state.circuit_open_until > now:
            return False

        return state.status not in (HealthStatus.UNHEALTHY,)

    def record_failure(self, engine_name: str) -> None:
        """Record a failed operation or health check for *engine_name*.

        Opens the circuit breaker when consecutive failures reach the
        threshold.
        """
        state = self._state(engine_name)
        state.failure_count += 1
        state.success_count = 0

        if state.failure_count >= self.failure_threshold:
            state.status = HealthStatus.UNHEALTHY
            state.circuit_open_until = (
                time.monotonic() + self.circuit_open_duration
            )
            logger.warning(
                "Circuit OPEN for engine %s after %d consecutive failures "
                "(cooldown %.0fs)",
                engine_name,
                state.failure_count,
                self.circuit_open_duration,
            )
        else:
            state.status = HealthStatus.DEGRADED
            logger.info(
                "Engine %s degraded (%d/%d failures)",
                engine_name,
                state.failure_count,
                self.failure_threshold,
            )

    def record_success(self, engine_name: str) -> None:
        """Record a successful operation for *engine_name*.

        Resets the failure counter and closes the circuit breaker if it was
        open or half-open.
        """
        state = self._state(engine_name)

        if state.circuit_open_until > 0:
            logger.info("Circuit CLOSED for engine %s after successful probe", engine_name)

        state.failure_count = 0
        state.success_count += 1
        state.circuit_open_until = 0.0
        state.status = HealthStatus.HEALTHY
        state.last_error = ""

    def get_status(self, engine_name: str) -> HealthStatus:
        """Return current status without performing a check."""
        return self._state(engine_name).status

    def summary(self) -> dict[str, dict[str, Any]]:
        """Return a JSON-friendly summary of all tracked engines."""
        out: dict[str, dict[str, Any]] = {}
        now = time.monotonic()
        for name, st in self._states.items():
            out[name] = {
                "status": st.status.value,
                "failure_count": st.failure_count,
                "circuit_open": st.circuit_open_until > now,
                "last_error": st.last_error,
            }
        return out

    def reset(self, engine_name: str) -> None:
        """Manually reset an engine's health state (e.g. after config change)."""
        if engine_name in self._states:
            self._states[engine_name] = _EngineState()
            logger.info("Health state reset for engine %s", engine_name)
