"""Retry utilities with exponential backoff and jitter."""
import asyncio
import random
import logging
from dataclasses import dataclass
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')
_logger = logging.getLogger(__name__)

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: tuple[type[Exception], ...] = (Exception,)

    def delay_for_attempt(self, attempt: int) -> float:
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay

async def retry_with_backoff(fn: Callable[..., Awaitable[T]], *args,
                              policy: RetryPolicy | None = None, **kwargs) -> T:
    """Execute async function with retry and exponential backoff."""
    policy = policy or RetryPolicy()
    last_error = None
    for attempt in range(policy.max_attempts):
        try:
            return await fn(*args, **kwargs)
        except policy.retryable_errors as e:
            last_error = e
            if attempt < policy.max_attempts - 1:
                delay = policy.delay_for_attempt(attempt)
                _logger.warning(f"Attempt {attempt+1}/{policy.max_attempts} failed: {e}. Retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
    raise last_error  # type: ignore
