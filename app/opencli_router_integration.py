"""opencli_router_integration.py — OpenCLI 路由决策"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from . import config

logger = logging.getLogger(__name__)


class OpenCLIRouter:
    """
    判断 URL 是否属于 OpenCLI 支持的站点白名单，
    并返回对应的 (site, command) 元组。
    白名单从 config.OPENCLI_ALLOWLIST 加载。
    """

    # 域名 → 站点标识符的映射（硬编码常用站点）
    _DOMAIN_SITE_MAP: dict[str, str] = {
        "bilibili.com": "bilibili",
        "zhihu.com": "zhihu",
        "news.ycombinator.com": "hackernews",
        "reddit.com": "reddit",
        "weibo.com": "weibo",
        "douban.com": "douban",
        "github.com": "github",
        "twitter.com": "twitter",
        "x.com": "twitter",
    }

    def __init__(self) -> None:
        self._allowlist: dict[str, str] = dict(config.OPENCLI_ALLOWLIST)

    def _url_to_site(self, url: str) -> str | None:
        """从 URL 中识别站点标识符"""
        try:
            domain = urlparse(url).netloc.removeprefix("www.")
        except Exception:
            return None
        # exact match first
        if domain in self._DOMAIN_SITE_MAP:
            return self._DOMAIN_SITE_MAP[domain]
        # suffix match (e.g. sub.bilibili.com)
        for key, site in self._DOMAIN_SITE_MAP.items():
            if domain.endswith("." + key):
                return site
        return None

    def get_opencli_command(self, url: str) -> tuple[str, str] | None:
        """
        若 URL 匹配白名单，返回 (site, command)；否则返回 None。
        """
        site = self._url_to_site(url)
        if site is None:
            return None
        if site not in self._allowlist:
            return None
        command = self._allowlist[site]
        return site, command

    def is_supported(self, url: str) -> bool:
        return self.get_opencli_command(url) is not None

    def add_site(self, site: str, command: str, domains: list[str] | None = None) -> None:
        """运行时动态注册站点"""
        self._allowlist[site] = command
        if domains:
            for d in domains:
                self._DOMAIN_SITE_MAP[d] = site


# 模块级单例
_router: OpenCLIRouter | None = None


def get_router() -> OpenCLIRouter:
    global _router
    if _router is None:
        _router = OpenCLIRouter()
    return _router
