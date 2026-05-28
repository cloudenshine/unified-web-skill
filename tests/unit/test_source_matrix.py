from app.discovery.source_matrix import (
    SourceMatrix,
    VALID_ACCESS_TYPES,
    VALID_COST_TIERS,
    VALID_FAILURE_MODES,
    VALID_PROMOTION_STATUSES,
    VALID_PROVIDERS,
    VALID_STABILITY_TIERS,
)


REQUIRED_CATEGORIES = {
    "docs",
    "code",
    "academic",
    "news",
    "social",
    "finance",
    "commerce",
    "search",
    "video",
}


def test_builtin_matrix_loads_seed_sources():
    matrix = SourceMatrix.load_builtin()

    assert len(matrix.all_sources()) >= 100


def test_builtin_matrix_covers_required_categories():
    matrix = SourceMatrix.load_builtin()
    summary = matrix.coverage_summary()

    assert REQUIRED_CATEGORIES.issubset(summary["categories"])
    assert len(summary["regions"]) >= 3


def test_builtin_matrix_has_unique_ids_and_https_verification_urls():
    matrix = SourceMatrix.load_builtin()
    sources = matrix.all_sources()

    ids = [source.source_id for source in sources]
    assert len(ids) == len(set(ids))
    assert all(source.verification_url.startswith("https://") for source in sources)


def test_builtin_matrix_entries_start_seeded():
    matrix = SourceMatrix.load_builtin()

    assert {source.status for source in matrix.all_sources()} == {"seeded"}
    assert matrix.verified_sources() == []


def test_builtin_matrix_has_enough_low_friction_verification_candidates():
    matrix = SourceMatrix.load_builtin()

    low_friction = [
        source
        for source in matrix.all_sources()
        if source.expected_provider == "scrapling" and source.difficulty in {"easy", "medium"}
    ]

    assert len(low_friction) >= 85


def test_sources_by_category_filters_entries():
    matrix = SourceMatrix.load_builtin()

    docs = matrix.sources_by_category("docs")

    assert docs
    assert all(source.category == "docs" for source in docs)


def test_builtin_matrix_entries_include_routing_strategy_fields():
    matrix = SourceMatrix.load_builtin()

    for source in matrix.all_sources():
        assert source.access_type in VALID_ACCESS_TYPES
        assert source.preferred_provider in VALID_PROVIDERS
        assert all(
            provider in VALID_PROVIDERS
            for provider in source.fallback_providers
        )
        assert source.cost_tier in VALID_COST_TIERS
        assert source.stability_tier in VALID_STABILITY_TIERS
        assert source.promotion_status in VALID_PROMOTION_STATUSES
        assert all(mode in VALID_FAILURE_MODES for mode in source.failure_modes)
        assert source.expected_provider == source.preferred_provider


def test_builtin_matrix_keeps_lightweight_global_backbone():
    matrix = SourceMatrix.load_builtin()

    lightweight = [
        source
        for source in matrix.all_sources()
        if source.access_type in {"api", "rss", "static_html"}
        and source.preferred_provider == "scrapling"
        and source.cost_tier == "low"
    ]

    assert len(lightweight) >= 85


def test_browser_or_boundary_sources_are_not_auto_promoted():
    matrix = SourceMatrix.load_builtin()

    sensitive_sources = [
        source
        for source in matrix.all_sources()
        if source.access_type in {
            "dynamic_browser",
            "interactive_session",
            "boundary",
        }
    ]

    assert sensitive_sources
    assert all(
        source.promotion_status in {"matrix_only", "blocked"}
        for source in sensitive_sources
    )


def test_matrix_has_no_unresolved_verified_candidates():
    matrix = SourceMatrix.load_builtin()

    unresolved = [
        source.source_id
        for source in matrix.all_sources()
        if source.promotion_status == "verified_candidate"
    ]

    assert unresolved == []


def test_scrapling_blocked_sources_use_browser_provider_path():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    for source_id in {
        "code_stackoverflow_python_asyncio",
        "news_reuters_world",
    }:
        source = sources[source_id]
        assert source.expected_provider == "bb-browser"
        assert source.preferred_provider == "bb-browser"
        assert source.cost_tier == "medium"
        assert "scrapling" in source.fallback_providers


def test_matrix_only_dynamic_refresh_classification():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    duckduckgo = sources["search_duckduckgo_python"]
    assert duckduckgo.expected_provider == "bb-browser"
    assert duckduckgo.preferred_provider == "bb-browser"
    assert "scrapling" in duckduckgo.fallback_providers
    assert duckduckgo.promotion_status == "matrix_only"

    producthunt = sources["commerce_producthunt"]
    assert producthunt.promotion_status == "blocked"
    assert producthunt.stability_tier == "fragile"
    assert "blocked" in producthunt.failure_modes


def test_verified_boundary_sources_remain_isolated_from_promotion():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    amazon = sources["commerce_amazon_search"]

    assert amazon.access_type == "boundary"
    assert amazon.preferred_provider == "bb-browser"
    assert amazon.cost_tier == "high"
    assert amazon.promotion_status == "matrix_only"


def test_arxiv_structured_source_uses_verified_browser_path():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    arxiv = sources["academic_arxiv_cs_ai"]

    assert arxiv.access_type == "structured_adapter"
    assert arxiv.expected_provider == "bb-browser"
    assert arxiv.preferred_provider == "bb-browser"
    assert "opencli" in arxiv.fallback_providers
    assert arxiv.promotion_status == "promoted"


def test_reddit_structured_source_is_matrix_only_when_login_is_required():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    reddit = sources["social_reddit_programming"]

    assert reddit.access_type == "structured_adapter"
    assert reddit.preferred_provider == "bb-browser"
    assert reddit.requires_auth is True
    assert reddit.promotion_status == "matrix_only"
    assert "auth_required" in reddit.failure_modes


def test_stackoverflow_browser_source_is_matrix_only_when_cloudflare_blocks():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    stackoverflow = sources["code_stackoverflow_python_asyncio"]

    assert stackoverflow.preferred_provider == "bb-browser"
    assert stackoverflow.promotion_status == "matrix_only"
    assert "blocked" in stackoverflow.failure_modes


def test_npm_source_uses_registry_api_for_stable_promoted_http_checks():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    npm = sources["code_npm_react"]

    assert npm.preferred_provider == "scrapling"
    assert npm.access_type == "api"
    assert npm.verification_url == "https://registry.npmjs.org/react/latest"
    assert npm.promotion_status == "promoted"


def test_rate_limited_or_volatile_api_sources_are_not_in_strict_promoted_http_batch():
    matrix = SourceMatrix.load_builtin()
    sources = {source.source_id: source for source in matrix.all_sources()}

    arxiv_api = sources["academic_arxiv_api_query"]
    openfoodfacts = sources["commerce_openfoodfacts_search"]

    assert arxiv_api.access_type == "api"
    assert arxiv_api.promotion_status == "matrix_only"
    assert arxiv_api.stability_tier == "variable"
    assert "rate_limited" in arxiv_api.failure_modes
    assert openfoodfacts.access_type == "api"
    assert openfoodfacts.promotion_status == "matrix_only"
    assert openfoodfacts.stability_tier == "variable"
    assert "rate_limited" in openfoodfacts.failure_modes
