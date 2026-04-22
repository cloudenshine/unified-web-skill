"""
Ring 0 — Pure HTTP fetch.

Dependencies: httpx (already required by scrapling)
Guarantee:    Works on ANY URL, ANY site, ZERO binary dependencies.
"""
from __future__ import annotations
import html
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

# --- User-agent rotation (modern browser fingerprints) ---------------------

_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

_ua_index = 0

def _next_ua() -> str:
    global _ua_index
    ua = _UA_POOL[_ua_index % len(_UA_POOL)]
    _ua_index += 1
    return ua


_BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


# --- HTML extraction (stdlib only) ----------------------------------------

class _TextExtractor(HTMLParser):
    """Minimal HTML→text extractor using stdlib html.parser."""

    _SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link",
                  "svg", "path", "button", "nav", "footer", "header", "aside"}
    _BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                   "li", "td", "th", "blockquote", "article", "section",
                   "br", "hr", "tr"}

    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._skip_depth = 0
        self._current_tag = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag in self._BLOCK_TAGS:
            self._buf.append("\n")
        self._current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._buf.append(stripped + " ")

    def get_text(self) -> str:
        text = "".join(self._buf)
        # Collapse whitespace, keep paragraph breaks
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _extract_title(html_content: str) -> str:
    m = re.search(r"<title[^>]*>([^<]{1,200})</title>", html_content, re.IGNORECASE)
    if m:
        return html.unescape(m.group(1).strip())
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']{1,200})["\']', html_content, re.IGNORECASE)
    if m:
        return html.unescape(m.group(1).strip())
    return ""


def extract_text(html_content: str) -> str:
    """Extract readable text from HTML — stdlib only, no lxml."""
    # Try trafilatura first (richer extraction) if available
    try:
        import trafilatura
        result = trafilatura.extract(html_content, include_tables=True, include_links=False)
        if result and len(result) > 50:
            return result
    except ImportError:
        pass

    # Try BeautifulSoup if available
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        pass

    # Stdlib fallback
    extractor = _TextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


# --- Fetch result ----------------------------------------------------------

class FetchResult:
    __slots__ = ("ok", "url", "html", "text", "title", "status", "engine",
                 "error", "duration_ms", "headers")

    def __init__(
        self,
        ok: bool,
        url: str,
        html: str = "",
        text: str = "",
        title: str = "",
        status: int = 0,
        engine: str = "r0_http",
        error: str = "",
        duration_ms: float = 0.0,
        headers: dict | None = None,
    ) -> None:
        self.ok = ok
        self.url = url
        self.html = html
        self.text = text
        self.title = title
        self.status = status
        self.engine = engine
        self.error = error
        self.duration_ms = duration_ms
        self.headers = headers or {}

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "html": self.html,
            "status": self.status,
            "engine": self.engine,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


# --- Core fetch -----------------------------------------------------------

async def fetch(
    url: str,
    *,
    timeout: int = 20,
    headers: dict | None = None,
    follow_redirects: bool = True,
    extract_text_content: bool = True,
) -> FetchResult:
    """Fetch any URL via httpx with browser-like headers.

    Never raises — returns FetchResult(ok=False) on any error.
    """
    t0 = time.perf_counter()
    merged_headers = {**_BASE_HEADERS, "User-Agent": _next_ua()}
    if headers:
        merged_headers.update(headers)

    try:
        async with httpx.AsyncClient(
            follow_redirects=follow_redirects,
            timeout=httpx.Timeout(connect=10.0, read=timeout, write=10.0, pool=5.0),
            verify=False,  # Skip SSL verification for maximum reach
        ) as client:
            resp = await client.get(url, headers=merged_headers)
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)

            html_content = ""
            content_type = resp.headers.get("content-type", "")
            if "text" in content_type or "html" in content_type or "xml" in content_type:
                html_content = resp.text
            elif "json" in content_type:
                html_content = resp.text
            else:
                # Binary content — return empty text, raw bytes size only
                return FetchResult(
                    ok=resp.status_code < 400,
                    url=str(resp.url),
                    html="",
                    text=f"[Binary content: {content_type}, {len(resp.content)} bytes]",
                    title="",
                    status=resp.status_code,
                    duration_ms=duration_ms,
                    headers=dict(resp.headers),
                )

            title = _extract_title(html_content)
            text = extract_text(html_content) if extract_text_content else ""

            return FetchResult(
                ok=resp.status_code < 400,
                url=str(resp.url),
                html=html_content,
                text=text,
                title=title,
                status=resp.status_code,
                duration_ms=duration_ms,
                headers=dict(resp.headers),
                error="" if resp.status_code < 400 else f"HTTP {resp.status_code}",
            )

    except httpx.TimeoutException:
        return FetchResult(ok=False, url=url, error=f"Timeout after {timeout}s",
                           duration_ms=round((time.perf_counter() - t0) * 1000, 1))
    except Exception as exc:
        return FetchResult(ok=False, url=url, error=str(exc),
                           duration_ms=round((time.perf_counter() - t0) * 1000, 1))


