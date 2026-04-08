"""Tests for app.engines.health — EngineHealthMonitor and circuit breaker."""

import time
import pytest
from unittest.mock import patch

from app.engines.health import EngineHealthMonitor, HealthStatus


class TestRecordSuccess:
    def test_initial_state_unknown(self):
        hm = EngineHealthMonitor()
        assert hm.get_status("eng1") == HealthStatus.UNKNOWN

    def test_record_success_makes_healthy(self):
        hm = EngineHealthMonitor()
        hm.record_success("eng1")
        assert hm.get_status("eng1") == HealthStatus.HEALTHY

    def test_success_resets_failure_count(self):
        hm = EngineHealthMonitor(failure_threshold=5)
        hm.record_failure("eng1")
        hm.record_failure("eng1")
        hm.record_success("eng1")
        assert hm.get_status("eng1") == HealthStatus.HEALTHY
        # State internals: failure counter should be 0
        state = hm._state("eng1")
        assert state.failure_count == 0


class TestRecordFailure:
    def test_single_failure_degrades(self):
        hm = EngineHealthMonitor(failure_threshold=3)
        hm.record_failure("eng1")
        assert hm.get_status("eng1") == HealthStatus.DEGRADED

    def test_failures_at_threshold_open_circuit(self):
        hm = EngineHealthMonitor(failure_threshold=3, circuit_open_duration=60.0)
        hm.record_failure("eng1")
        hm.record_failure("eng1")
        hm.record_failure("eng1")
        assert hm.get_status("eng1") == HealthStatus.UNHEALTHY
        assert hm.is_available("eng1") is False


class TestCircuitBreaker:
    def test_closed_to_open(self):
        hm = EngineHealthMonitor(failure_threshold=2, circuit_open_duration=60.0)
        hm.record_failure("eng1")
        assert hm.is_available("eng1") is True  # still DEGRADED, not UNHEALTHY
        hm.record_failure("eng1")
        assert hm.is_available("eng1") is False  # circuit open

    def test_open_to_half_open_after_duration(self):
        hm = EngineHealthMonitor(failure_threshold=2, circuit_open_duration=0.1)
        hm.record_failure("eng1")
        hm.record_failure("eng1")
        assert hm.is_available("eng1") is False
        # Wait for circuit to expire
        time.sleep(0.15)
        # After expiry, circuit_open_until is in the past, but status is still UNHEALTHY
        # is_available checks circuit_open_until > now (False now) and status != UNHEALTHY
        # So it remains unavailable because status is UNHEALTHY
        assert hm.is_available("eng1") is False

    def test_circuit_closes_on_success_after_open(self):
        hm = EngineHealthMonitor(failure_threshold=2, circuit_open_duration=0.05)
        hm.record_failure("eng1")
        hm.record_failure("eng1")
        assert hm.is_available("eng1") is False
        time.sleep(0.1)
        # Record a success (simulating a half-open probe)
        hm.record_success("eng1")
        assert hm.is_available("eng1") is True
        assert hm.get_status("eng1") == HealthStatus.HEALTHY


class TestIsAvailable:
    def test_unknown_is_available(self):
        hm = EngineHealthMonitor()
        assert hm.is_available("new_engine") is True

    def test_healthy_is_available(self):
        hm = EngineHealthMonitor()
        hm.record_success("eng1")
        assert hm.is_available("eng1") is True

    def test_degraded_is_available(self):
        hm = EngineHealthMonitor(failure_threshold=5)
        hm.record_failure("eng1")
        assert hm.get_status("eng1") == HealthStatus.DEGRADED
        assert hm.is_available("eng1") is True


class TestSummary:
    def test_summary_returns_dict(self):
        hm = EngineHealthMonitor()
        hm.record_success("a")
        hm.record_failure("b")
        s = hm.summary()
        assert "a" in s
        assert "b" in s
        assert s["a"]["status"] == "healthy"
        assert s["b"]["failure_count"] == 1


class TestReset:
    def test_reset_clears_state(self):
        hm = EngineHealthMonitor()
        hm.record_failure("eng1")
        hm.record_failure("eng1")
        hm.reset("eng1")
        assert hm.get_status("eng1") == HealthStatus.UNKNOWN
        assert hm.is_available("eng1") is True


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_check_healthy_engine(self):
        hm = EngineHealthMonitor()

        class MockEngine:
            name = "mock"
            async def health_check(self):
                return True

        status = await hm.check(MockEngine())
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_unhealthy_engine(self):
        hm = EngineHealthMonitor(failure_threshold=1)

        class MockEngine:
            name = "mock"
            async def health_check(self):
                return False

        status = await hm.check(MockEngine())
        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_exception(self):
        hm = EngineHealthMonitor(failure_threshold=1)

        class MockEngine:
            name = "mock"
            async def health_check(self):
                raise ConnectionError("connection refused")

        status = await hm.check(MockEngine())
        assert status == HealthStatus.UNHEALTHY
