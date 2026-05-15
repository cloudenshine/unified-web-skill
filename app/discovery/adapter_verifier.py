"""Live verification helpers for bb-browser site adapters."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Any

AdapterRunner = Callable[
    [str, str, str],
    Awaitable[list[dict[str, Any]]],
]


@dataclass(frozen=True)
class AdapterTarget:
    """One concrete bb-browser site adapter command to verify."""

    site: str
    command: str
    query: str

    @property
    def adapter(self) -> str:
        """Return the bb-browser adapter path."""
        return f"{self.site}/{self.command}"


@dataclass(frozen=True)
class AdapterVerificationResult:
    """Verification outcome for one site adapter command."""

    site: str
    command: str
    adapter: str
    query: str
    ok: bool
    quality_status: str
    result_count: int
    duration_ms: float
    error: str

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return asdict(self)


DEFAULT_HARD_ADAPTER_TARGETS: tuple[AdapterTarget, ...] = (
    AdapterTarget(site="reddit", command="search", query="python programming"),
    AdapterTarget(site="youtube", command="search", query="python asyncio"),
    AdapterTarget(site="bilibili", command="search", query="python"),
)


async def verify_adapter(
    target: AdapterTarget,
    runner: Callable[..., Awaitable[list[dict[str, Any]]]],
    *,
    timeout: int = 45,
    min_results: int = 1,
) -> AdapterVerificationResult:
    """Verify one adapter through an injected runner."""
    t0 = time.monotonic()
    try:
        items = await runner(
            target.site,
            target.command,
            target.query,
            timeout=timeout,
        )
        result_count = len(items)
        ok = result_count > 0
        if result_count >= min_results:
            quality_status = "verified"
        elif ok:
            quality_status = "weak"
        else:
            quality_status = "failed"
        error = ""
    except Exception as exc:
        result_count = 0
        ok = False
        quality_status = "failed"
        error = str(exc)

    return AdapterVerificationResult(
        site=target.site,
        command=target.command,
        adapter=target.adapter,
        query=target.query,
        ok=ok,
        quality_status=quality_status,
        result_count=result_count,
        duration_ms=(time.monotonic() - t0) * 1000,
        error=error,
    )


async def verify_adapters(
    targets: Iterable[AdapterTarget],
    runner: Callable[..., Awaitable[list[dict[str, Any]]]],
    *,
    limit: int | None = None,
    timeout: int = 45,
    min_results: int = 1,
) -> list[AdapterVerificationResult]:
    """Verify adapter targets sequentially for predictable provider load."""
    selected = list(targets)
    if limit is not None:
        selected = selected[:limit]

    results: list[AdapterVerificationResult] = []
    for target in selected:
        results.append(
            await verify_adapter(
                target,
                runner,
                timeout=timeout,
                min_results=min_results,
            )
        )
    return results
