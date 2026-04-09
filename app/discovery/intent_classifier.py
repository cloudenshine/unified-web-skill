"""
Rule-based intent classifier for search queries.

Classifies queries into types to optimise search strategy.
No external dependencies — pure keyword / regex matching.
"""

from __future__ import annotations

import enum
import logging
import re

from ..utils.language import detect_language as _detect_language

_logger = logging.getLogger(__name__)


class QueryIntent(enum.Enum):
    """High-level intent behind a user query."""

    INFORMATIONAL = "informational"  # "什么是…" / "how to…"
    NAVIGATIONAL = "navigational"    # Direct site / brand queries
    TRANSACTIONAL = "transactional"  # "buy" / "price" / "下载"
    NEWS = "news"                    # Current events, breaking news
    ACADEMIC = "academic"            # Research papers, studies
    SOCIAL = "social"                # Social-media content
    CODE = "code"                    # Programming, tech docs
    FINANCE = "finance"              # Stock, market data
    LOCAL = "local"                  # Location-based queries


# ---------------------------------------------------------------------------
# Keyword patterns — each maps to a set of regex patterns (compiled lazily).
# Both Chinese and English keywords are included.
# ---------------------------------------------------------------------------

_PATTERN_DEFS: dict[QueryIntent, list[str]] = {
    QueryIntent.INFORMATIONAL: [
        # Chinese
        r"什么是", r"如何", r"怎么", r"为什么", r"怎样", r"是什么",
        r"有哪些", r"哪些", r"区别", r"对比", r"比较",
        r"原理", r"教程", r"入门", r"指南", r"解释",
        r"含义", r"意思", r"定义", r"概念", r"介绍",
        # English
        r"\bhow\s+to\b", r"\bwhat\s+is\b", r"\bwhy\b", r"\bexplain\b",
        r"\bdifference\s+between\b", r"\bguide\b", r"\btutorial\b",
        r"\bwhat\s+are\b", r"\bmeaning\s+of\b", r"\bdefinition\b",
        r"\bintroduction\b", r"\boverview\b", r"\bunderstand\b",
    ],
    QueryIntent.NAVIGATIONAL: [
        r"官网", r"官方网站", r"登录", r"注册", r"首页",
        r"\b\.com\b", r"\b\.cn\b", r"\b\.org\b", r"\b\.io\b",
        r"\bofficial\s+site\b", r"\blogin\b", r"\bsign\s*up\b",
        r"\bhomepage\b", r"\bdashboard\b",
    ],
    QueryIntent.TRANSACTIONAL: [
        # Chinese
        r"购买", r"下载", r"价格", r"多少钱", r"优惠",
        r"折扣", r"促销", r"包邮", r"下单", r"买",
        r"订购", r"订阅", r"试用", r"免费", r"开通",
        # English
        r"\bbuy\b", r"\bprice\b", r"\bdownload\b", r"\bcoupon\b",
        r"\bdiscount\b", r"\bcheap\b", r"\bdeal\b", r"\bfree\b",
        r"\border\b", r"\bsubscribe\b", r"\btrial\b",
    ],
    QueryIntent.NEWS: [
        # Chinese
        r"新闻", r"最新", r"今日", r"今天", r"昨天",
        r"突发", r"快讯", r"热点", r"热搜", r"实时",
        r"刚刚", r"速报", r"头条", r"发布会", r"公告",
        # English
        r"\bnews\b", r"\bbreaking\b", r"\blatest\b", r"\btoday\b",
        r"\byesterday\b", r"\brecent\b", r"\bupdate\b",
        r"\bannouncement\b", r"\btrending\b",
    ],
    QueryIntent.ACADEMIC: [
        # Chinese
        r"论文", r"研究", r"学术", r"期刊", r"综述",
        r"文献", r"引用", r"摘要", r"实验", r"算法",
        r"模型", r"数据集", r"基准",
        # English
        r"\bpaper\b", r"\bresearch\b", r"\bacademic\b", r"\bjournal\b",
        r"\bsurvey\b", r"\bcitation\b", r"\babstract\b",
        r"\barxiv\b", r"\bdoi\b", r"\bpeer.review\b",
        r"\bthesis\b", r"\bdissertation\b",
    ],
    QueryIntent.SOCIAL: [
        # Chinese
        r"微博", r"朋友圈", r"抖音", r"小红书", r"B站",
        r"弹幕", r"评论", r"点赞", r"转发", r"粉丝",
        r"关注", r"博主", r"网红", r"KOL", r"帖子",
        # English
        r"\btweet\b", r"\breddit\b", r"\bpost\b", r"\bfollowers\b",
        r"\bhashtag\b", r"\bviral\b", r"\bmeme\b",
        r"\binfluencer\b", r"\bthread\b", r"\bsocial\s+media\b",
    ],
    QueryIntent.CODE: [
        # Chinese
        r"代码", r"编程", r"开发", r"报错", r"bug",
        r"源码", r"接口", r"框架", r"库",
        # English
        r"\bcode\b", r"\bprogramming\b", r"\bapi\b", r"\bsdk\b",
        r"\bgithub\b", r"\bstackoverflow\b", r"\bnpm\b", r"\bpip\b",
        r"\bbug\b", r"\berror\b", r"\bexception\b", r"\bdebug\b",
        r"\bfunction\b", r"\bclass\b", r"\blibrary\b", r"\bframework\b",
        r"\bpackage\b", r"\brepository\b", r"\bopen.source\b",
        r"\btypescript\b", r"\bpython\b", r"\brust\b", r"\bjava\b",
    ],
    QueryIntent.FINANCE: [
        # Chinese
        r"股票", r"基金", r"A股", r"港股", r"美股",
        r"涨", r"跌", r"行情", r"大盘", r"K线",
        r"市值", r"财报", r"利润", r"营收", r"分红",
        r"估值", r"市盈率", r"PE", r"ROE", r"ETF",
        # English
        r"\bstock\b", r"\bmarket\b", r"\binvest\b", r"\bfinance\b",
        r"\btrading\b", r"\bcrypto\b", r"\bbitcoin\b", r"\betf\b",
        r"\bdividend\b", r"\bearnings\b", r"\bportfolio\b",
        r"\bnasdaq\b", r"\bs&p\b",
    ],
    QueryIntent.LOCAL: [
        # Chinese
        r"附近", r"周边", r"哪里", r"地址", r"路线",
        r"导航", r"门店", r"餐厅", r"酒店", r"景点",
        r"地铁", r"公交", r"外卖", r"快递",
        # English
        r"\bnearby\b", r"\bnear\s+me\b", r"\bdirections\b",
        r"\blocation\b", r"\brestaurant\b", r"\bhotel\b",
        r"\bstore\b", r"\bmap\b", r"\baddress\b",
    ],
}

