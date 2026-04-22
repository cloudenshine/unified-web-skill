"""
Ring 3 — Research pipeline.

Orchestrates R0+R1 for multi-source research:
  query → expand → search → concurrent fetch → extract → deduplicate → store

Requires: Ring 0 (always). Ring 1 improves JS site coverage.
"""
from __future__ import annotations
import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Any

from . import r0_http, r1_browser
from ..probe import CAPS


# --- Query expansion (heuristic, no LLM needed) ---------------------------

_EXPANSION_TEMPLATES = {
    "zh": [
        "{query}",
        "{query} 详细介绍",
        "{query} 最新资讯",
        "{query} 教程",
        "{query} site:zhihu.com",
        "{query} site:bilibili.com",
    ],
    "en": [
        "{query}",
        "{query} guide",
        "{query} latest",
        "{query} tutorial",
        "{query} site:reddit.com",
        "{query} site:github.com",
    ],
}


def expand_queries(query: str, language: str = "zh", max_queries: int = 4) -> list[str]:
    templates = _EXPANSION_TEMPLATES.get(language, _EXPANSION_TEMPLATES["en"])
    return [t.format(query=query) for t in templates[:max_queries]]


# --- URL deduplication ----------------------------------------------------

def _url_fingerprint(url: str) -> str:
    """Normalize URL to a dedup key."""
    url = url.rstrip("/")
    url = re.sub(r"\?.*$", "", url)   # strip query params
    url = re.sub(r"#.*$", "", url)    # strip fragments
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return url.lower()


# --- Page quality scoring -------------------------------------------------

def _quality_score(text: str, url: str) -> float:
    if not text:
        return 0.0
    score = min(len(text) / 2000, 1.0)  # length score

    # Boost for known high-quality domains
    high_quality = ["github.com", "arxiv.org", "wikipedia.org",
                    "zhihu.com", "docs.", "research.", "paper"]
    for domain in high_quality:
        if domain in url:
            score = min(score + 0.2, 1.0)
            break

    # Penalize thin content
    if len(text) < 200:
        score *= 0.3
    return round(score, 3)


# --- Research record ------------------------------------------------------

@dataclass
class PageRecord:
    url: str
    title: str
    text: str
    html: str = ""
    engine: str = ""
    query: str = ""
    quality: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text[:5000],  # cap output size
            "engine": self.engine,
            "query": self.query,
            "quality": self.quality,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ResearchOutput:
    query: str
    records: list[PageRecord] = field(default_factory=list)
    queries_used: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    engines_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "records": [r.to_dict() for r in self.records],
            "total": len(self.records),
            "queries_used": self.queries_used,
            "duration_s": self.duration_s,
            "engines_used": sorted(set(self.engines_used)),
            "errors": self.errors,
        }


# --- Pipeline -------------------------------------------------------------

async def _fetch_url(
    url: str,
    query: str,
    timeout: int,
    use_browser: bool,
) -> PageRecord | None:
    """Fetch one URL, trying R1 browser first if available, else R0 HTTP."""
    # Try browser for JS-heavy known domains
    js_heavy = ["bilibili", "zhihu", "xiaohongshu", "douyin", "weibo", "twitter", "x.com"]
    needs_browser = any(d in url for d in js_heavy)

    if needs_browser and use_browser:
        r = await r1_browser.fetch(url, timeout=timeout)
        if r.ok:
            return PageRecord(
                url=r.url, title=r.title, text=r.text, html=r.html,
                engine=r.engine if hasattr(r, "engine") else "r1_browser",
                query=query,
                quality=_quality_score(r.text, url),
                duration_ms=r.duration_ms,
            )

    # Default: Ring 0 HTTP
    r = await r0_http.fetch(url, timeout=timeout)
    if r.ok:
        return PageRecord(
            url=r.url, title=r.title, text=r.text, html=r.html,
            engine=r.engine, query=query,
            quality=_quality_score(r.text, url),
            duration_ms=r.duration_ms,
        )
    return None


async def run(
    query: str,
    *,
    language: str = "zh",
    max_sources: int = 15,
    max_pages: int = 10,
    max_queries: int = 4,
    max_concurrency: int = 5,
    timeout: int = 15,
    min_quality: float = 0.1,
    min_text_length: int = 100,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    progress_cb: Callable[[str], Any] | None = None,
) -> ResearchOutput:
    """Run the full research pipeline for a query."""
    t0 = time.perf_counter()
    use_browser = CAPS.ring1
    output = ResearchOutput(query=query)

    def _progress(msg: str) -> None:
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    # Step 1: Query expansion
    queries = expand_queries(query, language=language, max_queries=max_queries)
    output.queries_used = queries
    _progress(f"Query expansion: {len(queries)} queries")

    # Step 2: Multi-query search
    all_urls: list[tuple[str, str]] = []  # (url, query)
    seen_fingerprints: set[str] = set()

    for q in queries:
        _progress(f"Searching: {q}")
        results = await r0_http.search(q, max_results=max_sources, language=language)
        for sr in results:
            if not sr.url:
                continue
            fp = _url_fingerprint(sr.url)
            if fp in seen_fingerprints:
                continue
            if include_domains and not any(d in sr.url for d in include_domains):
                continue
            if exclude_domains and any(d in sr.url for d in exclude_domains):
                continue
            seen_fingerprints.add(fp)
            all_urls.append((sr.url, q))

        if len(all_urls) >= max_sources:
            break

    _progress(f"Discovered {len(all_urls)} unique URLs")

    # Step 3: Concurrent fetch with semaphore
    sem = asyncio.Semaphore(max_concurrency)
    fetch_targets = all_urls[:max_pages]

    async def _bounded_fetch(url: str, q: str) -> PageRecord | None:
        async with sem:
            return await _fetch_url(url, q, timeout=timeout, use_browser=use_browser)

    tasks = [_bounded_fetch(url, q) for url, q in fetch_targets]
    fetched = await asyncio.gather(*tasks, return_exceptions=True)
    _progress(f"Fetched {len(fetch_targets)} pages")

    # Step 4: Quality gate + deduplication
    seen_content: set[str] = set()
    for item in fetched:
        if isinstance(item, Exception) or item is None:
            continue
        if len(item.text) < min_text_length:
            continue
        if item.quality < min_quality:
            continue
        # Content dedup via text fingerprint
        content_fp = hashlib.md5(item.text[:500].encode()).hexdigest()
        if content_fp in seen_content:
            continue
        seen_content.add(content_fp)
        output.records.append(item)
        output.engines_used.append(item.engine)

    # Sort by quality descending
    output.records.sort(key=lambda r: -r.quality)
    output.duration_s = round(time.perf_counter() - t0, 2)
    _progress(f"Done: {len(output.records)} quality records in {output.duration_s}s")

    return output
