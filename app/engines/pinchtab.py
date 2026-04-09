"""pinchtab.py — PinchTab MCP engine (HTTP API / JSON-RPC 2.0)."""
from __future__ import annotations

import os
import time
from typing import Any

from .base import BaseEngine, Capability, FetchResult, InteractResult

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class PinchTabEngine(BaseEngine):
    """Wraps the PinchTab MCP endpoint for browser interaction via HTTP API."""

    def __init__(self) -> None:
        self._base_url = (os.environ.get("PINCHTAB_BASE_URL", "") or "").rstrip("/")
        self._endpoint = os.environ.get("PINCHTAB_MCP_ENDPOINT", "/mcp")
        self._token = os.environ.get("PINCHTAB_TOKEN", "")
        super().__init__()

    @property
    def name(self) -> str:
        return "pinchtab"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.INTERACT}

    # -- helpers -----------------------------------------------------------

    def _url(self) -> str:
        return f"{self._base_url}{self._endpoint}"

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _rpc_payload(
        self, tool_name: str, arguments: dict[str, Any], rpc_id: int = 1
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        if not HAS_HTTPX:
            self._logger.warning("httpx library not installed")
            return False
        if not self._base_url:
            self._logger.warning("PINCHTAB_BASE_URL not configured")
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._base_url, headers=self._headers())
                return resp.status_code < 500
        except Exception as exc:
            self._logger.debug("health_check failed: %s", exc)
            return False

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        if not HAS_HTTPX:
            return FetchResult(ok=False, url=url, engine=self.name, error="httpx not installed")
        if not self._base_url:
            return FetchResult(ok=False, url=url, engine=self.name, error="PINCHTAB_BASE_URL not configured")

        t0 = time.monotonic()
        instance_id = opts.get("instance_id")
        try:
            payload = self._rpc_payload("browser_interact", {
                "url": url,
                "task": opts.get("task", ""),
                "instance_id": instance_id,
                "actions": [{"type": "navigate", "url": url}],
                "return_text": True,
                "return_snapshot": False,
            })
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self._url(), json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()

            result_data = data.get("result", {})
            text = result_data.get("text", "")
            dur = (time.monotonic() - t0) * 1000
            return FetchResult(
                ok=bool(text),
                url=url, engine=self.name,
                text=text, duration_ms=dur,
                metadata={
                    "instance_id": result_data.get("instance_id"),
                    "tab_id": result_data.get("tab_id"),
                },
            )
        except Exception as exc:
            dur = (time.monotonic() - t0) * 1000
            self._logger.warning("fetch failed: %s", exc)
            return FetchResult(ok=False, url=url, engine=self.name, duration_ms=dur, error=str(exc))

    async def interact(
        self, url: str, actions: list[dict[str, Any]], *, timeout: int = 60, **opts: Any
    ) -> InteractResult:
        if not HAS_HTTPX:
            return InteractResult(ok=False, url=url, engine=self.name, error="httpx not installed")
        if not self._base_url:
            return InteractResult(ok=False, url=url, engine=self.name, error="PINCHTAB_BASE_URL not configured")

        t0 = time.monotonic()
        instance_id = opts.get("instance_id")
        tab_id = opts.get("tab_id")

        # Actions are already in PinchTab format
        pt_actions = list(actions)

        try:
            payload = self._rpc_payload("browser_interact", {
                "url": url,
                "task": opts.get("task", ""),
                "instance_id": instance_id,
                "tab_id": tab_id,
                "actions": pt_actions,
                "return_text": True,
                "return_snapshot": opts.get("return_snapshot", True),
            })
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self._url(), json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()

            result_data = data.get("result", {})
            dur = (time.monotonic() - t0) * 1000
            return InteractResult(
                ok=True,
                url=url, engine=self.name,
                text=result_data.get("text", ""),
                snapshot=result_data.get("snapshot", ""),
                duration_ms=dur,
                metadata={
                    "instance_id": result_data.get("instance_id"),
                    "tab_id": result_data.get("tab_id"),
                    "raw": result_data,
                },
            )
        except Exception as exc:
            dur = (time.monotonic() - t0) * 1000
            self._logger.warning("interact failed: %s", exc)
            return InteractResult(ok=False, url=url, engine=self.name, duration_ms=dur, error=str(exc))
