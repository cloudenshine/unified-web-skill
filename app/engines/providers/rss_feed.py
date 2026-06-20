"""RSS/Atom feed parsing engine using feedparser."""

from __future__ import annotations

import logging
from typing import Any

from ..base import BaseEngine, Capability, FetchResult

logger = logging.getLogger(__name__)


class RSSFeedEngine(BaseEngine):
    """Fetch and parse RSS/Atom feeds into structured text."""

    name = "rss-feed"
    capabilities = {Capability.FETCH}

    async def fetch(self, url: str, *, timeout: int | None = None, **kwargs: Any) -> FetchResult:
        try:
            import feedparser
        except ImportError:
            return FetchResult(ok=False, url=url, engine=self.name, error="feedparser not installed")

        import httpx
        try:
            async with httpx.AsyncClient(timeout=timeout or 15) as client:
                resp = await client.get(url, headers={"User-Agent": "unified-web-skill/3.0"})
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            if not feed.entries:
                return FetchResult(ok=False, url=url, engine=self.name, error="No entries found in feed")

            text_parts = [f"# {feed.feed.get('title', 'Untitled Feed')}"]
            if feed.feed.get("subtitle"):
                text_parts.append(f"> {feed.feed['subtitle']}")
            text_parts.append("")
            for i, entry in enumerate(feed.entries[:50], 1):
                title = entry.get("title", "Untitled")
                link = entry.get("link", "")
                published = entry.get("published", "")
                summary = entry.get("summary", "")[:500] if entry.get("summary") else ""
                text_parts.append(f"## {i}. {title}")
                if link:
                    text_parts.append(f"   URL: {link}")
                if published:
                    text_parts.append(f"   Date: {published}")
                if summary:
                    text_parts.append(f"   {summary[:300]}")
                text_parts.append("")

            text = "\n".join(text_parts)
            return FetchResult(ok=True, url=url, engine=self.name, text=text, quality_score=0.8, metadata={"source": "rss", "entries": len(feed.entries)})
        except Exception as exc:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"RSS fetch failed: {exc}")
