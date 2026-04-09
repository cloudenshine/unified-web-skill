"""
Content extraction from HTML/text with multiple strategies.

Tries scrapling's Adaptor for CSS-based extraction first,
falls back to regex-based tag stripping.
"""

import hashlib
import re
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

from ..utils.language import detect_language as _detect_language

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Precompiled patterns
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|iframe|svg)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_META_TITLE_RE = re.compile(
    r'<meta\s+(?:[^>]*?)property=["\']og:title["\']\s+content=["\'](.*?)["\']',
    re.IGNORECASE,
)
_HREF_RE = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)

# Date extraction patterns
_DATE_META_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r'<meta\s+[^>]*(?:name|property)=["\']'
        r"(?:article:published_time|datePublished|pubdate|date|DC\.date"
        r"|publishdate|og:article:published_time)"
        r'["\']\s+content=["\'](.*?)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta\s+content=["\'](.*?)["\']\s+[^>]*(?:name|property)=["\']'
        r"(?:article:published_time|datePublished|pubdate|date|DC\.date"
        r"|publishdate|og:article:published_time)[\"']",
        re.IGNORECASE,
    ),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.IGNORECASE),
]

_DATE_BODY_PATTERNS: list[re.Pattern[str]] = [
    # ISO-8601: 2024-01-15T10:30:00Z
    re.compile(r"\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s\"'<>]*)\b"),
    # YYYY-MM-DD
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    # YYYY/MM/DD
    re.compile(r"\b(\d{4}/\d{2}/\d{2})\b"),
    # Chinese date: 2024年1月15日
    re.compile(r"(\d{4}年\d{1,2}月\d{1,2}日)"),
]


