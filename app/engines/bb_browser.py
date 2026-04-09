"""bb_browser.py — bb-browser engine: the most capable engine (126+ site adapters)."""
from __future__ import annotations

import json
import os
import time
from typing import Any

from .base import BaseEngine, Capability, FetchResult, InteractResult, SearchResult

_SEARCH_ENGINES: dict[str, str] = {
    "google": "google/search",
    "baidu": "baidu/search",
    "bing": "bing/search",
    "duckduckgo": "duckduckgo/search",
    "sogou_wechat": "sogou/weixin",
}

_SITE_SEARCH: dict[str, str] = {
    "twitter": "twitter/search",
    "reddit": "reddit/search",
    "bilibili": "bilibili/search",
    "xiaohongshu": "xiaohongshu/search",
    "youtube": "youtube/search",
    "zhihu": "zhihu/search",
    "github": "github/issues",
    "arxiv": "arxiv/search",
    "hackernews": "hackernews/top",
    "weibo": "weibo/search",
    "douban": "douban/search",
    "v2ex": "v2ex/hot",
    "stackoverflow": "stackoverflow/search",
}

# Combined domain→adapter for fetch routing
_DOMAIN_ADAPTER: dict[str, str] = {
    "bilibili.com": "bilibili",
    "zhihu.com": "zhihu",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "reddit.com": "reddit",
    "github.com": "github",
    "youtube.com": "youtube",
    "xiaohongshu.com": "xiaohongshu",
    "weibo.com": "weibo",
    "douban.com": "douban",
    "news.ycombinator.com": "hackernews",
    "arxiv.org": "arxiv",
    "stackoverflow.com": "stackoverflow",
    "v2ex.com": "v2ex",
}


def _url_to_platform(url: str) -> str | None:
    from urllib.parse import urlparse

    try:
        host = (urlparse(url).hostname or "").removeprefix("www.").lower()
    except Exception:
        return None
    if host in _DOMAIN_ADAPTER:
        return _DOMAIN_ADAPTER[host]
    for suffix, plat in _DOMAIN_ADAPTER.items():
        if host.endswith("." + suffix):
            return plat
    return None


