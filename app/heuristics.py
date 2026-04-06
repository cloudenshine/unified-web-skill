"""heuristics.py — 路由决策（中英文双语关键词）"""
from urllib.parse import urlparse

INTERACTIVE_HINTS_ZH = (
    "点击", "登录", "填写", "提交", "注册", "勾选", "选择", "下一页",
    "加载更多", "翻页", "滚动", "输入", "验证码", "结账", "购买"
)
INTERACTIVE_HINTS_EN = (
    "click", "fill", "login", "submit", "checkout", "signup",
    "scroll", "select", "checkbox", "dropdown", "next page", "load more",
    "captcha", "register", "input", "type"
)
INTERACTIVE_HINTS = INTERACTIVE_HINTS_ZH + INTERACTIVE_HINTS_EN

JS_HINTS = (
    "__next", "__next_data__", "react", "vue", "webpack", "angular",
    "application/json", "spa", "_app", "nuxt", "svelte"
)

BLOCK_STATUS = {401, 403, 407, 429, 500, 502, 503, 504}
# Use phrases that are unambiguous — avoid single words like "bot" (matches "robots")
# or "blocked" (common in CSS class names) or "challenge" (generic)
BLOCK_MARKERS = (
    "captcha",
    "access denied",
    "detected as a bot",
    "you are a bot",
    "are you a robot",
    "not a robot",        # "I am not a robot" checkbox text
    "cloudflare ray id",  # CF challenge page signature
    "just a moment",      # CF challenge page
    "ddos protection by cloudflare",
    "security check",
    "your ip has been blocked",
    "your request has been blocked",
    "unusual traffic",
    "automated access",
)

# Trusted TLDs/domains for source scoring
TRUSTED_TLDS = {".gov", ".edu", ".ac.", ".org"}
KNOWN_TRUSTED = {"wikipedia.org", "reuters.com", "bbc.com", "nature.com",
                 "scholar.google.com", "arxiv.org", "pubmed.ncbi.nlm.nih.gov"}


def is_interactive_text(text: str) -> bool:
    l = (text or "").lower()
    return any(k in l for k in INTERACTIVE_HINTS)


def url_js_hint(url: str) -> bool:
    l = (url or "").lower()
    return any(p in l for p in JS_HINTS)


def is_blocked_status(status: int) -> bool:
    return status in BLOCK_STATUS


def body_blocked(body: str) -> bool:
    l = (body or "").lower()
    return any(m in l for m in BLOCK_MARKERS)


def auto_route(url: str, task_text: str) -> str:
    """返回: 'pinchtab' | 'dynamic' | 'http'"""
    if is_interactive_text(task_text):
        return "pinchtab"
    if url_js_hint(url):
        return "dynamic"
    return "http"


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # strip www.
        return host.removeprefix("www.")
    except Exception:
        return url


def score_domain_trust(url: str) -> float:
    """Return trust score 0.0–1.0 for URL domain"""
    domain = extract_domain(url)
    if not domain:
        return 0.3
    # exact match
    for trusted in KNOWN_TRUSTED:
        if domain == trusted or domain.endswith("." + trusted):
            return 0.95
    # TLD match
    full = "." + domain
    for tld in TRUSTED_TLDS:
        if tld in full:
            return 0.85
    # .com / .net / .io — neutral
    if domain.endswith((".com", ".net", ".io", ".co")):
        return 0.55
    return 0.45
