"""inject.py — Credential injection helpers for engine subprocesses.

Provides utilities to inject platform cookies/tokens into engine subprocesses
as environment variables or CLI arguments.
"""

from __future__ import annotations

import logging
from typing import Any

from .config import CredentialStore

_logger = logging.getLogger(__name__)


# -- Domain-to-platform mapping for cookie injection --------------------------

# Maps URL hostname patterns to credential platform names.
# Keep in sync with extractor.PLATFORM_DOMAINS
_HOST_TO_PLATFORM: dict[str, str] = {
    "twitter.com":      "twitter",
    "x.com":            "twitter",
    "xiaohongshu.com":  "xiaohongshu",
    "xhslink.com":      "xiaohongshu",
    "bilibili.com":     "bilibili",
    "b23.tv":           "bilibili",
    "xueqiu.com":       "xueqiu",
    "zhihu.com":        "zhihu",
}


def platform_for_url(url: str) -> str | None:
    """Return the credential platform name for a URL, or None."""
    from urllib.parse import urlparse
    try:
        host = (urlparse(url).hostname or "").removeprefix("www.").lower()
    except Exception:
        return None
    return _HOST_TO_PLATFORM.get(host)


# -- Environment variable injection -------------------------------------------

def env_for_platform(platform: str) -> dict[str, str]:
    """Return environment variables to set for the given platform.

    These vars are recognised by engine CLIs (`opencli`,
    etc.) and will be merged into the subprocess environment at spawn time.

    Returns an empty dict when no credentials exist.
    """
    store = CredentialStore.get_instance()
    creds = store.get_all(platform)
    if not creds:
        return {}

    env: dict[str, str] = {}

    if platform == "twitter":
        if "auth_token" in creds:
            env["TWITTER_AUTH_TOKEN"] = creds["auth_token"]
        if "ct0" in creds:
            env["TWITTER_CT0"] = creds["ct0"]

    elif platform == "xiaohongshu":
        if "cookies" in creds:
            env["XHS_COOKIES"] = creds["cookies"]

    elif platform == "bilibili":
        if "SESSDATA" in creds:
            env["BILI_SESSDATA"] = creds["SESSDATA"]
        if "bili_jct" in creds:
            env["BILI_JCT"] = creds["bili_jct"]

    elif platform == "xueqiu" and "cookies" in creds:
        env["XUEQIU_COOKIE"] = creds["cookies"]

    return env


def env_for_url(url: str) -> dict[str, str]:
    """Resolve a URL to platform credentials and return env vars."""
    plat = platform_for_url(url)
    if plat is None:
        return {}
    return env_for_platform(plat)


# -- Cookie header injection (for HTTP engines) -------------------------------

def cookie_header_for_platform(platform: str) -> str:
    """Build a raw `Cookie` header for platforms that need it.

    For `xiaohongshu` and `xueqiu` the entire credential string *is*
    the cookie value; for others we build `name=value; name=value`.
    """
    store = CredentialStore.get_instance()
    creds = store.get_all(platform)
    if not creds:
        return ""

    if platform in ("xiaohongshu", "xueqiu"):
        # The full raw cookie string is stored under "cookies"
        return creds.get("cookies", "")

    # Standard name=value pairs
    parts: list[str] = []
    for k, v in creds.items():
        if k != "cookies":
            parts.append(f"{k}={v}")

    return "; ".join(parts)



