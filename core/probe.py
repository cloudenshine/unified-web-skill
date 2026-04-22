"""Capability probe — detect what's available at runtime, once, at import time."""
from __future__ import annotations
import shutil
import subprocess
import sys
import os
from dataclasses import dataclass, field


@dataclass
class Capabilities:
    httpx: bool = False
    beautifulsoup: bool = False
    trafilatura: bool = False
    playwright: bool = False
    playwright_browsers: bool = False
    bb_browser_path: str = ""
    opencli_path: str = ""

    @property
    def ring0(self) -> bool:
        return self.httpx

    @property
    def ring1(self) -> bool:
        return self.playwright and self.playwright_browsers

    @property
    def ring2(self) -> bool:
        return bool(self.bb_browser_path or self.opencli_path)

    @property
    def ring3(self) -> bool:
        return self.ring0

    def summary(self) -> dict:
        return {
            "ring0_http": self.ring0,
            "ring1_browser": self.ring1,
            "ring2_cli": self.ring2,
            "ring3_pipeline": self.ring3,
            "details": {
                "httpx": self.httpx,
                "beautifulsoup": self.beautifulsoup,
                "trafilatura": self.trafilatura,
                "playwright": self.playwright,
                "playwright_browsers": self.playwright_browsers,
                "bb_browser": self.bb_browser_path or None,
                "opencli": self.opencli_path or None,
            }
        }


def _check_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _find_binary(name: str, env_key: str | None = None) -> str:
    """Return the absolute path of a binary, or '' if not found.

    Checks: env var override → shutil.which (system PATH) → common Windows npm paths.
    """
    if env_key:
        from_env = os.environ.get(env_key, "").strip()
        if from_env:
            # Could be a name or full path
            if os.path.isabs(from_env) and os.path.isfile(from_env):
                return from_env
            found = shutil.which(from_env)
            if found:
                return found

    # shutil.which searches PATH (cross-platform)
    found = shutil.which(name)
    if found:
        return found

    # Windows-specific: check common npm install locations
    win_candidates = [
        rf"D:\Programs\npm\{name}",
        rf"D:\Programs\npm\{name}.cmd",
        rf"C:\Users\Admin\AppData\Roaming\npm\{name}",
        rf"C:\Users\Admin\AppData\Roaming\npm\{name}.cmd",
        rf"C:\Program Files\nodejs\{name}",
    ]
    for candidate in win_candidates:
        if os.path.isfile(candidate):
            return candidate

    return ""


def _check_playwright_browsers() -> bool:
    """Check if Playwright Chromium browser is installed.

    Uses a subprocess ping to avoid event-loop conflicts when called inside
    an already-running asyncio context.
    """
    try:
        # Fast path: check the well-known install location directly
        import platform
        home = os.path.expanduser("~")
        if platform.system() == "Windows":
            candidates = [
                os.path.join(home, "AppData", "Local", "ms-playwright"),
            ]
        else:
            candidates = [
                os.path.join(home, ".cache", "ms-playwright"),
                os.path.join(home, "snap", "chromium"),
            ]
        for base in candidates:
            if os.path.isdir(base):
                # Walk one level to find a chromium dir
                for entry in os.listdir(base):
                    if "chromium" in entry.lower():
                        chromium_dir = os.path.join(base, entry)
                        # Check for chrome binary inside
                        for walk_root, _, files in os.walk(chromium_dir):
                            for fname in files:
                                if fname.lower() in ("chrome.exe", "chromium", "chrome"):
                                    return True
    except Exception:
        pass

    # Fallback: run playwright in a subprocess to avoid loop conflict
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "from playwright.sync_api import sync_playwright; "
             "p=sync_playwright().start(); "
             "print(p.chromium.executable_path); "
             "p.stop()"],
            capture_output=True, text=True, timeout=10,
        )
        path = result.stdout.strip()
        return bool(path) and os.path.isfile(path)
    except Exception:
        return False


def detect() -> Capabilities:
    caps = Capabilities()
    caps.httpx = _check_import("httpx")
    caps.beautifulsoup = _check_import("bs4")
    caps.trafilatura = _check_import("trafilatura")
    caps.playwright = _check_import("playwright")
    if caps.playwright:
        caps.playwright_browsers = _check_playwright_browsers()
    caps.bb_browser_path = _find_binary("bb-browser", "BB_BROWSER_BIN")
    caps.opencli_path = _find_binary("opencli", "OPENCLI_BIN")
    return caps


# Module-level singleton — probed once at import
CAPS: Capabilities = detect()
