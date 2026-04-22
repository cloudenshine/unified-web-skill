"""
Ring 2 — CLI engine commands (bb-browser / opencli).

Uses FULL ABSOLUTE PATHS from probe — no PATH dependency.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Any

from ..probe import CAPS


def available() -> bool:
    return CAPS.ring2


def bb_browser_path() -> str:
    return CAPS.bb_browser_path


def opencli_path() -> str:
    return CAPS.opencli_path


class CliResult:
    __slots__ = ("ok", "site", "command", "data", "engine", "error", "duration_ms")

    def __init__(self, ok: bool, site: str = "", command: str = "",
                 data: Any = None, engine: str = "", error: str = "",
                 duration_ms: float = 0.0) -> None:
        self.ok = ok
        self.site = site
        self.command = command
        self.data = data
        self.engine = engine
        self.error = error
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "site": self.site, "command": self.command,
            "data": self.data, "engine": self.engine, "error": self.error,
            "duration_ms": self.duration_ms,
        }


async def _run(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return (proc.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"))
    except asyncio.TimeoutError:
        return (-1, "", f"Timeout after {timeout}s")
    except Exception as exc:
        return (-2, "", str(exc))


async def run_bb_browser(site: str, command: str, args: list[str] = (), timeout: int = 20) -> CliResult:
    """Run: bb-browser site {site}/{command} [args] --json"""
    t0 = time.perf_counter()
    path = bb_browser_path()
    if not path:
        return CliResult(ok=False, site=site, command=command, engine="bb-browser",
                         error="bb-browser binary not found", duration_ms=0)

    cmd = [path, "site", f"{site}/{command}"] + list(args) + ["--json"]
    rc, stdout, stderr = await _run(cmd, timeout=timeout)
    duration_ms = round((time.perf_counter() - t0) * 1000, 1)

    if rc == 0 and stdout.strip():
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = stdout.strip()
            return CliResult(ok=True, site=site, command=command, data=data,
                             engine="bb-browser", duration_ms=duration_ms)
        # Check if bb-browser itself reports failure (success: false)
        if isinstance(data, dict) and data.get("success") is False:
            err = data.get("error", "bb-browser: site not found")
            return CliResult(ok=False, site=site, command=command, engine="bb-browser",
                             error=err, duration_ms=duration_ms)
        return CliResult(ok=True, site=site, command=command, data=data,
                         engine="bb-browser", duration_ms=duration_ms)

    return CliResult(ok=False, site=site, command=command, engine="bb-browser",
                     error=stderr.strip() or f"exit {rc}", duration_ms=duration_ms)


async def run_opencli(site: str, command: str, args: list[str] = (), timeout: int = 20) -> CliResult:
    """Run: opencli {site} {command} [args] --format json"""
    t0 = time.perf_counter()
    path = opencli_path()
    if not path:
        return CliResult(ok=False, site=site, command=command, engine="opencli",
                         error="opencli binary not found", duration_ms=0)

    cmd = [path, site, command] + list(args) + ["--format", "json"]
    rc, stdout, stderr = await _run(cmd, timeout=timeout)
    duration_ms = round((time.perf_counter() - t0) * 1000, 1)

    if rc == 0 and stdout.strip():
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = stdout.strip()
        return CliResult(ok=True, site=site, command=command, data=data,
                         engine="opencli", duration_ms=duration_ms)

    return CliResult(ok=False, site=site, command=command, engine="opencli",
                     error=stderr.strip() or f"exit {rc}", duration_ms=duration_ms)


async def site_command(site: str, command: str, args: list[str] = (), timeout: int = 20) -> CliResult:
    """Try bb-browser first, fall back to opencli."""
    if bb_browser_path():
        result = await run_bb_browser(site, command, args, timeout=timeout)
        if result.ok:
            return result

    if opencli_path():
        result = await run_opencli(site, command, args, timeout=timeout)
        return result

    return CliResult(ok=False, site=site, command=command,
                     error="No CLI engines available (bb-browser and opencli not found)")
