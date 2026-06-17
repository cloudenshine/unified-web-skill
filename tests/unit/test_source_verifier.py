import pytest

from app.discovery.source_matrix import SourceEntry
from app.discovery.source_verifier import (
    SourceVerificationResult,
    select_sources,
    verify_source,
    verify_sources,
)
from app.engines.base import FetchResult


def _source(
    source_id: str = "docs_example",
    *,
    site_id: str = "example",
    display_name: str = "Example",
    category: str = "docs",
    verification_url: str = "https://example.com/docs",
    access_type: str = "static_html",
    preferred_provider: str = "scrapling",
    cost_tier: str = "low",
    promotion_status: str = "verified_candidate",
) -> SourceEntry:
    return SourceEntry(
        source_id=source_id,
        site_id=site_id,
        display_name=display_name,
        category=category,
        region="global",
        languages=["en"],
        difficulty="easy",
        verification_url=verification_url,
        expected_provider="scrapling",
        requires_auth=False,
        status="seeded",
        access_type=access_type,
        preferred_provider=preferred_provider,
        fallback_providers=[],
        cost_tier=cost_tier,
        stability_tier="stable",
        promotion_status=promotion_status,
        failure_modes=["timeout", "empty_content"],
    )


async def _ok_fetcher(url: str, *, timeout: int, preferred_provider: str):
    return FetchResult(
        ok=True,
        url=url,
        status=200,
        text="x" * 500,
        engine="scrapling-http",
        duration_ms=12.5,
    )


async def _short_fetcher(url: str, *, timeout: int, preferred_provider: str):
    return FetchResult(
        ok=True,
        url=url,
        status=200,
        text="short",
        engine="scrapling-http",
        duration_ms=4.0,
    )


async def _fail_fetcher(url: str, *, timeout: int, preferred_provider: str):
    return FetchResult(
        ok=False,
        url=url,
        status=403,
        error="blocked",
        engine="scrapling-http",
        duration_ms=9.0,
    )


def test_source_verification_result_serializes_to_dict():
    result = SourceVerificationResult(
        source_id="docs_example",
        site_id="example",
        category="docs",
        verification_url="https://example.com/docs",
        expected_provider="scrapling",
        ok=True,
        quality_status="verified",
        status_code=200,
        provider="scrapling-http",
        text_length=500,
        duration_ms=12.5,
        error="",
    )

    assert result.to_dict()["quality_status"] == "verified"


def test_select_sources_filters_by_ids_and_categories():
    sources = [
        _source("docs_one"),
        _source(
            source_id="news_one",
            site_id="news",
            display_name="News",
            category="news",
            verification_url="https://example.com/news",
        ),
        _source("docs_two"),
    ]

    selected = select_sources(
        sources,
        source_ids=["docs_two"],
        categories=["news"],
    )

    assert [source.source_id for source in selected] == ["news_one", "docs_two"]


def test_select_sources_filters_by_strategy_fields():
    sources = [
        _source("api_promoted", access_type="api", promotion_status="promoted"),
        _source("rss_promoted", access_type="rss", promotion_status="promoted"),
        _source(
            "browser_promoted",
            access_type="dynamic_browser",
            preferred_provider="opencli",
            promotion_status="promoted",
            cost_tier="medium",
        ),
        _source("api_matrix_only", access_type="api", promotion_status="matrix_only"),
    ]

    selected = select_sources(
        sources,
        access_types=["api", "rss"],
        promotion_statuses=["promoted"],
        cost_tiers=["low"],
        preferred_providers=["scrapling"],
    )

    assert [source.source_id for source in selected] == [
        "api_promoted",
        "rss_promoted",
    ]


@pytest.mark.asyncio
async def test_verify_source_marks_verified_for_enough_text():
    result = await verify_source(_source(), _ok_fetcher, min_text_length=200)

    assert result.ok is True
    assert result.quality_status == "verified"
    assert result.provider == "scrapling-http"
    assert result.text_length == 500


@pytest.mark.asyncio
async def test_verify_source_marks_weak_for_short_text():
    result = await verify_source(_source(), _short_fetcher, min_text_length=200)

    assert result.ok is True
    assert result.quality_status == "weak"
    assert result.text_length == 5


@pytest.mark.asyncio
async def test_verify_source_marks_failed_fetch():
    result = await verify_source(_source(), _fail_fetcher, min_text_length=200)

    assert result.ok is False
    assert result.quality_status == "failed"
    assert result.error == "blocked"


@pytest.mark.asyncio
async def test_verify_sources_respects_limit():
    sources = [_source("one"), _source("two"), _source("three")]

    results = await verify_sources(sources, _ok_fetcher, limit=2)

    assert [result.source_id for result in results] == ["one", "two"]
