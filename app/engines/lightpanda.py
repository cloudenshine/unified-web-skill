"""lightpanda.py — Lightpanda CDP engine (WebSocket-based browser)."""
from __future__ import annotations

import json
import os
import time
from typing import Any

from .base import BaseEngine, Capability, FetchResult, InteractResult

try:
    import websockets
    import websockets.client

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class LightpandaEngine(BaseEngine):
    """Connects to a Lightpanda CDP server via WebSocket for fast, low-memory browsing."""

    def __init__(self) -> None:
        self._cdp_url = os.environ.get("LP_CDP_URL", "ws://127.0.0.1:9222")
        self._msg_id = 0
        super().__init__()

    @property
    def name(self) -> str:
        return "lightpanda"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.INTERACT}

    # -- helpers -----------------------------------------------------------

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def _send_cdp(
        self, ws: Any, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a CDP command and wait for the matching response."""
        msg_id = self._next_id()
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        await ws.send(json.dumps(payload))

        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise RuntimeError(f"CDP error: {data['error']}")
                return data.get("result", {})

    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        if not HAS_WEBSOCKETS:
            self._logger.warning("websockets library not installed")
            return False
        try:
            async with websockets.client.connect(self._cdp_url, open_timeout=5) as ws:
                result = await self._send_cdp(ws, "Browser.getVersion")
                self._logger.debug("Lightpanda version: %s", result)
                return True
        except Exception as exc:
            self._logger.debug("health_check failed: %s", exc)
            return False

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        if not HAS_WEBSOCKETS:
            return FetchResult(ok=False, url=url, engine=self.name, error="websockets not installed")

        t0 = time.monotonic()
        try:
            async with websockets.client.connect(
                self._cdp_url, open_timeout=timeout, close_timeout=5
            ) as ws:
                # Navigate
                await self._send_cdp(ws, "Page.navigate", {"url": url})
                # Wait for load
                await self._send_cdp(ws, "Page.enable")

                # Try LP.getMarkdown first (AI-optimized output)
                text = ""
                html = ""
                metadata: dict[str, Any] = {}
                try:
                    md_result = await self._send_cdp(ws, "LP.getMarkdown")
                    text = md_result.get("markdown", md_result.get("result", ""))
                    metadata["format"] = "markdown"
                except Exception:
                    # Fallback to Runtime.evaluate for innerHTML
                    try:
                        eval_result = await self._send_cdp(
                            ws, "Runtime.evaluate",
                            {"expression": "document.documentElement.outerHTML"},
                        )
                        html = eval_result.get("result", {}).get("value", "")
                    except Exception:
                        pass

                # Also try semantic tree
                try:
                    sem = await self._send_cdp(ws, "LP.getSemanticTree")
                    metadata["semantic_tree"] = sem
                except Exception:
                    pass

                dur = (time.monotonic() - t0) * 1000
                return FetchResult(
                    ok=bool(text or html),
                    url=url, engine=self.name,
                    html=html, text=text,
                    duration_ms=dur, metadata=metadata,
                )
        except Exception as exc:
            dur = (time.monotonic() - t0) * 1000
            self._logger.warning("fetch failed: %s", exc)
            return FetchResult(ok=False, url=url, engine=self.name, duration_ms=dur, error=str(exc))

    async def interact(
        self, url: str, actions: list[dict[str, Any]], *, timeout: int = 60, **opts: Any
    ) -> InteractResult:
        if not HAS_WEBSOCKETS:
            return InteractResult(ok=False, url=url, engine=self.name, error="websockets not installed")

        t0 = time.monotonic()
        try:
            async with websockets.client.connect(
                self._cdp_url, open_timeout=timeout, close_timeout=5
            ) as ws:
                # Navigate to page
                await self._send_cdp(ws, "Page.navigate", {"url": url})
                await self._send_cdp(ws, "Page.enable")

                last_result: dict[str, Any] = {}
                for action in actions:
                    act_type = action.get("type", "")
                    if act_type == "click":
                        selector = action.get("selector", "")
                        last_result = await self._send_cdp(
                            ws, "LP.clickNode", {"selector": selector}
                        )
                    elif act_type == "fill":
                        selector = action.get("selector", "")
                        value = action.get("value", "")
                        last_result = await self._send_cdp(
                            ws, "LP.fillNode", {"selector": selector, "value": value}
                        )
                    elif act_type == "evaluate":
                        expression = action.get("expression", "")
                        last_result = await self._send_cdp(
                            ws, "Runtime.evaluate", {"expression": expression}
                        )
                    elif act_type == "wait":
                        import asyncio
                        await asyncio.sleep(action.get("seconds", 1))
                    else:
                        self._logger.warning("unknown action type: %s", act_type)

                # Get final page content
                text = ""
                try:
                    md_result = await self._send_cdp(ws, "LP.getMarkdown")
                    text = md_result.get("markdown", md_result.get("result", ""))
                except Exception:
                    try:
                        eval_result = await self._send_cdp(
                            ws, "Runtime.evaluate",
                            {"expression": "document.body.innerText"},
                        )
                        text = eval_result.get("result", {}).get("value", "")
                    except Exception:
                        pass

                dur = (time.monotonic() - t0) * 1000
                return InteractResult(
                    ok=True, url=url, engine=self.name,
                    text=text, duration_ms=dur,
                    metadata={"last_action_result": last_result},
                )
        except Exception as exc:
            dur = (time.monotonic() - t0) * 1000
            self._logger.warning("interact failed: %s", exc)
            return InteractResult(ok=False, url=url, engine=self.name, duration_ms=dur, error=str(exc))
