"""opencli.py — OpenCLI engine: wraps the ``opencli`` binary."""
from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.parse import urlparse

from .base import BaseEngine, Capability, FetchResult, SearchResult

# opencli exit‐code semantics
_EXIT_MEANINGS: dict[int, str] = {
    0: "success",
    66: "no_data",
    69: "unavailable",
    75: "tempfail",
    77: "auth_required",
    78: "not_found",
}


def _domain_to_site(url: str) -> str | None:
    """Resolve a URL to an opencli site identifier via SiteRegistry."""
    from ..discovery.site_registry import SiteRegistry
    registry = SiteRegistry.get_instance()
    cap = registry.lookup_by_url(url)
    if cap and "opencli" in cap.engines:
        return cap.site_id
    return None


class OpenCLIEngine(BaseEngine):
    """Wraps the ``opencli`` CLI binary for structured site data."""

    def __init__(self) -> None:
        self._bin = os.environ.get("OPENCLI_BIN", "opencli")
        self._timeout = int(os.environ.get("OPENCLI_TIMEOUT_SECONDS", "12"))
        super().__init__()

    @property
    def name(self) -> str:
        return "opencli"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.SEARCH, Capability.STRUCTURED}

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        rc, out, _ = await self._run_subprocess([self._bin, "--version"], timeout=10)
        if rc == 0 and out.strip():
            self._logger.debug("opencli version: %s", out.strip())
            return True
        return False

    async def fetch(self, url: str, *, timeout: int = 0, **opts: Any) -> FetchResult:
        # Cap at self._timeout — callers must not extend it beyond the configured limit
        timeout = min(timeout or self._timeout, self._timeout)
        t0 = time.monotonic()
        site = _domain_to_site(url)
        if site is None:
            return FetchResult(
                ok=False, url=url, engine=self.name,
                duration_ms=(time.monotonic() - t0) * 1000,
                error=f"unsupported domain for opencli: {url}",
            )

        command = opts.get("command", "")
        cmd = [self._bin, site]
        if command:
            cmd.append(command)

        rc, stdout, stderr = await self._run_subprocess(cmd, timeout=timeout)
        dur = (time.monotonic() - t0) * 1000

        if rc != 0:
            meaning = _EXIT_MEANINGS.get(rc, f"exit_{rc}")
            self._logger.warning("opencli %s exited %d (%s): %s", site, rc, meaning, stderr[:200])
            return FetchResult(
                ok=False, url=url, engine=self.name, text=stdout,
                status=rc, duration_ms=dur,
                error=f"{meaning}: {stderr[:300]}",
            )

        # Try to parse JSON output
        metadata: dict[str, Any] = {}
        text = stdout
        try:
            data = json.loads(stdout)
            metadata = data if isinstance(data, dict) else {"items": data}
            text = json.dumps(data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass

        return FetchResult(
            ok=True, url=url, engine=self.name, text=text,
            status=0, duration_ms=dur, metadata=metadata,
        )

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "zh", **opts: Any
    ) -> list[SearchResult]:
        """OpenCLI has no generic search; delegate to site-specific commands when possible."""
        site = opts.get("site", "")
        command = opts.get("command", "search")
        if not site:
            self._logger.debug("opencli search requires an explicit 'site' opt")
            return []

        cmd = [self._bin, site, command, query]
        rc, stdout, _ = await self._run_subprocess(cmd, timeout=self._timeout)
        if rc != 0:
            return []

        results: list[SearchResult] = []
        try:
            data = json.loads(stdout)
            items = data if isinstance(data, list) else data.get("items", [])
            for idx, item in enumerate(items[:max_results]):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", item.get("link", "")),
                    snippet=item.get("snippet", item.get("description", "")),
                    rank=idx + 1,
                    source=f"opencli:{site}",
                    metadata=item,
                ))
        except (json.JSONDecodeError, ValueError):
            pass
        return results
