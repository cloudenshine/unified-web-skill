"""source_scorer.py — URL 可信度评分"""
from __future__ import annotations

from urllib.parse import urlparse

from .heuristics import KNOWN_TRUSTED, TRUSTED_TLDS

# 主流可信媒体（补充 heuristics.py 中的 KNOWN_TRUSTED）
_KNOWN_MEDIA: frozenset[str] = frozenset({
    "nytimes.com", "theguardian.com", "washingtonpost.com", "economist.com",
    "ft.com", "wsj.com", "bloomberg.com", "cnbc.com", "xinhua.net",
    "people.com.cn", "chinadaily.com.cn", "cctv.com", "cnn.com", "bbc.co.uk",
    "ap.org", "apnews.com", "reuters.com", "nature.com", "science.org",
    "techcrunch.com", "wired.com", "arstechnica.com",
})


def _extract_domain(url: str) -> tuple[str, str]:
    """返回 (netloc, domain_without_www)"""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or ""
        scheme = parsed.scheme or ""
        domain = netloc.removeprefix("www.")
        return scheme, domain
    except Exception:
        return "", ""


def score_credibility(
    url: str,
    trusted_mode: bool = True,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> float:
    """
    计算 URL 可信度得分（0.0–1.0）。
    - gov/edu/org TLD: +0.3
    - HTTPS: +0.1
    - 已知媒体/学术: +0.1
    - trusted_mode 且低信域名: 降低评分
    """
    scheme, domain = _extract_domain(url)
    if not domain:
        return 0.3

    # 强制排除
    if exclude_domains:
        for ex in exclude_domains:
            if domain == ex or domain.endswith("." + ex):
                return 0.0

    # 强制包含（给最高可信度）
    if include_domains:
        for inc in include_domains:
            if domain == inc or domain.endswith("." + inc):
                return 1.0

    score = 0.4  # baseline

    # HTTPS 加分
    if scheme == "https":
        score += 0.1

    # 精确匹配已知可信源
    for trusted in KNOWN_TRUSTED:
        if domain == trusted or domain.endswith("." + trusted):
            score += 0.45
            return min(score, 1.0)

    # 已知媒体加分
    for media in _KNOWN_MEDIA:
        if domain == media or domain.endswith("." + media):
            score += 0.1
            break

    # TLD 加分
    full = "." + domain
    for tld in TRUSTED_TLDS:
        if tld in full:
            score += 0.3
            break

    # .com/.net 中性
    if domain.endswith((".com", ".net", ".io", ".co")):
        score += 0.05

    if trusted_mode:
        # trusted_mode 下对低信域名惩罚
        if score < 0.5:
            score *= 0.8

    return round(min(max(score, 0.0), 1.0), 4)
