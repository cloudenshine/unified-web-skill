"""Tests for RoutingStats — EWMA scoring, domain isolation, reset."""

import sys; sys.path.insert(0, "E:/claude_work/g/unified-web-skill")
from app.engines.routing_stats import RoutingStats


class TestRoutingStats:
    def test_record_success_updates_stats(self):
        rs = RoutingStats()
        rs.record("scrapling", "example.com", True, 200)
        ds = rs.domain_stats("example.com")
        assert ds["scrapling"]["attempts"] == 1
        assert ds["scrapling"]["successes"] == 1

    def test_record_failure_does_not_increment_successes(self):
        rs = RoutingStats()
        rs.record("opencli", "example.com", False, 500)
        ds = rs.domain_stats("example.com")
        assert ds["opencli"]["attempts"] == 1
        assert ds["opencli"]["successes"] == 0

    def test_ewma_latency_converges(self):
        rs = RoutingStats()
        for _ in range(100):
            rs.record("engine", "dom", True, 300)
        ds = rs.domain_stats("dom")
        # EWMA should converge toward 300
        assert abs(ds["engine"]["ewma_latency_ms"] - 300) < 10

    def test_score_cold_start_default(self):
        rs = RoutingStats()
        assert rs.score("unknown", "any.com") == 0.6

    def test_score_high_success_high(self):
        rs = RoutingStats()
        rs.record("e1", "d", True, 100)
        rs.record("e2", "d", False, 100)
        assert rs.score("e1", "d") > rs.score("e2", "d")

    def test_domain_isolation(self):
        rs = RoutingStats()
        rs.record("e", "good.com", True, 100)
        rs.record("e", "bad.com", False, 100)
        assert rs.score("e", "good.com") > rs.score("e", "bad.com")

    def test_engine_summary_aggregates(self):
        rs = RoutingStats()
        rs.record("e", "a.com", True, 100)
        rs.record("e", "b.com", True, 100)
        rs.record("e", "c.com", False, 100)
        s = rs.engine_summary("e")
        assert s["total_attempts"] == 3
        assert s["total_successes"] == 2
        assert abs(s["overall_success_rate"] - 0.667) < 0.001

    def test_reset_clears_entry(self):
        rs = RoutingStats()
        rs.record("e", "d", True, 100)
        assert rs.score("e", "d") != 0.6
        rs.reset("e", "d")
        assert rs.score("e", "d") == 0.6

    def test_update_quality(self):
        rs = RoutingStats()
        rs.record("e", "d", True, 100)
        rs.update_quality("e", "d", 0.9)
        ds = rs.domain_stats("d")
        assert ds["e"]["avg_quality"] == 0.9

    def test_summary_contains_all_entries(self):
        rs = RoutingStats()
        rs.record("a", "x.com", True, 100)
        rs.record("b", "y.com", False, 200)
        s = rs.summary()
        assert "a" in s
        assert "b" in s
