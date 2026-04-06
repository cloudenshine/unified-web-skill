"""extractor.py — 正文/链接/时间/语言提取"""
import hashlib
import re
from urllib.parse import urljoin, urlparse

from .quality_validator import detect_language

# Tags whose content is usually navigation/boilerplate
_NOISE_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript"}
# Patterns that indicate likely article date
_DATE_PATTERNS = [
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}",   # 2026-01-15 or 2026年1月15日
    r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",        # 15/01/2026
]


def extract_text(page_source: str, max_chars: int = 8000) -> str:
    """
    Best-effort text extraction from HTML string.
    Uses scrapling Selector if available, otherwise basic regex strip.
    """
    try:
        from scrapling.parser import Adaptor
        page = Adaptor(page_source, auto_match=False)
        # Remove noise tags
        chunks = []
        for el in page.css("p, h1, h2, h3, h4, li, td, th, blockquote, article"):
            t = el._root.text_content().strip()
            if t:
                chunks.append(t)
        text = "\n".join(chunks)
    except Exception:
        # Fallback: strip all tags
        text = re.sub(r"<[^>]+>", " ", page_source)
        text = re.sub(r"&[a-z]+;", " ", text)

    text = re.sub(r"\s{3,}", "\n\n", text).strip()
    return text[:max_chars]


def extract_links(page_source: str, base_url: str) -> list[str]:
    """Extract absolute links from HTML"""
    hrefs = re.findall(r'href=["\']([^"\'#?][^"\']*)["\']', page_source)
    links = []
    for href in hrefs:
        try:
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https"):
                links.append(absolute.split("#")[0])
        except Exception:
            pass
    # deduplicate preserving order
    seen: set[str] = set()
    result = []
    for link in links:
        if link not in seen:
            seen.add(link)
            result.append(link)
    return result


def extract_same_domain_links(page_source: str, base_url: str) -> list[str]:
    """Extract only links on the same domain"""
    base_domain = urlparse(base_url).netloc.removeprefix("www.")
    all_links = extract_links(page_source, base_url)
    return [
        l for l in all_links
        if urlparse(l).netloc.removeprefix("www.") == base_domain
    ]


def extract_date(page_source: str) -> str | None:
    """Try to find a publication date in the HTML"""
    # Check meta tags first
    meta_patterns = [
        r'<meta[^>]+(?:name|property)=["\'](?:date|article:published_time|pubdate)["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:date|article:published_time)["\']',
    ]
    for pat in meta_patterns:
        m = re.search(pat, page_source, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Look in page text
    for pat in _DATE_PATTERNS:
        m = re.search(pat, page_source)
        if m:
            return m.group(0).strip()
    return None


def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def build_record(url: str, title: str, text: str, published_at: str | None,
                 fetch_mode: str, source_type: str, extra: dict | None = None) -> dict:
    lang = detect_language(text)
    return {
        "url": url,
        "title": title,
        "text": text,
        "summary": text[:300].replace("\n", " "),
        "credibility": extra.get("credibility", 0.5) if extra else 0.5,
        "fetch_mode": fetch_mode,
        "source_type": source_type,
        "tool_chain": extra.get("tool_chain", [source_type]) if extra else [source_type],
        "content_hash": content_hash(text),
        "published_at": published_at,
        "text_length": len(text),
        "language_detected": lang,
    }