class BBBrowserEngine(BaseEngine):
    """Wraps the ``bb-browser`` CLI — 126+ site adapters, structured output."""

    def __init__(self) -> None:
        self._bin = os.environ.get("BB_BROWSER_BIN", "bb-browser")
        super().__init__()

    @property
    def name(self) -> str:
        return "bb-browser"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.SEARCH, Capability.INTERACT, Capability.STRUCTURED}

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        rc, out, _ = await self._run_subprocess([self._bin, "status"], timeout=10)
        if rc == 0:
            return True
        # fallback: try daemon status
        rc2, out2, _ = await self._run_subprocess([self._bin, "daemon", "status"], timeout=10)
        return rc2 == 0

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        t0 = time.monotonic()
        platform = _url_to_platform(url)

        if platform:
            command = opts.get("command", "")
            if command:
                adapter = f"{platform}/{command}"
            else:
                adapter = platform
            cmd = [self._bin, "site", adapter, "--json"]
            extra_args: list[str] = opts.get("args", [])
            if extra_args:
                cmd.extend(extra_args)
        else:
            # Generic URL fetch
            cmd = [self._bin, "open", url, "--json"]

        rc, stdout, stderr = await self._run_subprocess(cmd, timeout=timeout)
        dur = (time.monotonic() - t0) * 1000

        if rc != 0:
            self._logger.warning("bb-browser exited %d: %s", rc, stderr[:200])
            return FetchResult(
                ok=False, url=url, engine=self.name,
                status=rc, duration_ms=dur,
                error=stderr[:300] or f"exit code {rc}",
            )

        # For generic open, get text content
        text = stdout
        metadata: dict[str, Any] = {}
        if not platform:
            get_cmd = [self._bin, "get", "text", "--json"]
            rc2, text_out, _ = await self._run_subprocess(get_cmd, timeout=timeout)
            if rc2 == 0:
                text = text_out

        # Parse JSON if available
        try:
            data = json.loads(text)
            metadata = data if isinstance(data, dict) else {"items": data}
            text = json.dumps(data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass

        return FetchResult(
            ok=True, url=url, engine=self.name,
            text=text, duration_ms=dur, metadata=metadata,
        )

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "zh", **opts: Any
    ) -> list[SearchResult]:
        t0 = time.monotonic()

        # Determine which search adapter to use
        search_engine = opts.get("engine", "")
        site = opts.get("site", "")

        if site and site in _SITE_SEARCH:
            adapter = _SITE_SEARCH[site]
        elif search_engine and search_engine in _SEARCH_ENGINES:
            adapter = _SEARCH_ENGINES[search_engine]
        else:
            # Default: google for English, baidu for Chinese
            adapter = "baidu/search" if language == "zh" else "google/search"

        cmd = [self._bin, "site", adapter, query, "--json"]
        rc, stdout, stderr = await self._run_subprocess(cmd, timeout=30)

        if rc != 0:
            self._logger.warning("search via %s failed: %s", adapter, stderr[:200])
            # Fallback: DuckDuckGo via ddgs
            return self._ddgs_fallback(query, max_results, language)

        results: list[SearchResult] = []
        try:
            data = json.loads(stdout)
            items = data if isinstance(data, list) else data.get("items", data.get("results", []))
            for idx, item in enumerate(items[:max_results]):
                if isinstance(item, dict):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", item.get("link", "")),
                        snippet=item.get("snippet", item.get("description", item.get("text", ""))),
                        rank=idx + 1,
                        source=f"bb-browser:{adapter}",
                        metadata=item,
                    ))
        except (json.JSONDecodeError, ValueError):
            self._logger.warning("failed to parse search output as JSON")

        # If bb-browser returned empty, fall back to DuckDuckGo
        if not results:
            return self._ddgs_fallback(query, max_results, language)

        return results

    @staticmethod
    def _ddgs_fallback(query: str, max_results: int, language: str) -> list[SearchResult]:
        """DuckDuckGo search fallback when bb-browser search adapters fail."""
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return []
        region = "cn-zh" if language == "zh" else "wt-wt"
        results: list[SearchResult] = []
        try:
            ddgs = DDGS()
            for idx, r in enumerate(ddgs.text(query, region=region, max_results=max_results)):
                results.append(SearchResult(
                    url=r.get("href", r.get("link", "")),
                    title=r.get("title", ""),
                    snippet=r.get("body", r.get("snippet", "")),
                    source="bb-browser:ddgs-fallback",
                    rank=idx,
                ))
        except Exception:
            pass
        return results

    async def interact(
        self, url: str, actions: list[dict[str, Any]], *, timeout: int = 60, **opts: Any
    ) -> InteractResult:
        t0 = time.monotonic()

        # Open the page first
        open_cmd = [self._bin, "open", url, "--json"]
        rc, _, stderr = await self._run_subprocess(open_cmd, timeout=timeout)
        if rc != 0:
            dur = (time.monotonic() - t0) * 1000
            return InteractResult(
                ok=False, url=url, engine=self.name,
                duration_ms=dur, error=f"failed to open: {stderr[:200]}",
            )

        # Execute actions sequentially
        last_output = ""
        for action in actions:
            act_type = action.get("type", "")
            if act_type == "click":
                selector = action.get("selector", "")
                act_cmd = [self._bin, "click", selector, "--json"]
            elif act_type == "fill" or act_type == "type":
                selector = action.get("selector", "")
                value = action.get("value", "")
                act_cmd = [self._bin, "fill", selector, value, "--json"]
            elif act_type == "scroll":
                direction = action.get("direction", "down")
                act_cmd = [self._bin, "scroll", direction, "--json"]
            elif act_type == "wait":
                import asyncio
                await asyncio.sleep(action.get("seconds", 1))
                continue
            elif act_type == "screenshot":
                act_cmd = [self._bin, "screenshot", "--json"]
            else:
                self._logger.warning("unknown action type: %s", act_type)
                continue

            rc, stdout, stderr = await self._run_subprocess(act_cmd, timeout=timeout)
            if rc != 0:
                dur = (time.monotonic() - t0) * 1000
                return InteractResult(
                    ok=False, url=url, engine=self.name,
                    duration_ms=dur,
                    error=f"action '{act_type}' failed: {stderr[:200]}",
                )
            last_output = stdout

        # Get final page text
        text_cmd = [self._bin, "get", "text", "--json"]
        rc, text_out, _ = await self._run_subprocess(text_cmd, timeout=timeout)
        text = text_out if rc == 0 else last_output

        dur = (time.monotonic() - t0) * 1000
        return InteractResult(
            ok=True, url=url, engine=self.name,
            text=text, duration_ms=dur,
        )