# --- Search via DuckDuckGo HTML (no API key, no binary) -------------------

_DDG_HEADERS = {
    **_BASE_HEADERS,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://duckduckgo.com/",
}


class SearchResult:
    __slots__ = ("url", "title", "snippet", "rank", "source")

    def __init__(self, url: str, title: str, snippet: str, rank: int = 0, source: str = "ddg") -> None:
        self.url = url
        self.title = title
        self.snippet = snippet
        self.rank = rank
        self.source = source

    def to_dict(self) -> dict:
        return {"url": self.url, "title": self.title, "snippet": self.snippet,
                "rank": self.rank, "source": self.source}


async def search(
    query: str,
    *,
    max_results: int = 10,
    language: str = "zh",
) -> list[SearchResult]:
    """Search via DuckDuckGo — zero API key, zero binary dependencies.

    Falls back to duckduckgo_search package if available (more reliable).
    """
    # Try ddgs package (new name) or duckduckgo_search (old name)
    for _mod in ("ddgs", "duckduckgo_search"):
        try:
            _ddgs_mod = __import__(_mod, fromlist=["DDGS"])
            DDGS = _ddgs_mod.DDGS
            results: list[SearchResult] = []
            region = "cn-zh" if language.startswith("zh") else "wt-wt"
            with DDGS() as ddgs_inst:
                for i, r in enumerate(ddgs_inst.text(query, region=region, max_results=max_results)):
                    results.append(SearchResult(
                        url=r.get("href", ""),
                        title=r.get("title", ""),
                        snippet=r.get("body", ""),
                        rank=i + 1,
                    ))
            if results:
                return results
            break  # Package found but no results — don't retry with old package
        except ImportError:
            continue
        except Exception:
            break

    # Fallback: Bing HTML scrape (most permissive, works globally)
    return await _bing_search(query, max_results=max_results, language=language)


async def _bing_search(query: str, max_results: int = 10, language: str = "zh") -> list[SearchResult]:
    """Bing HTML search — no API key required."""
    import urllib.parse
    mkt = "zh-CN" if language.startswith("zh") else "en-US"
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&mkt={mkt}&count={max_results}"
    r = await fetch(url, timeout=15, extract_text_content=False)
    if not r.ok or not r.html:
        return []

    results: list[SearchResult] = []
    # Parse Bing result items: <li class="b_algo">
    pattern = re.compile(
        r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>([^<]+)</a></h2>.*?'
        r'<p[^>]*>(.*?)</p>',
        re.DOTALL
    )
    for i, m in enumerate(pattern.finditer(r.html)):
        href = m.group(1)
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        snippet = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
        if not href.startswith("http"):
            continue
        results.append(SearchResult(url=href, title=title, snippet=snippet, rank=i + 1, source="bing"))
        if len(results) >= max_results:
            break

    return results


# --- Link extraction ------------------------------------------------------

def extract_links(html_content: str, base_url: str = "") -> list[str]:
    """Extract all absolute URLs from HTML."""
    links: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\'#][^"\']*)["\']', html_content, re.IGNORECASE):
        raw = m.group(1).strip()
        if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        abs_url = urljoin(base_url, raw).split("#")[0]
        if abs_url not in seen and abs_url.startswith("http"):
            seen.add(abs_url)
            links.append(abs_url)
    return links