# Compiled pattern cache (built on first use)
_COMPILED: dict[QueryIntent, list[re.Pattern[str]]] | None = None


def _compile_patterns() -> dict[QueryIntent, list[re.Pattern[str]]]:
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in _PATTERN_DEFS.items()
        }
    return _COMPILED


# ---------------------------------------------------------------------------
# Source recommendations per intent + language
# ---------------------------------------------------------------------------

_SOURCE_MAP: dict[tuple[QueryIntent, str], list[str]] = {
    # zh
    (QueryIntent.INFORMATIONAL, "zh"): ["baidu", "zhihu", "google", "wikipedia"],
    (QueryIntent.NAVIGATIONAL, "zh"):  ["baidu", "google"],
    (QueryIntent.TRANSACTIONAL, "zh"): ["taobao", "jd", "smzdm", "baidu"],
    (QueryIntent.NEWS, "zh"):          ["baidu", "toutiao", "36kr", "weibo"],
    (QueryIntent.ACADEMIC, "zh"):      ["google", "arxiv", "zhihu", "baidu"],
    (QueryIntent.SOCIAL, "zh"):        ["weibo", "xiaohongshu", "zhihu", "bilibili"],
    (QueryIntent.CODE, "zh"):          ["github", "google", "csdn", "stackoverflow"],
    (QueryIntent.FINANCE, "zh"):       ["xueqiu", "eastmoney", "baidu"],
    (QueryIntent.LOCAL, "zh"):         ["baidu", "ctrip", "google"],
    # en
    (QueryIntent.INFORMATIONAL, "en"): ["google", "wikipedia", "duckduckgo"],
    (QueryIntent.NAVIGATIONAL, "en"):  ["google", "duckduckgo"],
    (QueryIntent.TRANSACTIONAL, "en"): ["google", "amazon", "duckduckgo"],
    (QueryIntent.NEWS, "en"):          ["google", "hackernews", "reddit", "bbc"],
    (QueryIntent.ACADEMIC, "en"):      ["google", "arxiv", "wikipedia"],
    (QueryIntent.SOCIAL, "en"):        ["twitter", "reddit", "google"],
    (QueryIntent.CODE, "en"):          ["github", "google", "stackoverflow", "npm"],
    (QueryIntent.FINANCE, "en"):       ["google", "yahoo", "bloomberg"],
    (QueryIntent.LOCAL, "en"):         ["google", "duckduckgo"],
}


class IntentClassifier:
    """Rule-based query intent classification.

    Uses keyword / regex patterns in both Chinese and English to determine
    the most likely intent behind a search query.  No ML models required.
    """

    def classify(self, query: str, language: str = "auto") -> QueryIntent:
        """Classify *query* into a :class:`QueryIntent`.

        Parameters
        ----------
        query:
            The raw search string.
        language:
            ``"zh"``, ``"en"``, ``"auto"`` (detect), or ``"mixed"``.

        Returns
        -------
        QueryIntent
            The best-matching intent.  Falls back to ``INFORMATIONAL``
            when no strong signal is found.
        """
        if language == "auto":
            language = self.detect_language(query)

        compiled = _compile_patterns()
        scores: dict[QueryIntent, int] = {intent: 0 for intent in QueryIntent}

        for intent, patterns in compiled.items():
            for pat in patterns:
                if pat.search(query):
                    scores[intent] += 1

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] == 0:
            return QueryIntent.INFORMATIONAL

        _logger.debug("intent scores for %r: %s → %s", query, scores, best)
        return best

    def get_recommended_sources(
        self, intent: QueryIntent, language: str = "zh"
    ) -> list[str]:
        """Return recommended search-engine names for *intent* + *language*.

        Falls back to a generic list when there is no specific mapping.
        """
        lang = language if language in ("zh", "en") else "en"
        key = (intent, lang)
        if key in _SOURCE_MAP:
            return list(_SOURCE_MAP[key])
        return ["google", "duckduckgo"]

    def detect_language(self, text: str) -> str:
        """Delegate to shared utility."""
        return _detect_language(text)
