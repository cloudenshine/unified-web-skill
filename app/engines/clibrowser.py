"""clibrowser.py — CLIBrowser engine: zero-dependency Rust-based browser."""
from __future__ import annotations

import json
import os
import time
from typing import Any

from .base import BaseEngine, Capability, FetchResult, SearchResult


class CLIBrowserEngine(BaseEngine):
    """Wraps the ``clibrowser`` Rust binary for lightweight fetch & search."""

    def __init__(self) -> None:
        self._bin = os.environ.get("CLIBROWSER_BIN", "clibrowser")
        super().__init__()

    @property
    def name(self) -> str:
        return "clibrowser"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.SEARCH}

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        rc, out, _ = await self._run_subprocess([self._bin, "--version"], timeout=10)
        if rc == 0 and out.strip():
            self._logger.debug("clibrowser version: %s", out.strip())
            return True
        # Fallback: try a simple fetch
        rc2, _, _ = await self._run_subprocess(
            [self._bin, "get", "https://httpbin.org/get"], timeout=15,
        )
        return rc2 == 0

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        t0 = time.monotonic()

        session = opts.get("session", "")
        stealth = opts.get("stealth", False)

        # Build command
        cmd: list[str] = [self._bin]
        if session:
            cmd.extend(["--session", session])
        if stealth:
            cmd.append("--stealth")
        cmd.extend(["get", url])

        rc, stdout, stderr = await self._run_subprocess(cmd, timeout=timeout)
        dur_get = (time.monotonic() - t0) * 1000

        if rc != 0:
            self._logger.warning("clibrowser get failed (%d): %s", rc, stderr[:200])
            return FetchResult(
                ok=False, url=url, engine=self.name,
                status=rc, duration_ms=dur_get,
                error=stderr[:300] or f"exit code {rc}",
            )

        # Convert to markdown for cleaner output
        md_cmd: list[str] = [self._bin]
        if session:
            md_cmd.extend(["--session", session])
        md_cmd.append("markdown")

        rc2, md_out, md_err = await self._run_subprocess(md_cmd, timeout=timeout)
        dur = (time.monotonic() - t0) * 1000

        if rc2 == 0 and md_out.strip():
            return FetchResult(
                ok=True, url=url, engine=self.name,
                text=md_out, html=stdout,
                duration_ms=dur,
                metadata={"format": "markdown"},
            )

        # Fallback: raw HTML output
        return FetchResult(
            ok=True, url=url, engine=self.name,
            html=stdout, text=stdout,
            duration_ms=dur,
        )

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "zh", **opts: Any
    ) -> list[SearchResult]:
        cmd = [self._bin, "search", query]
        rc, stdout, stderr = await self._run_subprocess(cmd, timeout=30)

        if rc != 0:
            self._logger.warning("clibrowser search failed (%d): %s", rc, stderr[:200])
            return []

        results: list[SearchResult] = []

        # Try JSON parsing first
        try:
            data = json.loads(stdout)
            items = data if isinstance(data, list) else data.get("results", data.get("items", []))
            for idx, item in enumerate(items[:max_results]):
                if isinstance(item, dict):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", item.get("link", "")),
                        snippet=item.get("snippet", item.get("description", "")),
                        rank=idx + 1,
                        source="clibrowser",
                        metadata=item,
                    ))
            return results
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: parse plain-text output (line-based)
        lines = stdout.strip().splitlines()
        idx = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Heuristic: lines with http are URLs
            if line.startswith("http://") or line.startswith("https://"):
                results.append(SearchResult(
                    url=line, rank=idx + 1, source="clibrowser",
                ))
                idx += 1
            elif results and not results[-1].title:
                results[-1].title = line
            elif results and not results[-1].snippet:
                results[-1].snippet = line
            if idx >= max_results:
                break

        return results
