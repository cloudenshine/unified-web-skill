"""Run live verification for the global source coverage matrix."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.discovery.source_matrix import SourceMatrix
from app.discovery.source_verifier import select_sources, verify_sources
from app.engines.base import FetchResult
from app.engines.manager import EngineManager
from app.mcp_server import _get_engine_manager


REGRESSION_PROFILES = {
    "promoted-http": {
        "exclude_ids": "academic_arxiv_api_query,commerce_openfoodfacts_search",
        "access_types": "api,rss,static_html",
        "promotion_statuses": "promoted",
        "preferred_providers": "scrapling",
        "strict_preferred_provider": True,
        "limit": 100,
        "timeout": 30,
        "output": "outputs/source_matrix_regression_promoted_http.json",
    },
    "promoted-structured": {
        "access_types": "structured_adapter",
        "promotion_statuses": "promoted",
        "strict_preferred_provider": True,
        "limit": 20,
        "timeout": 45,
        "output": "outputs/source_matrix_regression_promoted_structured.json",
    },
    "promoted-browser": {
        "preferred_providers": "opencli",
        "promotion_statuses": "promoted",
        "strict_preferred_provider": True,
        "limit": 20,
        "timeout": 45,
        "output": "outputs/source_matrix_regression_promoted_browser.json",
    },
    "boundary-watch": {
        "access_types": "boundary",
        "promotion_statuses": "matrix_only",
        "strict_preferred_provider": True,
        "limit": 10,
        "timeout": 45,
        "output": "outputs/source_matrix_regression_boundary_watch.json",
    },
    "special-watch": {
        "ids": "commerce_producthunt,commerce_amazon_search",
        "strict_preferred_provider": True,
        "limit": 10,
        "timeout": 45,
        "output": "outputs/source_matrix_regression_special_watch.json",
    },
    "rate-limited-watch": {
        "ids": "academic_arxiv_api_query,commerce_openfoodfacts_search",
        "strict_preferred_provider": True,
        "limit": 10,
        "timeout": 60,
        "output": "outputs/source_matrix_regression_rate_limited_watch.json",
    },
}


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _summarize(results: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for result in results:
        status = result["quality_status"]
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": len(results),
        "counts": counts,
        "verified": counts.get("verified", 0),
        "weak": counts.get("weak", 0),
        "failed": counts.get("failed", 0),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", default="", help="Comma-separated source ids")
    parser.add_argument(
        "--exclude-ids",
        default="",
        help="Comma-separated source ids to exclude after selection",
    )
    parser.add_argument("--categories", default="", help="Comma-separated categories")
    parser.add_argument("--access-types", default="", help="Comma-separated access types")
    parser.add_argument(
        "--promotion-statuses",
        default="",
        help="Comma-separated promotion statuses",
    )
    parser.add_argument("--cost-tiers", default="", help="Comma-separated cost tiers")
    parser.add_argument(
        "--preferred-providers",
        default="",
        help="Comma-separated preferred providers",
    )
    parser.add_argument(
        "--strict-preferred-provider",
        action="store_true",
        help="Do not append implicit fallback engines during verification",
    )
    parser.add_argument(
        "--regression-profile",
        choices=sorted(REGRESSION_PROFILES),
        default="",
        help="Apply a stable source-matrix regression batch profile",
    )
    parser.add_argument(
        "--fail-on-unverified",
        action="store_true",
        help="Exit 1 when any selected source is weak or failed",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--min-text-length", type=int, default=200)
    parser.add_argument(
        "--output",
        default="outputs/source_matrix_verification.json",
        help="Output JSON file",
    )
    return parser


def _resolve_regression_profile(args: argparse.Namespace) -> argparse.Namespace:
    if not args.regression_profile:
        return args

    profile = REGRESSION_PROFILES[args.regression_profile]
    defaults = _build_parser().parse_args([])
    for key, value in profile.items():
        if getattr(args, key) == getattr(defaults, key):
            setattr(args, key, value)
    return args


def _exit_code_for_summary(summary: dict, *, fail_on_unverified: bool) -> int:
    if not fail_on_unverified:
        return 0
    if summary.get("weak", 0) or summary.get("failed", 0):
        return 1
    return 0


async def _fetch_matrix_url(
    em: EngineManager,
    url: str,
    *,
    timeout: int,
    preferred_provider: str,
    strict_preferred_provider: bool,
) -> FetchResult:
    if strict_preferred_provider:
        engine = em.get_engine(preferred_provider)
        if engine is None:
            return FetchResult(
                ok=False,
                url=url,
                engine=preferred_provider,
                error=f"Preferred provider not registered: {preferred_provider}",
            )
        return await engine.fetch(url, timeout=timeout)

    preferred = [preferred_provider] if preferred_provider else None
    return await em.fetch_with_fallback(
        url,
        preferred_engines=preferred,
        allow_fallback_engines=True,
        timeout=timeout,
        no_cache=True,
    )


async def _main() -> int:
    parser = _build_parser()
    args = _resolve_regression_profile(parser.parse_args())

    matrix = SourceMatrix.load_builtin()
    selected = select_sources(
        matrix.all_sources(),
        source_ids=_split_csv(args.ids),
        categories=_split_csv(args.categories),
        access_types=_split_csv(args.access_types),
        promotion_statuses=_split_csv(args.promotion_statuses),
        cost_tiers=_split_csv(args.cost_tiers),
        preferred_providers=_split_csv(args.preferred_providers),
    )
    exclude_ids = set(_split_csv(args.exclude_ids))
    if exclude_ids:
        selected = [
            source
            for source in selected
            if source.source_id not in exclude_ids
        ]

    em = _get_engine_manager()

    async def fetcher(url: str, *, timeout: int, preferred_provider: str):
        return await _fetch_matrix_url(
            em,
            url,
            timeout=timeout,
            preferred_provider=preferred_provider,
            strict_preferred_provider=args.strict_preferred_provider,
        )

    results = await verify_sources(
        selected,
        fetcher,
        limit=args.limit,
        timeout=args.timeout,
        min_text_length=args.min_text_length,
    )
    payload = {
        "summary": _summarize([result.to_dict() for result in results]),
        "results": [result.to_dict() for result in results],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = payload["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Results saved to {output}")
    return _exit_code_for_summary(
        summary,
        fail_on_unverified=args.fail_on_unverified,
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
