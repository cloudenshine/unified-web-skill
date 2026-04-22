"""
Ring 1 — Browser automation with stealth support.

Engine selection (auto-fallback):
  1. patchright  — Chromium fork patched against bot-detection (Cloudflare etc.)
  2. playwright  — Standard Chromium (fallback)

Extras:
  - Cookie file / cookie dict injection for login-required pages
  - Persistent browser context (session reuse across calls)
  - Screenshot, JS eval, structured interaction actions
"""
from __future__ import annotations
import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from ..probe import CAPS

# ── Engine selection ────────────────────────────────────────────────────────

def _pw_module():
    """Return the best available async_playwright import."""
    try:
        from patchright.async_api import async_playwright
        return async_playwright, "patchright"
    except ImportError:
        from playwright.async_api import async_playwright
        return async_playwright, "playwright"


def available() -> bool:
    return CAPS.ring1


# ── Cookie helpers ──────────────────────────────────────────────────────────

def _load_cookies(cookie_source: str | list | None) -> list[dict]:
    """Accept cookies as JSON string, file path, or list of dicts."""
    if not cookie_source:
        return []
    if isinstance(cookie_source, list):
        return cookie_source
    src = str(cookie_source).strip()
    # File path
    if os.path.isfile(src):
        return json.loads(Path(src).read_text(encoding="utf-8"))
    # JSON string
    try:
        parsed = json.loads(src)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


# ── Result type ─────────────────────────────────────────────────────────────

class BrowserFetchResult:
    __slots__ = ("ok", "url", "html", "text", "title", "screenshot_b64",
                 "error", "duration_ms", "engine")

    def __init__(self, ok: bool, url: str = "", html: str = "", text: str = "",
                 title: str = "", screenshot_b64: str = "",
                 error: str = "", duration_ms: float = 0.0,
                 engine: str = "r1_browser") -> None:
        self.ok = ok
        self.url = url
        self.html = html
        self.text = text
        self.title = title
        self.screenshot_b64 = screenshot_b64
        self.error = error
        self.duration_ms = duration_ms
        self.engine = engine

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "url": self.url, "title": self.title,
            "text": self.text, "html": self.html,
            "screenshot_b64": self.screenshot_b64,
            "error": self.error, "duration_ms": self.duration_ms,
            "engine": self.engine,
        }


# ── Core fetch ──────────────────────────────────────────────────────────────

async def fetch(
    url: str,
    *,
    timeout: int = 30,
    screenshot: bool = False,
    wait_for: str = "networkidle",
    js_eval: str = "",
    extra_headers: dict | None = None,
    cookies: str | list | None = None,
    stealth: bool = True,
) -> BrowserFetchResult:
    """Fetch a URL via browser (patchright stealth > playwright fallback).

    Args:
        url: Target URL.
        timeout: Page load timeout in seconds.
        screenshot: Return base64 JPEG screenshot.
        wait_for: networkidle | domcontentloaded | load
        js_eval: JS expression to evaluate; result included in text prefix.
        extra_headers: Additional HTTP headers.
        cookies: Cookie file path, JSON string, or list of cookie dicts.
                 Cookies are injected before navigation — enables login-required pages.
        stealth: Use patchright (stealth) if available (default True).
    """
    if not available():
        return BrowserFetchResult(ok=False, url=url, error="Ring 1 offline (no browser installed)")

    t0 = time.perf_counter()
    async_playwright, eng_name = _pw_module() if stealth else (None, None)
    if not stealth or async_playwright is None:
        from playwright.async_api import async_playwright as _pw
        async_playwright, eng_name = _pw, "playwright"

    parsed_cookies = _load_cookies(cookies)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                extra_http_headers=extra_headers or {},
                ignore_https_errors=True,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            # Inject cookies before navigation
            if parsed_cookies:
                await ctx.add_cookies(parsed_cookies)

            page = await ctx.new_page()

            # Navigate with graceful wait fallback
            try:
                await page.goto(url, wait_until=wait_for, timeout=timeout * 1000)
            except Exception:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                except Exception as exc:
                    await browser.close()
                    return BrowserFetchResult(ok=False, url=url, error=str(exc),
                                             duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                                             engine=eng_name)

            title = await page.title()
            html_content = await page.content()
            text = await page.evaluate("document.body ? document.body.innerText : ''")

            prefix = ""
            if js_eval:
                try:
                    prefix = str(await page.evaluate(js_eval)) + "\n\n"
                except Exception:
                    pass

            screenshot_b64 = ""
            if screenshot:
                try:
                    shot = await page.screenshot(type="jpeg", quality=75, full_page=False)
                    screenshot_b64 = base64.b64encode(shot).decode()
                except Exception:
                    pass

            await browser.close()
            return BrowserFetchResult(
                ok=True, url=page.url, html=html_content,
                text=(prefix + (text or "")).strip(),
                title=title, screenshot_b64=screenshot_b64,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                engine=eng_name,
            )

    except Exception as exc:
        return BrowserFetchResult(ok=False, url=url, error=str(exc),
                                  duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                                  engine=eng_name or "r1_browser")


