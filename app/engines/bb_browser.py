"""bb_browser.py — bb-browser engine: the most capable engine (126+ site adapters)."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import math
import os
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

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

_PLATFORM_COMMANDS: dict[str, set[str]] = {
    "arxiv": {"search"},
    "bilibili": {"search"},
    "douban": {"search"},
    "github": {"issues"},
    "hackernews": {"top"},
    "reddit": {"hot", "search"},
    "stackoverflow": {"search"},
    "twitter": {"search"},
    "v2ex": {"hot"},
    "weibo": {"search"},
    "xiaohongshu": {"search"},
    "youtube": {"search"},
    "zhihu": {"search"},
}


def _url_to_platform(url: str) -> str | None:
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


def _build_structured_adapter_command(binary: str, url: str) -> list[str] | None:
    """Translate known structured URLs into current bb-browser site adapters."""
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    host = (parsed.hostname or "").removeprefix("www.").lower()
    query = parse_qs(parsed.query)

    if host == "youtube.com" and parsed.path == "/results":
        search_query = query.get("search_query", [""])[0].strip()
        if search_query:
            return [binary, "site", "youtube/search", search_query, "--json"]

    if host == "search.bilibili.com" and parsed.path.startswith("/all"):
        keyword = query.get("keyword", [""])[0].strip()
        if keyword:
            return [binary, "site", "bilibili/search", keyword, "--json"]

    if host == "reddit.com":
        match = re.fullmatch(r"/r/([^/]+)/?", parsed.path)
        if match:
            return [binary, "site", "reddit/hot", match.group(1), "--json"]

    if host == "arxiv.org":
        match = re.fullmatch(r"/list/([^/]+)/recent/?", parsed.path)
        if match:
            return [binary, "site", "arxiv/search", match.group(1), "--json"]

    return None


def _validate_public_http_url(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"unsupported bb-browser target: {url}") from exc

    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").strip().lower()
    if scheme not in {"http", "https"} or not host:
        raise ValueError(f"unsupported bb-browser target: {url}")
    if host == "localhost" or host.endswith(".local"):
        raise ValueError(f"refusing local bb-browser target: {url}")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError(f"refusing local bb-browser target: {url}")


def _build_fetch_command(binary: str, url: str, opts: dict[str, Any]) -> list[str]:
    """Build the bb-browser command for URL fetches.

    Latest bb-browser requires a concrete site adapter such as
    ``youtube/search``. Plain platform names like ``youtube`` are not valid
    adapter commands, so ordinary URL fetches now use ``open`` + ``eval``.
    """
    _validate_public_http_url(url)
    platform = _url_to_platform(url)
    command = opts.get("command", "")
    if platform and command:
        allowed_commands = _PLATFORM_COMMANDS.get(platform, set())
        if command not in allowed_commands:
            raise ValueError(f"unsupported bb-browser command for {platform}: {command}")
        raw_args = opts.get("args", [])
        if not isinstance(raw_args, (list, tuple)) or not all(isinstance(arg, str) for arg in raw_args):
            raise ValueError("bb-browser args must be a list of strings")
        adapter = f"{platform}/{command}"
        extra_args = list(raw_args)
        return [binary, "site", adapter] + extra_args + ["--json"]
    structured = _build_structured_adapter_command(binary, url)
    if structured:
        return structured
    return [binary, "open", url, "--json"]


def _extract_text_from_html(html: str) -> str:
    """Best-effort text extraction for generic bb-browser page fetches."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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

    async def _daemon_available(self) -> bool:
        """Quick check if bb-browser daemon is running (subprocess-based, non-blocking)."""
        rc, out, _ = await self._run_subprocess([self._bin, "daemon", "status"], timeout=5)
        normalized = out.lower()
        return rc == 0 and "running" in normalized and "not running" not in normalized

    async def health_check(self) -> bool:
        rc, out, _ = await self._run_subprocess([self._bin, "status"], timeout=10)
        normalized = out.lower()
        if rc == 0 and "not running" not in normalized:
            return True
        # fallback: try daemon status
        return await self._daemon_available()

    async def version_info(self) -> dict[str, Any]:
        return await self._version_from_command(
            [self._bin, "--version"],
            provider=self.name,
            timeout=5,
        )

    @staticmethod
    def _load_json_result(stdout: str) -> Any:
        payload = json.loads(stdout)
        if isinstance(payload, dict):
            if payload.get("error"):
                raise ValueError(payload["error"].get("message", "bb-browser returned an error"))
            if "result" in payload:
                return payload["result"]
        return payload

    async def _eval_tab(self, tab_id: str, expression: str, *, timeout: int) -> Any:
        rc, stdout, stderr = await self._run_subprocess(
            [self._bin, "eval", expression, "--tab", tab_id, "--json"],
            timeout=timeout,
        )
        if rc != 0:
            raise RuntimeError(stderr[:300] or f"bb-browser eval failed with exit code {rc}")
        result = self._load_json_result(stdout)
        return result.get("result") if isinstance(result, dict) else result

    async def _wait_for_tab_text(self, tab_id: str, *, timeout: int) -> str:
        deadline = time.monotonic() + max(min(timeout, 10), 1)
        while True:
            remaining = max(1, math.ceil(deadline - time.monotonic()))
            text_value = await self._eval_tab(
                tab_id,
                "document.body?.innerText || document.documentElement.innerText || ''",
                timeout=remaining,
            )
            text = str(text_value or "").strip()
            if text:
                return text
            if time.monotonic() >= deadline:
                return ""
            await asyncio.sleep(1)

    async def _close_tab(self, tab_id: str, *, timeout: int) -> None:
        await self._run_subprocess(
            [self._bin, "close", "--tab", tab_id, "--json"],
            timeout=timeout,
        )

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        t0 = time.monotonic()
        try:
            cmd = _build_fetch_command(self._bin, url, opts)
        except ValueError as exc:
            return FetchResult(
                ok=False,
                url=url,
                engine=self.name,
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(exc),
            )

        rc, stdout, stderr = await self._run_subprocess(cmd, timeout=timeout)
        dur = (time.monotonic() - t0) * 1000

        if rc != 0:
            self._logger.warning("bb-browser exited %d: %s", rc, stderr[:200])
            return FetchResult(
                ok=False, url=url, engine=self.name,
                status=rc, duration_ms=dur,
                error=stderr[:300] or f"exit code {rc}",
            )

        # Adapter-backed site commands still return their final payload directly.
        if len(cmd) > 1 and cmd[1] == "site":
            text = stdout
            metadata: dict[str, Any] = {}

            try:
                data = json.loads(text)
                metadata = data if isinstance(data, dict) else {"items": data}
                text = json.dumps(data, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, ValueError):
                pass

            return FetchResult(
                ok=True,
                url=url,
                engine=self.name,
                text=text,
                duration_ms=dur,
                metadata=metadata,
            )

        metadata: dict[str, Any] = {}
        html = ""
        text = ""
        tab_id = ""

        try:
            open_result = self._load_json_result(stdout)
            if not isinstance(open_result, dict):
                raise ValueError("bb-browser open did not return a result object")
            tab_id = str(open_result.get("tabId", "")).strip()
            if not tab_id:
                raise ValueError("bb-browser open did not return a tabId")

            text_value = await self._wait_for_tab_text(tab_id, timeout=timeout)
            html_value = await self._eval_tab(
                tab_id,
                "document.documentElement.outerHTML",
                timeout=timeout,
            )
            text = str(text_value or "").strip()
            html = str(html_value or "")
            if not text and html:
                text = _extract_text_from_html(html)
            metadata = {"tabId": tab_id}
        except (json.JSONDecodeError, ValueError, RuntimeError) as exc:
            self._logger.warning("bb-browser generic fetch failed: %s", exc)
            return FetchResult(
                ok=False,
                url=url,
                engine=self.name,
                status=rc,
                duration_ms=dur,
                error=str(exc),
            )
        finally:
            if tab_id:
                try:
                    await self._close_tab(tab_id, timeout=timeout)
                except Exception as exc:
                    self._logger.debug("bb-browser close tab %s failed: %s", tab_id, exc)

        return FetchResult(
            ok=True,
            url=url,
            engine=self.name,
            text=text,
            html=html,
            duration_ms=dur,
            metadata=metadata,
        )

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "zh", **opts: Any
    ) -> list[SearchResult]:
        # Determine which search adapter to use
        search_engine = opts.get("engine", "")
        site = opts.get("site", "")

        if site and site in _SITE_SEARCH:
            adapter = _SITE_SEARCH[site]
        elif search_engine and search_engine in _SEARCH_ENGINES:
            adapter = _SEARCH_ENGINES[search_engine]
        else:
            # Default: baidu for Chinese, duckduckgo for English
            # (google/search is unreliable due to anti-bot detection)
            adapter = "baidu/search" if language == "zh" else "duckduckgo/search"

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
