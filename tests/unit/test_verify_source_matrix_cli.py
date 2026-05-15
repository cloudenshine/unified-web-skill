import pytest

from app.engines.manager import EngineManager
from verify_source_matrix import (
    _build_parser,
    _exit_code_for_summary,
    _fetch_matrix_url,
    _resolve_regression_profile,
)

from .conftest import FailingEngine, StubEngine


@pytest.mark.asyncio
async def test_fetch_matrix_url_strict_uses_only_preferred_provider():
    mgr = EngineManager()
    mgr.register(FailingEngine("scrapling"))
    mgr.register(StubEngine("bb-browser"))

    result = await _fetch_matrix_url(
        mgr,
        "https://example.com",
        timeout=5,
        preferred_provider="scrapling",
        strict_preferred_provider=True,
    )

    assert result.ok is False
    assert result.engine == "scrapling"
    assert result.error == "always fails"


@pytest.mark.asyncio
async def test_fetch_matrix_url_non_strict_keeps_manager_fallback():
    mgr = EngineManager()
    mgr.register(FailingEngine("scrapling"))
    mgr.register(StubEngine("bb-browser"))

    result = await _fetch_matrix_url(
        mgr,
        "https://example.com",
        timeout=5,
        preferred_provider="scrapling",
        strict_preferred_provider=False,
    )

    assert result.ok is True
    assert result.engine == "bb-browser"


def test_regression_profile_applies_promoted_http_defaults():
    parser = _build_parser()
    args = parser.parse_args(["--regression-profile", "promoted-http"])

    _resolve_regression_profile(args)

    assert "academic_arxiv_api_query" in args.exclude_ids
    assert "commerce_openfoodfacts_search" in args.exclude_ids
    assert args.access_types == "api,rss,static_html"
    assert args.promotion_statuses == "promoted"
    assert args.preferred_providers == "scrapling"
    assert args.strict_preferred_provider is True
    assert args.limit == 100
    assert args.timeout == 30
    assert args.output.endswith("source_matrix_regression_promoted_http.json")


def test_regression_profile_keeps_explicit_overrides():
    parser = _build_parser()
    args = parser.parse_args(
        [
            "--regression-profile",
            "special-watch",
            "--limit",
            "2",
            "--output",
            "outputs/custom.json",
        ]
    )

    _resolve_regression_profile(args)

    assert args.ids == "commerce_producthunt,commerce_amazon_search"
    assert args.strict_preferred_provider is True
    assert args.limit == 2
    assert args.output == "outputs/custom.json"


def test_regression_profile_applies_rate_limited_watch_defaults():
    parser = _build_parser()
    args = parser.parse_args(["--regression-profile", "rate-limited-watch"])

    _resolve_regression_profile(args)

    assert args.ids == "academic_arxiv_api_query,commerce_openfoodfacts_search"
    assert args.strict_preferred_provider is True
    assert args.limit == 10
    assert args.timeout == 60
    assert args.output.endswith("source_matrix_regression_rate_limited_watch.json")


def test_fail_on_unverified_returns_failure_for_weak_or_failed_results():
    assert _exit_code_for_summary(
        {"weak": 1, "failed": 0},
        fail_on_unverified=True,
    ) == 1
    assert _exit_code_for_summary(
        {"weak": 0, "failed": 1},
        fail_on_unverified=True,
    ) == 1
    assert _exit_code_for_summary(
        {"weak": 0, "failed": 0},
        fail_on_unverified=True,
    ) == 0


def test_fail_on_unverified_is_opt_in():
    assert _exit_code_for_summary(
        {"weak": 1, "failed": 1},
        fail_on_unverified=False,
    ) == 0
