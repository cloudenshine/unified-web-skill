"""extractor.py — Browser cookie extraction for platform credentials.

Wraps `browser_cookie3` to extract cookies for known social/video platforms
from Chrome, Edge, Firefox, Opera, Brave, and Chromium.

Also provides a migration path from Agent Reach's `~/.agent-reach/config.yaml`.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .config import CredentialStore, _cred_dir
from ..exceptions import CookieExtractionError, WebSkillError

try:
    import browser_cookie3 as bc3
    HAS_BC3 = True
except ImportError:
    HAS_BC3 = False

_logger = logging.getLogger(__name__)


# -- Error --------------------------------------------------------------------




# -- Platform / Domain mapping ------------------------------------------------

# Maps top-level platform names to the domains their cookies are stored under
PLATFORM_DOMAINS: dict[str, list[str]] = {
    "twitter":     ["twitter.com", "x.com"],
    "xiaohongshu": ["xiaohongshu.com", "xhslink.com"],
    "bilibili":    ["bilibili.com", "b23.tv"],
    "xueqiu":      ["xueqiu.com"],
    "zhihu":       ["zhihu.com"],
}

# Which cookie names to keep for each platform (empty = keep all found)
PLATFORM_KEY_MAP: dict[str, list[str]] = {
    "twitter":     ["auth_token", "ct0"],
    "bilibili":    ["SESSDATA", "bili_jct", "DedeUserID"],
    "xueqiu":      ["xq_a_token", "xq_id_token", "xq_r_token", "xq_is_login", "u"],
    # xiaohongshu uses raw cookie header, no specific key filter
}

# Browsers to try, in priority order
_BROWSERS = ["chrome", "chromium", "edge", "brave", "opera", "firefox"]


# -- Core extraction ----------------------------------------------------------

def _try_browser_cookies(domain: str, browser_name: str) -> dict[str, str]:
    """Extract cookies for *domain* from a single browser.

    Returns a flat `{cookie_name: cookie_value}` dict.  May return empty.
    """
    if not HAS_BC3:
        _logger.debug("browser_cookie3 not installed")
        return {}

    loader = getattr(bc3, browser_name, None)
    if loader is None:
        return {}

    result: dict[str, str] = {}
    try:
        jar = loader(domain_name=domain)
        for cookie in jar:
            if cookie.name and cookie.value:
                name = str(cookie.name).strip()
                value = str(cookie.value).strip()
                if name and value:
                    result[name] = value
    except PermissionError:
        _logger.debug("Permission denied reading %s cookies for %s", browser_name, domain)
        return {}
    except Exception as exc:
        _logger.debug("Failed to extract %s cookies from %s: %s", domain, browser_name, exc)
        return {}

    return result


def _merge_cookies(results: list[dict[str, str]]) -> dict[str, str]:
    """Merge several cookie dicts; first-found wins."""
    merged: dict[str, str] = {}
    for d in results:
        for k, v in d.items():
            if k not in merged:
                merged[k] = v
    return merged


# -- Public API ---------------------------------------------------------------

def extract_for_domain(domain: str) -> dict[str, str]:
    """Extract cookies for *domain* across all available browsers.

    Returns a flat `{name: value}` dict.  Raises :class:CookieExtractionError
    if no cookies could be read from any browser.
    """
    all_cookies: list[dict[str, str]] = []
    for browser in _BROWSERS:
        cookies = _try_browser_cookies(domain, browser)
        if cookies:
            _logger.info("Found %d cookies for %s in %s", len(cookies), domain, browser)
            all_cookies.append(cookies)

    merged = _merge_cookies(all_cookies)
    if not merged:
        raise CookieExtractionError(
            f"No cookies found for domain {domain!r} in any browser. "
            "Ensure you are logged into this site in Chrome/Edge/Firefox."
        )
    return merged


def extract_for_platform(platform: str) -> dict[str, str]:
    """Extract cookies for a named platform (e.g. `"twitter"`, `"bilibili"`).

    Returns a filtered dict containing only the keys relevant to that platform
    (based on :data:PLATFORM_KEY_MAP), or all cookies when no filter exists.

    Raises :class:CookieExtractionError on failure.
    """
    domains = PLATFORM_DOMAINS.get(platform)
    if not domains:
        raise CookieExtractionError(f"Unknown platform: {platform!r}")

    all_cookies: list[dict[str, str]] = []
    for domain in domains:
        try:
            cookies = extract_for_domain(domain)
            if cookies:
                all_cookies.append(cookies)
        except CookieExtractionError:
            continue

    merged = _merge_cookies(all_cookies)

    if not merged:
        raise CookieExtractionError(
            f"No cookies found for platform {platform!r} "
            f"(domains: {', '.join(domains)}). "
            "Log into the site in your browser first."
        )

    # Apply key filter if defined
    keys = PLATFORM_KEY_MAP.get(platform)
    if keys:
        filtered = {k: v for k, v in merged.items() if k in keys}
        if not filtered:
            raise CookieExtractionError(
                f"Found cookies for {platform!r} but none matched expected keys {keys}. "
                f"Available keys: {list(merged.keys())}"
            )
        return filtered

    # No filter — return all (e.g. xiaohongshu uses a raw cookie attribute)
    return merged


def extract_all() -> dict[str, dict[str, str]]:
    """Extract credentials for every known platform from browser cookies.

    Returns `{platform: {key: value}}`.  Silent on platforms where
    extraction fails.
    """
    result: dict[str, dict[str, str]] = {}
    for platform in PLATFORM_DOMAINS:
        try:
            creds = extract_for_platform(platform)
            if creds:
                result[platform] = creds
                _logger.info("Extracted %d credentials for %s", len(creds), platform)
        except CookieExtractionError as exc:
            _logger.info("No cookies for %s: %s", platform, exc)
    return result


def extract_to_store(platform: str | None = None) -> int:
    """Extract cookies and write to the :class:CredentialStore.

    Args:
        platform: If set, extract only this platform; otherwise extract all.

    Returns:
        Number of platforms successfully extracted.
    """
    store = CredentialStore.get_instance()

    if platform:
        sources = {platform: extract_for_platform(platform)}
    else:
        sources = extract_all()

    count = 0
    for plat, kv in sources.items():
        if kv:
            store.set_platform(plat, kv)
            count += 1

    if count > 0:
        store.save()

    return count


# -- Agent Reach migration ----------------------------------------------------

def _parse_agent_reach_yaml(path: str | Path) -> dict[str, str]:
    """Parse the flat key:value structure of `~/.agent-reach/config.yaml`."""
    import yaml
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Agent Reach config not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError(f"Unexpected Agent Reach config format: {type(raw).__name__}")

    return {str(k): str(v) for k, v in raw.items()}


_AGENT_REACH_MAP: dict[str, tuple[str, str]] = {
    "twitter_auth_token": ("twitter", "auth_token"),
    "twitter_ct0":        ("twitter", "ct0"),
}

_AGENT_REACH_PLATFORM_DIRECT: dict[str, str] = {
    "xueqiu_cookie": "xueqiu",
    # add more raw-cookie platforms here as they appear in Agent Reach
}


def import_from_agent_reach() -> dict[str, dict[str, str]]:
    """Import credentials from `~/.agent-reach/config.yaml`.

    Reads cookie/token values that the user already configured in Agent Reach
    and writes them into the UWS CredentialStore.

    Returns the imported `{platform: {key: value}}` map.
    """
    ar_path = Path.home() / ".agent-reach" / "config.yaml"
    raw = _parse_agent_reach_yaml(ar_path)

    store = CredentialStore.get_instance()
    imported: dict[str, dict[str, str]] = {}

    # 1. Named keys (auth_token, ct0, etc.)
    for ar_key, (platform, store_key) in _AGENT_REACH_MAP.items():
        val = raw.get(ar_key, "")
        if val:
            store.set(platform, store_key, val)
            imported.setdefault(platform, {})[store_key] = val

    # 2. Raw cookie blobs (xueqiu_cookie → raw cookie string)
    for ar_key, platform in _AGENT_REACH_PLATFORM_DIRECT.items():
        val = raw.get(ar_key, "")
        if val:
            store.set(platform, "cookies", val)
            imported.setdefault(platform, {})["cookies"] = val

    if imported:
        store.save()
        _logger.info("Imported %d platforms from Agent Reach", len(imported))
    else:
        _logger.info("No credentials imported from Agent Reach (config empty or missing)")

    return imported

