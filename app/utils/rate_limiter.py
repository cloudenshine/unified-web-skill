"""Per-domain rate limiter with token bucket algorithm."""
import asyncio
import time
import logging
from collections import defaultdict

class DomainRateLimiter:
    """Rate limiter with per-domain tracking and configurable QPS."""
    
    def __init__(self, default_qps: float = 2.0):
        self._default_qps = default_qps
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._logger = logging.getLogger(__name__)
    
    async def acquire(self, domain: str, qps: float | None = None) -> None:
        """Wait until rate limit allows a request to this domain."""
        qps = qps or self._default_qps
        interval = 1.0 / qps
        async with self._locks[domain]:
            now = time.monotonic()
            last = self._last_request.get(domain, 0)
            wait = interval - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[domain] = time.monotonic()
    
    def reset(self, domain: str | None = None) -> None:
        """Reset rate limit state."""
        if domain:
            self._last_request.pop(domain, None)
        else:
            self._last_request.clear()
