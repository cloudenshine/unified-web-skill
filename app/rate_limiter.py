"""rate_limiter.py — Per-domain QPS 令牌桶"""
import asyncio
import time
from collections import defaultdict


class DomainRateLimiter:
    """每域名独立令牌桶，防止单域名过载"""

    def __init__(self, default_qps: float = 1.0):
        self._qps = default_qps
        self._last: dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str, qps: float | None = None) -> float:
        """等待直到可以请求该域名，返回实际等待秒数"""
        rate = qps or self._qps
        min_interval = 1.0 / rate
        async with self._lock:
            now = time.monotonic()
            wait = self._last[domain] + min_interval - now
            if wait > 0:
                await asyncio.sleep(wait)
                waited = wait
            else:
                waited = 0.0
            self._last[domain] = time.monotonic()
        return waited

    def reset(self, domain: str | None = None) -> None:
        """Reset limiter state (useful for tests)"""
        if domain:
            self._last.pop(domain, None)
        else:
            self._last.clear()