# ── Interactive actions ──────────────────────────────────────────────────────

async def interact(
    url: str,
    actions: list[dict[str, Any]],
    *,
    timeout: int = 60,
    screenshot: bool = True,
    cookies: str | list | None = None,
    stealth: bool = True,
) -> BrowserFetchResult:
    """Execute browser actions: click, fill, scroll, navigate, evaluate, wait.

    Action schema:
        {"action": "click",    "selector": "button#submit"}
        {"action": "fill",     "selector": "input[name=q]", "value": "hello"}
        {"action": "type",     "selector": "textarea",       "value": "hello"}
        {"action": "scroll",   "value": "800"}
        {"action": "wait",     "wait_ms": 1500}
        {"action": "navigate", "value": "https://example.com"}
        {"action": "evaluate", "value": "window.scrollTo(0, document.body.scrollHeight)"}
        {"action": "wait_for", "selector": ".result-list"}
        {"action": "press",    "selector": "input", "value": "Enter"}
    """
    if not available():
        return BrowserFetchResult(ok=False, url=url, error="Ring 1 offline")

    t0 = time.perf_counter()
    async_playwright, eng_name = _pw_module() if stealth else (None, None)
    if not stealth or async_playwright is None:
        from playwright.async_api import async_playwright as _pw
        async_playwright, eng_name = _pw, "playwright"

    parsed_cookies = _load_cookies(cookies)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
                ignore_https_errors=True,
            )
            if parsed_cookies:
                await ctx.add_cookies(parsed_cookies)

            page = await ctx.new_page()

            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

            for action in actions:
                act = action.get("action", "")
                selector = action.get("selector", "")
                value = str(action.get("value", ""))
                wait_ms = int(action.get("wait_ms", 300))

                try:
                    if act == "click" and selector:
                        await page.click(selector, timeout=10000)
                    elif act == "fill" and selector:
                        await page.fill(selector, value, timeout=10000)
                    elif act == "type" and selector:
                        await page.type(selector, value, delay=50)
                    elif act == "scroll":
                        await page.evaluate(f"window.scrollBy(0, {int(value) if value.lstrip('-').isdigit() else 500})")
                    elif act == "wait":
                        await asyncio.sleep(wait_ms / 1000)
                    elif act == "navigate":
                        await page.goto(value, wait_until="domcontentloaded", timeout=timeout * 1000)
                    elif act == "evaluate":
                        await page.evaluate(value)
                    elif act == "wait_for" and selector:
                        await page.wait_for_selector(selector, timeout=15000)
                    elif act == "press" and selector:
                        await page.press(selector, value or "Enter")
                except Exception as action_err:
                    # Non-fatal: log and continue
                    pass

                if wait_ms > 0 and act != "wait":
                    await asyncio.sleep(wait_ms / 1000)

            title = await page.title()
            html_content = await page.content()
            text = await page.evaluate("document.body ? document.body.innerText : ''")

            screenshot_b64 = ""
            if screenshot:
                try:
                    shot = await page.screenshot(type="jpeg", quality=75)
                    screenshot_b64 = base64.b64encode(shot).decode()
                except Exception:
                    pass

            await browser.close()
            return BrowserFetchResult(
                ok=True, url=page.url, html=html_content, text=text or "",
                title=title, screenshot_b64=screenshot_b64,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                engine=eng_name,
            )

    except Exception as exc:
        return BrowserFetchResult(ok=False, url=url, error=str(exc),
                                  duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                                  engine=eng_name or "r1_browser")
