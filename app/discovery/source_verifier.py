"""Live verification helpers for global source matrix entries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass

from .source_matrix import SourceEntry
from ..engines.base import FetchResult

SourceFetcher = Callable[
    [str],
    Awaitable[FetchResult],
]


@dataclass(frozen=True)
class SourceVerificationResult:
    """Verification outcome for one source matrix entry."""

    source_id: str
    site_id: str
    category: str
    verification_url: str
    expected_provider: str
    ok: bool
    quality_status: str
    status_code: int
    provider: str
    text_length: int
    duration_ms: float
    error: str

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return asdict(self)


async def verify_source(
    source: SourceEntry,
    fetcher: Callable[..., Awaitable[FetchResult]],
    *,
    timeout: int = 20,
    min_text_length: int = 200,
) -> SourceVerificationResult:
    """Verify a single source through an injected fetcher."""
    result = await fetcher(
        source.verification_url,
        timeout=timeout,
        preferred_provider=source.expected_provider,
    )
    text_length = len(result.text or "")
    if not result.ok:
        quality_status = "failed"
    elif text_length < min_text_length:
        quality_status = "weak"
    else:
        quality_status = "verified"

    return SourceVerificationResult(
        source_id=source.source_id,
        site_id=source.site_id,
        category=source.category,
        verification_url=source.verification_url,
        expected_provider=source.expected_provider,
        ok=result.ok,
        quality_status=quality_status,
        status_code=result.status,
        provider=result.engine,
        text_length=text_length,
        duration_ms=result.duration_ms,
        error=result.error,
    )


async def verify_sources(
    sources: Iterable[SourceEntry],
    fetcher: Callable[..., Awaitable[FetchResult]],
    *,
    limit: int | None = None,
    timeout: int = 20,
    min_text_length: int = 200,
) -> list[SourceVerificationResult]:
    """Verify source entries sequentially for predictable provider load."""
    selected = list(sources)
    if limit is not None:
        selected = selected[:limit]

    results: list[SourceVerificationResult] = []
    for source in selected:
        results.append(
            await verify_source(
                source,
                fetcher,
                timeout=timeout,
                min_text_length=min_text_length,
            )
        )
    return results


def select_sources(
    sources: Iterable[SourceEntry],
    *,
    source_ids: list[str] | None = None,
    categories: list[str] | None = None,
    access_types: list[str] | None = None,
    promotion_statuses: list[str] | None = None,
    cost_tiers: list[str] | None = None,
    preferred_providers: list[str] | None = None,
) -> list[SourceEntry]:
    """Select matrix entries by source id and/or category, preserving order."""
    source_id_set = set(source_ids or [])
    category_set = set(categories or [])
    access_type_set = set(access_types or [])
    promotion_status_set = set(promotion_statuses or [])
    cost_tier_set = set(cost_tiers or [])
    preferred_provider_set = set(preferred_providers or [])
    if not any(
        (
            source_id_set,
            category_set,
            access_type_set,
            promotion_status_set,
            cost_tier_set,
            preferred_provider_set,
        )
    ):
        return list(sources)

    selected: list[SourceEntry] = []
    for source in sources:
        if (
            (source_id_set or category_set)
            and source.source_id not in source_id_set
            and source.category not in category_set
        ):
            continue
        if access_type_set and source.access_type not in access_type_set:
            continue
        if (
            promotion_status_set
            and source.promotion_status not in promotion_status_set
        ):
            continue
        if cost_tier_set and source.cost_tier not in cost_tier_set:
            continue
        if (
            preferred_provider_set
            and source.preferred_provider not in preferred_provider_set
        ):
            continue
        selected.append(source)
    return selected
