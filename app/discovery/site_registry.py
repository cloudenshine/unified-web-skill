"""
Site capability registry — single source of truth for all known websites.

Maps domains → engines, commands, auth requirements, content types.
Replaces all scattered hardcoded domain lists throughout the old codebase.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)


@dataclass
class SiteCapability:
    """Describes a single website and how to interact with it."""

    site_id: str                                # e.g. "bilibili"
    display_name: str                           # e.g. "哔哩哔哩"
    domains: list[str]                          # e.g. ["bilibili.com", "b23.tv"]
    engines: list[str]                          # priority: ["bb-browser", "opencli", "scrapling"]
    commands: dict[str, str] = field(default_factory=dict)
    auth_required: bool = False
    auth_engine: str = ""                       # "pinchtab" | "bb-browser"
    content_type: str = "article"               # video|article|social|news|paper|code|finance|shopping|search|jobs
    country: str = "global"                     # cn|global|us|jp
    default_fetch_mode: str = "auto"            # http|dynamic|stealth|auto
    notes: str = ""


class SiteRegistry:
    """Singleton registry of all known sites and their capabilities.

    Usage::

        registry = SiteRegistry.get_instance()
        registry.load_builtin()

        cap = registry.lookup_by_url("https://www.bilibili.com/video/BV123")
        print(cap.engines)  # ["bb-browser", "opencli"]
    """

    _instance: Optional[SiteRegistry] = None

    def __init__(self) -> None:
        self._sites: dict[str, SiteCapability] = {}
        self._domain_index: dict[str, str] = {}  # domain → site_id
        self._loaded = False

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> SiteRegistry:
        """Return the global singleton, creating and loading builtins if needed."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load_builtin()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (useful in tests)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_from_file(self, path: str | Path) -> int:
        """Load site definitions from a JSON file.

        The file should contain a list of objects, each matching the
        :class:`SiteCapability` field names.

        Returns
        -------
        int
            Number of sites loaded.
        """
        p = Path(path)
        if not p.exists():
            _logger.warning("site registry file not found: %s", p)
            return 0

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _logger.error("failed to parse site registry file %s: %s", p, exc)
            return 0

        count = 0
        for entry in data:
            try:
                site = SiteCapability(**entry)
                self.register(site)
                count += 1
            except TypeError as exc:
                _logger.warning("skipping invalid site entry: %s", exc)
        _logger.info("loaded %d sites from %s", count, p)
        return count

    def load_builtin(self) -> int:
        """Load the built-in site catalogue (60+ sites).

        This is the single source of truth that replaces every scattered
        domain list in the old codebase.

        Returns
        -------
        int
            Number of sites registered.
        """
        sites = _builtin_sites()
        for site in sites:
            self.register(site)
        self._loaded = True
        _logger.info("loaded %d built-in sites", len(sites))
        return len(sites)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, site: SiteCapability) -> None:
        """Register (or overwrite) a site capability."""
        self._sites[site.site_id] = site
        for domain in site.domains:
            self._domain_index[domain.lower()] = site.site_id

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def lookup_by_domain(self, domain: str) -> Optional[SiteCapability]:
        """Find a site by domain, supporting subdomain matching.

        Tries an exact hit first, then progressively strips sub-domains.
        For example ``www.bilibili.com`` → ``bilibili.com``.
        """
        domain = domain.lower().rstrip(".")

        # Exact match
        if domain in self._domain_index:
            return self._sites[self._domain_index[domain]]

        # Suffix / parent-domain match
        parts = domain.split(".")
        for i in range(1, len(parts)):
            candidate = ".".join(parts[i:])
            if candidate in self._domain_index:
                return self._sites[self._domain_index[candidate]]

        return None

    def lookup_by_url(self, url: str) -> Optional[SiteCapability]:
        """Extract the domain from *url* and look it up."""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or parsed.path.split("/")[0]
        except Exception:
            return None
        if not host:
            return None
        return self.lookup_by_domain(host)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_search_engines(self) -> list[SiteCapability]:
        """Return sites that expose a ``search`` command."""
        return [s for s in self._sites.values() if "search" in s.commands]

    def get_sites_by_country(self, country: str) -> list[SiteCapability]:
        """Filter sites by ``country`` field (e.g. ``"cn"``)."""
        return [s for s in self._sites.values() if s.country == country]

    def get_sites_by_content_type(self, content_type: str) -> list[SiteCapability]:
        """Filter sites by ``content_type`` (e.g. ``"video"``)."""
        return [s for s in self._sites.values() if s.content_type == content_type]

    def get_preferred_engines(self, url: str) -> list[str]:
        """Return the engine priority list for *url*.

        Falls back to ``["scrapling", "http"]`` when the site is unknown.
        """
        cap = self.lookup_by_url(url)
        if cap:
            return list(cap.engines)
        return ["scrapling", "http"]

    def is_chinese_domain(self, url: str) -> bool:
        """``True`` if the URL belongs to a Chinese (``cn``) site."""
        cap = self.lookup_by_url(url)
        return cap is not None and cap.country == "cn"

    def needs_auth(self, url: str) -> bool:
        """``True`` if the site behind *url* requires authentication."""
        cap = self.lookup_by_url(url)
        return cap is not None and cap.auth_required

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @property
    def site_count(self) -> int:
        """Number of registered sites."""
        return len(self._sites)

    def all_sites(self) -> list[SiteCapability]:
        """Return every registered site."""
        return list(self._sites.values())

    def __contains__(self, site_id: str) -> bool:
        return site_id in self._sites

    def __getitem__(self, site_id: str) -> SiteCapability:
        return self._sites[site_id]


