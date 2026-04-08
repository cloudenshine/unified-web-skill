"""URL routing heuristics and block detection."""
import re
import logging
from urllib.parse import urlparse

from ..constants import (
    INTERACTIVE_KEYWORDS,
    BLOCK_MARKERS,
    BLOCKED_STATUS_CODES,
    JS_FRAMEWORK_HINTS,
)

_logger = logging.getLogger(__name__)


def is_interactive_task(text: str) -> bool:
    """Check if task description suggests browser interaction is needed."""
    lower = text.lower()
    return any(k in lower for k in INTERACTIVE_KEYWORDS)


def is_blocked_response(status: int, body: str = "") -> bool:
    """Check if response indicates blocking."""
    if status in BLOCKED_STATUS_CODES:
        return True
    if body:
        lower = body[:5000].lower()
        return any(marker in lower for marker in BLOCK_MARKERS)
    return False


def is_js_heavy(url: str, html: str = "") -> bool:
    """Check if URL/content suggests JavaScript-heavy page."""
    combined = (url + " " + html[:2000]).lower()
    return any(hint in combined for hint in JS_FRAMEWORK_HINTS)


def suggest_fetch_mode(url: str, task_text: str = "", is_chinese: bool = False) -> str:
    """Suggest fetch mode based on URL and task context.

    Returns: 'pinchtab', 'dynamic', 'http', 'stealth'
    """
    if is_interactive_task(task_text):
        return "pinchtab"
    if is_chinese:
        return "dynamic"
    if is_js_heavy(url):
        return "dynamic"
    return "http"


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    # Add scheme if missing so urlparse works correctly
    if "://" not in url:
        url = "http://" + url
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""