class ContentExtractor:
    """Extracts structured content from fetch results."""

    def extract(self, fetch_result) -> dict:
        """Extract text, title, date, links, hash from a FetchResult.

        Returns dict with keys:
        - text: cleaned text content
        - title: page title
        - summary: first 300 chars
        - date: publication date (ISO format or None)
        - links: list of extracted URLs
        - content_hash: SHA1 hash of text (first 16 chars)
        - language: detected language
        """
        html = getattr(fetch_result, "html", "") or ""
        raw_text = getattr(fetch_result, "text", "") or ""
        url = getattr(fetch_result, "url", "") or ""

        # Extract text: prefer HTML extraction, fall back to raw text
        if html:
            text = self.extract_text(html)
        else:
            text = raw_text

        title = self.extract_title(html) if html else (getattr(fetch_result, "title", "") or "")
        date = self.extract_date(html) if html else None
        links = self.extract_links(html, base_url=url) if html else []
        c_hash = self.content_hash(text) if text else ""
        language = self.detect_language(text)
        summary = text[:300].strip() if text else ""

        return {
            "text": text,
            "title": title,
            "summary": summary,
            "date": date,
            "links": links,
            "content_hash": c_hash,
            "language": language,
        }

    def extract_text(self, html: str, max_chars: int = 10000) -> str:
        """Extract readable text from HTML.

        Priority: trafilatura → scrapling Adaptor → regex fallback.
        """
        if not html:
            return ""

        # Strategy 0: trafilatura (best quality for article pages)
        try:
            import trafilatura
            text = trafilatura.extract(html, include_comments=False,
                                       include_tables=True, no_fallback=False,
                                       favor_recall=True)
            if text and len(text) > 80:
                return text[:max_chars]
        except ImportError:
            _logger.debug("trafilatura not available")
        except Exception as exc:
            _logger.debug("trafilatura extraction failed: %s", exc)

        # Strategy 1: scrapling Adaptor
        try:
            from scrapling import Adaptor  # type: ignore[import-untyped]

            page = Adaptor(html, auto_match=False)
            # Try common article containers first
            for selector in ("article", "main", ".content", "#content", ".post-body", ".article-body"):
                elements = page.css(selector)
                if elements:
                    texts = [el.text for el in elements if el.text]
                    if texts:
                        combined = "\n".join(texts)
                        if len(combined) > 80:
                            return combined[:max_chars]

            # Fallback: body text
            body = page.css("body")
            if body:
                text = body[0].text or ""
                if len(text) > 50:
                    return text[:max_chars]
        except ImportError:
            _logger.debug("scrapling not available, using regex fallback")
        except Exception as exc:
            _logger.debug("scrapling extraction failed: %s", exc)

        # Strategy 2: regex-based tag stripping
        return self._regex_extract(html, max_chars)

    def _regex_extract(self, html: str, max_chars: int) -> str:
        """Regex-based HTML → text extraction."""
        text = html

        # Remove scripts, styles, and comments
        text = _SCRIPT_STYLE_RE.sub(" ", text)
        text = _COMMENT_RE.sub(" ", text)

        # Convert block elements to newlines
        text = re.sub(r"<(?:br|p|div|h[1-6]|li|tr|blockquote|section|header|footer)[^>]*>",
                       "\n", text, flags=re.IGNORECASE)

        # Strip remaining tags
        text = _TAG_RE.sub(" ", text)

        # Decode common HTML entities
        text = (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
            .replace("&#x27;", "'")
            .replace("&#x2F;", "/")
        )

        # Normalise whitespace
        text = _WHITESPACE_RE.sub(" ", text)
        text = _BLANK_LINES_RE.sub("\n\n", text)

        # Clean up lines
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]
        text = "\n".join(lines)

        return text[:max_chars].strip()

    def extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        if not html:
            return ""

        # Try og:title first (usually cleaner)
        m = _META_TITLE_RE.search(html[:5000])
        if m:
            title = m.group(1).strip()
            if title:
                return self._decode_entities(title)

        # Fall back to <title> tag
        m = _TITLE_RE.search(html[:5000])
        if m:
            title = m.group(1).strip()
            # Remove common suffixes like " - SiteName" or " | Brand"
            title = re.sub(r"\s*[|\-–—]\s*[^|\-–—]{1,30}$", "", title)
            return self._decode_entities(title)

        return ""

    def extract_date(self, html: str) -> Optional[str]:
        """Extract publication date from meta tags and body patterns."""
        if not html:
            return None

        # Check meta tags / <time> elements first (most reliable)
        for pattern in _DATE_META_PATTERNS:
            m = pattern.search(html[:10000])
            if m:
                date_str = m.group(1).strip()
                normalised = self._normalise_date(date_str)
                if normalised:
                    return normalised

        # Check body text for date patterns
        body_text = html[:15000]
        for pattern in _DATE_BODY_PATTERNS:
            m = pattern.search(body_text)
            if m:
                date_str = m.group(1).strip()
                normalised = self._normalise_date(date_str)
                if normalised:
                    return normalised

        return None

    def extract_links(self, html: str, base_url: str = "") -> list[str]:
        """Extract and resolve links from HTML."""
        if not html:
            return []

        raw_links = _HREF_RE.findall(html)
        resolved: list[str] = []
        seen: set[str] = set()

        for href in raw_links:
            href = href.strip()
            # Skip anchors, javascript, mailto, data URIs
            if not href or href.startswith(("#", "javascript:", "mailto:", "data:", "tel:")):
                continue

            # Resolve relative URLs
            if base_url and not href.startswith(("http://", "https://", "//")):
                href = urljoin(base_url, href)
            elif href.startswith("//"):
                href = "https:" + href

            # Normalise
            normalised = href.rstrip("/")
            if normalised not in seen:
                seen.add(normalised)
                resolved.append(href)

        return resolved

    def content_hash(self, text: str) -> str:
        """Generate SHA1 hash of text (16 chars)."""
        return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:16]

    def detect_language(self, text: str) -> str:
        """Delegate to shared utility (with content-appropriate defaults)."""
        return _detect_language(text, min_length=5, sample_size=2000)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_entities(text: str) -> str:
        """Decode common HTML entities."""
        return (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
        )

    @staticmethod
    def _normalise_date(date_str: str) -> Optional[str]:
        """Normalise various date formats to ISO-8601 date string.

        Returns YYYY-MM-DD or full ISO timestamp, or None if unparseable.
        """
        if not date_str:
            return None

        # Handle Chinese dates: 2024年1月15日 → 2024-01-15
        m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # Handle YYYY/MM/DD → YYYY-MM-DD
        m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_str)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # Already ISO-8601 (YYYY-MM-DD or YYYY-MM-DDThh:mm:ss…)
        m = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
        if m:
            return date_str.strip()

        return None
