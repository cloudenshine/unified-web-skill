"""discovery.py — DuckDuckGo 搜索发现（带 fallback）"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from .research_models import Candidate
from .source_scorer import score_credibility

logger = logging.getLogger(__name__)

# 模块级导入，方便 mock；未安装时为 None
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None  # type: ignore


def _filter_url(url: str, include_domains: list[str], exclude_domains: list[str]) -> bool:
    """True = 保留该 URL"""
    try:
        domain = urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return False
    if not domain:
        return False  # no valid netloc = not a usable URL
    if exclude_domains:
        for ex in exclude_domains:
            if domain == ex or domain.endswith("." + ex):
                return False
    if include_domains:
        for inc in include_domains:
            if domain == inc or domain.endswith("." + inc):
                return True
        return False
    return True


def discover_from_queries(
    queries: list[str],
    max_sources: int = 20,
    trusted_mode: bool = True,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    min_credibility: float = 0.0,
) -> list[Candidate]:
    """
    使用 duckduckgo_search 从查询词列表中发现 URL 候选。
    ddgs 失败时静默降级，返回空列表。
    """
    include_domains = include_domains or []
    exclude_domains = exclude_domains or []

    seen_urls: set[str] = set()
    candidates: list[Candidate] = []

    per_query = max(1, max_sources // max(len(queries), 1)) + 2

    if DDGS is None:
        logger.warning("duckduckgo_search not installed; discovery returns empty")
        return []

    for query in queries:
        if len(candidates) >= max_sources:
            break
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=per_query))
        except Exception as exc:
            logger.warning("DDGS search failed for %r: %s", query, exc)
            continue

        for r in results:
            url = (r.get("href") or r.get("url") or "").strip()
            if not url:
                continue
            canonical = url.split("#")[0].rstrip("/")
            if canonical in seen_urls:
                continue
            if not _filter_url(url, include_domains, exclude_domains):
                continue
            credibility = score_credibility(
                url, trusted_mode=trusted_mode,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            )
            if credibility < min_credibility:
                continue
            seen_urls.add(canonical)
            candidates.append(Candidate(
                url=url,
                canonical_url=canonical,
                score=credibility,
                source_type="web",
            ))
            if len(candidates) >= max_sources:
                break

    return candidates