# ======================================================================
# Built-in site catalogue
# ======================================================================

def _builtin_sites() -> list[SiteCapability]:  # noqa: C901 — intentionally long
    """Return the full built-in site list (60+ entries)."""

    sites: list[SiteCapability] = []

    def _s(**kw: object) -> None:
        sites.append(SiteCapability(**kw))  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Chinese Social / Content
    # ------------------------------------------------------------------

    _s(
        site_id="bilibili",
        display_name="哔哩哔哩",
        domains=["bilibili.com", "b23.tv"],
        engines=["bb-browser", "opencli"],
        commands={"search": "bilibili/search", "hot": "bilibili/hot", "video": "bilibili/video"},
        content_type="video",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="zhihu",
        display_name="知乎",
        domains=["zhihu.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "zhihu/search", "hot": "zhihu/hot", "question": "zhihu/question"},
        content_type="article",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="weibo",
        display_name="微博",
        domains=["weibo.com", "m.weibo.cn", "weibo.cn"],
        engines=["bb-browser", "opencli"],
        commands={"search": "weibo/search", "hot": "weibo/hot"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="xiaohongshu",
        display_name="小红书",
        domains=["xiaohongshu.com", "xhslink.com"],
        engines=["bb-browser"],
        commands={"search": "xiaohongshu/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="cn",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="douban",
        display_name="豆瓣",
        domains=["douban.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "douban/search", "movie": "douban/movie"},
        content_type="article",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="douyin",
        display_name="抖音",
        domains=["douyin.com"],
        engines=["bb-browser"],
        commands={"search": "douyin/search", "hot": "douyin/hot"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="video",
        country="cn",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="tieba",
        display_name="百度贴吧",
        domains=["tieba.baidu.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "tieba/search"},
        content_type="social",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="qq",
        display_name="腾讯网",
        domains=["qq.com", "new.qq.com"],
        engines=["bb-browser", "scrapling"],
        commands={},
        content_type="news",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="baidu",
        display_name="百度",
        domains=["baidu.com", "m.baidu.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "baidu/search"},
        content_type="search",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="36kr",
        display_name="36氪",
        domains=["36kr.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "36kr/search", "hot": "36kr/hot"},
        content_type="news",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="csdn",
        display_name="CSDN",
        domains=["csdn.net", "blog.csdn.net"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "csdn/search"},
        content_type="code",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="cnblogs",
        display_name="博客园",
        domains=["cnblogs.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "cnblogs/search"},
        content_type="code",
        country="cn",
        default_fetch_mode="http",
    )
    _s(
        site_id="v2ex",
        display_name="V2EX",
        domains=["v2ex.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"hot": "v2ex/hot"},
        content_type="social",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="jike",
        display_name="即刻",
        domains=["okjike.com", "m.okjike.com"],
        engines=["bb-browser"],
        commands={"search": "jike/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="hupu",
        display_name="虎扑",
        domains=["hupu.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"hot": "hupu/hot"},
        content_type="social",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="linuxdo",
        display_name="LINUX DO",
        domains=["linux.do"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"hot": "linuxdo/hot", "search": "linuxdo/search"},
        content_type="social",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="toutiao",
        display_name="今日头条",
        domains=["toutiao.com", "m.toutiao.com"],
        engines=["bb-browser"],
        commands={"search": "toutiao/search", "hot": "toutiao/hot"},
        content_type="news",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="sohu",
        display_name="搜狐",
        domains=["sohu.com", "news.sohu.com"],
        engines=["bb-browser", "scrapling"],
        commands={},
        content_type="news",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="xiaoyuzhoufm",
        display_name="小宇宙FM",
        domains=["xiaoyuzhoufm.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "xiaoyuzhoufm/search"},
        content_type="article",
        country="cn",
        default_fetch_mode="dynamic",
        notes="Podcast platform",
    )
    _s(
        site_id="qidian",
        display_name="起点中文网",
        domains=["qidian.com"],
        engines=["bb-browser", "scrapling"],
        commands={"search": "qidian/search"},
        content_type="article",
        country="cn",
        default_fetch_mode="dynamic",
        notes="Web novel platform",
    )
    _s(
        site_id="youdao",
        display_name="有道",
        domains=["youdao.com", "dict.youdao.com"],
        engines=["opencli", "scrapling"],
        commands={"translate": "youdao/translate"},
        content_type="article",
        country="cn",
        default_fetch_mode="http",
        notes="Translation / dictionary",
    )
    _s(
        site_id="wechat",
        display_name="微信公众号",
        domains=["mp.weixin.qq.com", "weixin.qq.com"],
        engines=["bb-browser"],
        commands={"search": "wechat/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="article",
        country="cn",
        default_fetch_mode="stealth",
    )

    # ------------------------------------------------------------------
    # Chinese Finance / Commerce
    # ------------------------------------------------------------------

    _s(
        site_id="xueqiu",
        display_name="雪球",
        domains=["xueqiu.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "xueqiu/search", "hot": "xueqiu/hot"},
        content_type="finance",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="eastmoney",
        display_name="东方财富",
        domains=["eastmoney.com", "guba.eastmoney.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "eastmoney/search"},
        content_type="finance",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="boss",
        display_name="BOSS直聘",
        domains=["zhipin.com"],
        engines=["bb-browser"],
        commands={"search": "boss/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="jobs",
        country="cn",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="ctrip",
        display_name="携程",
        domains=["ctrip.com", "m.ctrip.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "ctrip/search"},
        content_type="shopping",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="smzdm",
        display_name="什么值得买",
        domains=["smzdm.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "smzdm/search", "hot": "smzdm/hot"},
        content_type="shopping",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="taobao",
        display_name="淘宝",
        domains=["taobao.com", "m.taobao.com"],
        engines=["bb-browser"],
        commands={"search": "taobao/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="shopping",
        country="cn",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="jd",
        display_name="京东",
        domains=["jd.com", "m.jd.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "jd/search"},
        content_type="shopping",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="pinduoduo",
        display_name="拼多多",
        domains=["pinduoduo.com"],
        engines=["bb-browser"],
        commands={"search": "pinduoduo/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="shopping",
        country="cn",
        default_fetch_mode="stealth",
    )

    # ------------------------------------------------------------------
    # Global Social
    # ------------------------------------------------------------------

    _s(
        site_id="twitter",
        display_name="X (Twitter)",
        domains=["twitter.com", "x.com", "mobile.twitter.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "twitter/search", "trending": "twitter/trending"},
        auth_required=True,
        auth_engine="pinchtab",
        content_type="social",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="reddit",
        display_name="Reddit",
        domains=["reddit.com", "old.reddit.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "reddit/search", "hot": "reddit/hot"},
        content_type="social",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="facebook",
        display_name="Facebook",
        domains=["facebook.com", "m.facebook.com", "fb.com"],
        engines=["bb-browser"],
        commands={},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="global",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="instagram",
        display_name="Instagram",
        domains=["instagram.com"],
        engines=["bb-browser"],
        commands={},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="global",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="tiktok",
        display_name="TikTok",
        domains=["tiktok.com"],
        engines=["bb-browser"],
        commands={"search": "tiktok/search"},
        content_type="video",
        country="global",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="discord",
        display_name="Discord",
        domains=["discord.com", "discord.gg"],
        engines=["bb-browser"],
        commands={},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="telegram",
        display_name="Telegram",
        domains=["telegram.org", "t.me"],
        engines=["bb-browser"],
        commands={},
        content_type="social",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="bluesky",
        display_name="Bluesky",
        domains=["bsky.app"],
        engines=["bb-browser", "scrapling"],
        commands={"search": "bluesky/search"},
        content_type="social",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="linkedin",
        display_name="LinkedIn",
        domains=["linkedin.com"],
        engines=["bb-browser"],
        commands={"search": "linkedin/search"},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="social",
        country="global",
        default_fetch_mode="stealth",
    )
    _s(
        site_id="mastodon",
        display_name="Mastodon",
        domains=["mastodon.social", "mastodon.online"],
        engines=["scrapling"],
        commands={},
        content_type="social",
        country="global",
        default_fetch_mode="http",
    )

    # ------------------------------------------------------------------
    # Global Tech
    # ------------------------------------------------------------------

    _s(
        site_id="github",
        display_name="GitHub",
        domains=["github.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "github/search", "trending": "github/trending", "repo": "github/repo"},
        content_type="code",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="stackoverflow",
        display_name="Stack Overflow",
        domains=["stackoverflow.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "stackoverflow/search"},
        content_type="code",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="hackernews",
        display_name="Hacker News",
        domains=["news.ycombinator.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"search": "hackernews/search", "hot": "hackernews/hot"},
        content_type="news",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="medium",
        display_name="Medium",
        domains=["medium.com"],
        engines=["bb-browser", "scrapling"],
        commands={},
        content_type="article",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="devto",
        display_name="DEV Community",
        domains=["dev.to"],
        engines=["opencli", "scrapling"],
        commands={"search": "devto/search"},
        content_type="code",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="npm",
        display_name="npm",
        domains=["npmjs.com", "www.npmjs.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "npm/search"},
        content_type="code",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="pypi",
        display_name="PyPI",
        domains=["pypi.org"],
        engines=["opencli", "scrapling"],
        commands={"search": "pypi/search"},
        content_type="code",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="arxiv",
        display_name="arXiv",
        domains=["arxiv.org"],
        engines=["opencli", "scrapling"],
        commands={"search": "arxiv/search"},
        content_type="paper",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="gitlab",
        display_name="GitLab",
        domains=["gitlab.com"],
        engines=["scrapling"],
        commands={},
        content_type="code",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="mdn",
        display_name="MDN Web Docs",
        domains=["developer.mozilla.org"],
        engines=["scrapling"],
        commands={},
        content_type="code",
        country="global",
        default_fetch_mode="http",
        notes="Mozilla developer documentation",
    )

    # ------------------------------------------------------------------
    # Global Content / Media
    # ------------------------------------------------------------------

    _s(
        site_id="youtube",
        display_name="YouTube",
        domains=["youtube.com", "youtu.be", "m.youtube.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "youtube/search", "trending": "youtube/trending"},
        content_type="video",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="wikipedia",
        display_name="Wikipedia",
        domains=["wikipedia.org", "en.wikipedia.org", "zh.wikipedia.org"],
        engines=["opencli", "scrapling"],
        commands={"search": "wikipedia/search"},
        content_type="article",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="bbc",
        display_name="BBC",
        domains=["bbc.com", "bbc.co.uk"],
        engines=["opencli", "scrapling"],
        commands={"search": "bbc/search"},
        content_type="news",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="reuters",
        display_name="Reuters",
        domains=["reuters.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "reuters/search"},
        content_type="news",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="producthunt",
        display_name="Product Hunt",
        domains=["producthunt.com"],
        engines=["bb-browser", "opencli", "scrapling"],
        commands={"hot": "producthunt/hot"},
        content_type="news",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="imdb",
        display_name="IMDb",
        domains=["imdb.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "imdb/search"},
        content_type="video",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="amazon",
        display_name="Amazon",
        domains=["amazon.com", "amazon.co.uk", "amazon.co.jp"],
        engines=["bb-browser", "scrapling"],
        commands={"search": "amazon/search"},
        content_type="shopping",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="nytimes",
        display_name="The New York Times",
        domains=["nytimes.com"],
        engines=["bb-browser", "scrapling"],
        commands={},
        content_type="news",
        country="us",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="cnn",
        display_name="CNN",
        domains=["cnn.com"],
        engines=["scrapling"],
        commands={},
        content_type="news",
        country="us",
        default_fetch_mode="http",
    )
    _s(
        site_id="spotify",
        display_name="Spotify",
        domains=["spotify.com", "open.spotify.com"],
        engines=["bb-browser"],
        commands={},
        auth_required=True,
        auth_engine="bb-browser",
        content_type="video",
        country="global",
        default_fetch_mode="dynamic",
        notes="Music / podcast streaming",
    )
    _s(
        site_id="twitch",
        display_name="Twitch",
        domains=["twitch.tv"],
        engines=["bb-browser"],
        commands={},
        content_type="video",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="quora",
        display_name="Quora",
        domains=["quora.com"],
        engines=["bb-browser", "scrapling"],
        commands={},
        content_type="article",
        country="global",
        default_fetch_mode="dynamic",
    )

    # ------------------------------------------------------------------
    # Search Engines
    # ------------------------------------------------------------------

    _s(
        site_id="google",
        display_name="Google",
        domains=["google.com", "www.google.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "google/search"},
        content_type="search",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="bing",
        display_name="Bing",
        domains=["bing.com", "www.bing.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "bing/search"},
        content_type="search",
        country="global",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="duckduckgo",
        display_name="DuckDuckGo",
        domains=["duckduckgo.com"],
        engines=["opencli", "scrapling"],
        commands={"search": "duckduckgo/search"},
        content_type="search",
        country="global",
        default_fetch_mode="http",
    )
    _s(
        site_id="sogou",
        display_name="搜狗",
        domains=["sogou.com"],
        engines=["bb-browser", "opencli"],
        commands={"search": "sogou/search"},
        content_type="search",
        country="cn",
        default_fetch_mode="dynamic",
    )
    _s(
        site_id="yandex",
        display_name="Yandex",
        domains=["yandex.com", "yandex.ru"],
        engines=["bb-browser", "scrapling"],
        commands={"search": "yandex/search"},
        content_type="search",
        country="global",
        default_fetch_mode="dynamic",
    )

    return sites
