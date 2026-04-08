"""Consolidated constants — single source of truth for the unified web skill."""

# ---------------------------------------------------------------------------
# Interactive task keywords (Chinese + English)
# ---------------------------------------------------------------------------
INTERACTIVE_KEYWORDS_ZH: list[str] = [
    "点击", "登录", "填写", "提交", "输入", "注册",
    "选择", "下拉", "弹窗", "验证", "滚动", "翻页", "加载更多",
]

INTERACTIVE_KEYWORDS_EN: list[str] = [
    "click", "login", "fill", "submit", "type", "register",
    "select", "dropdown", "popup", "verify", "scroll", "paginate",
    "load more", "sign in", "sign up",
]

INTERACTIVE_KEYWORDS: list[str] = INTERACTIVE_KEYWORDS_ZH + INTERACTIVE_KEYWORDS_EN

# ---------------------------------------------------------------------------
# Block / anti-bot detection markers
# ---------------------------------------------------------------------------
BLOCK_MARKERS: list[str] = [
    "captcha", "access denied", "cloudflare", "just a moment",
    "not a robot", "unusual traffic", "ip has been blocked",
    "challenge-running", "rate limit", "too many requests",
    "bot detection", "please verify", "human verification",
    "security check", "blocked", "forbidden",
]

BLOCKED_STATUS_CODES: set[int] = {401, 403, 407, 429, 500, 502, 503, 504}

# ---------------------------------------------------------------------------
# JS framework indicators
# ---------------------------------------------------------------------------
JS_FRAMEWORK_HINTS: list[str] = [
    "__next", "__nuxt", "react", "vue", "angular",
    "webpack", "gatsby", "remix", "svelte", "vite",
]

# ---------------------------------------------------------------------------
# Chinese-centric domains (often need special handling)
# ---------------------------------------------------------------------------
CHINESE_DOMAINS: list[str] = [
    "bilibili.com", "zhihu.com", "weibo.com", "douyin.com",
    "xiaohongshu.com", "baidu.com", "toutiao.com", "163.com",
    "qq.com", "sohu.com", "sina.com.cn", "csdn.net",
    "cnblogs.com", "juejin.cn", "jianshu.com", "taobao.com",
    "jd.com", "tmall.com", "pinduoduo.com", "meituan.com",
    "douban.com", "iqiyi.com", "youku.com", "wechat.com",
    "36kr.com", "huxiu.com", "leiphone.com", "thepaper.cn",
    "caixin.com", "yicai.com", "people.com.cn", "xinhuanet.com",
    "chinadaily.com.cn",
]

# ---------------------------------------------------------------------------
# Trusted source domains (gov, edu, major institutions)
# ---------------------------------------------------------------------------
TRUSTED_DOMAINS: set[str] = {
    # Chinese government / education
    "gov.cn", "edu.cn", "ac.cn",
    # Other government
    "gov.uk", "gov.us", "gov.au",
    # Education / academic
    "edu", "ac.uk", "ac.jp",
    # International organisations
    "who.int", "un.org", "worldbank.org",
    # Academic publishers
    "nature.com", "science.org", "ieee.org", "acm.org",
    # Wire services
    "reuters.com", "apnews.com", "bbc.com",
    # Research repositories
    "arxiv.org", "pubmed.ncbi.nlm.nih.gov",
}

# ---------------------------------------------------------------------------
# Known media outlets
# ---------------------------------------------------------------------------
KNOWN_MEDIA: set[str] = {
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "bloomberg.com", "ft.com", "economist.com",
    "xinhuanet.com", "people.com.cn", "chinadaily.com.cn",
    "caixin.com", "thepaper.cn", "yicai.com",
    "36kr.com", "huxiu.com", "leiphone.com",
}

# ---------------------------------------------------------------------------
# Known tech / developer sources
# ---------------------------------------------------------------------------
KNOWN_TECH: set[str] = {
    "github.com", "stackoverflow.com", "dev.to",
    "hackernews.com", "news.ycombinator.com",
    "medium.com", "substack.com",
    "csdn.net", "cnblogs.com", "juejin.cn",
}

# ---------------------------------------------------------------------------
# Fetch modes
# ---------------------------------------------------------------------------
FETCH_MODE_HTTP = "http"
FETCH_MODE_DYNAMIC = "dynamic"
FETCH_MODE_STEALTH = "stealth"
FETCH_MODE_PINCHTAB = "pinchtab"

# ---------------------------------------------------------------------------
# Default timeouts (seconds)
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_HTTP = 10
DEFAULT_TIMEOUT_DYNAMIC = 30
DEFAULT_TIMEOUT_STEALTH = 60
DEFAULT_TIMEOUT_PINCHTAB = 60

# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------
OUTPUT_FORMAT_JSON = "json"
OUTPUT_FORMAT_NDJSON = "ndjson"
OUTPUT_FORMAT_MD = "md"
