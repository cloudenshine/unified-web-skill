"""tests/test_rate_limiter.py"""
import asyncio
import time
import pytest
from app.rate_limiter import DomainRateLimiter


class TestDomainRateLimiter:
    def test_first_request_no_wait(self):
        limiter = DomainRateLimiter(default_qps=2.0)

        async def run():
            waited = await limiter.acquire("example.com")
            return waited

        waited = asyncio.run(run())
        assert waited == 0.0

    def test_second_request_waits(self):
        limiter = DomainRateLimiter(default_qps=2.0)  # 0.5s interval

        async def run():
            await limiter.acquire("example.com")
            t0 = time.monotonic()
            waited = await limiter.acquire("example.com")
            elapsed = time.monotonic() - t0
            return waited, elapsed

        waited, elapsed = asyncio.run(run())
        assert waited > 0
        # Should have waited roughly 0.5s (allow some tolerance)
        assert elapsed >= 0.3

    def test_different_domains_no_interference(self):
        limiter = DomainRateLimiter(default_qps=1.0)  # 1s interval

        async def run():
            await limiter.acquire("site-a.com")
            t0 = time.monotonic()
            waited = await limiter.acquire("site-b.com")  # different domain
            elapsed = time.monotonic() - t0
            return waited, elapsed

        waited, elapsed = asyncio.run(run())
        assert waited == 0.0
        assert elapsed < 0.1  # no wait for different domain

    def test_reset_domain(self):
        limiter = DomainRateLimiter(default_qps=1.0)

        async def run():
            await limiter.acquire("example.com")
            limiter.reset("example.com")
            waited = await limiter.acquire("example.com")
            return waited

        waited = asyncio.run(run())
        assert waited == 0.0

    def test_reset_all(self):
        limiter = DomainRateLimiter(default_qps=2.0)

        async def run():
            await limiter.acquire("a.com")
            await limiter.acquire("b.com")
            limiter.reset()
            w1 = await limiter.acquire("a.com")
            w2 = await limiter.acquire("b.com")
            return w1, w2

        w1, w2 = asyncio.run(run())
        assert w1 == 0.0
        assert w2 == 0.0

    def test_custom_qps_override(self):
        limiter = DomainRateLimiter(default_qps=10.0)

        async def run():
            await limiter.acquire("example.com", qps=1.0)  # custom: 1s interval
            t0 = time.monotonic()
            waited = await limiter.acquire("example.com", qps=1.0)
            elapsed = time.monotonic() - t0
            return waited, elapsed

        waited, elapsed = asyncio.run(run())
        assert waited > 0
        assert elapsed >= 0.8  # close to 1s
