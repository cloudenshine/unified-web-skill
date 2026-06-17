from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request
from typing import Any

from ..credential.inject import cookie_header_for_platform, platform_for_url
from .base import BaseEngine, Capability, FetchResult, InteractResult

try:
    import websockets
except ImportError:  # pragma: no cover - optional at runtime
    websockets = None  # type: ignore[assignment]


def _request_json(url: str, *, timeout: int, method: str = "GET") -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        if not raw:
            return None
        return json.loads(raw)


def _rewrite_local_url_for_container(url: str, profile: str) -> str:
    if not profile:
        return url
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return url
    host = "host.docker.internal"
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    else:
        netloc = host
    rewritten = parsed._replace(netloc=netloc)
    return urllib.parse.urlunparse(rewritten)


class _CDPSession:
    def __init__(self, websocket: Any):
        self._ws = websocket
        self._next_id = 0

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        payload = {"id": self._next_id, "method": method, "params": params or {}}
        await self._ws.send(json.dumps(payload))

        while True:
            raw = await self._ws.recv()
            message = json.loads(raw)
            if message.get("id") != self._next_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method} failed: {message['error']}")
            return message.get("result", {})



async def _inject_cookies_via_cdp(cdp: _CDPSession, url: str) -> None:
    """Inject stored credentials as cookies into the CDP session before navigation."""
    plat = platform_for_url(url)
    if plat is None:
        return
    cookie_str = cookie_header_for_platform(plat)
    if not cookie_str:
        return
    # Parse and inject each cookie via Network.setCookie
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, _, value = pair.partition("=")
        name = name.strip()
        value = value.strip()
        if name and value:
            try:
                await cdp.call("Network.setCookie", {
                    "name": name,
                    "value": value,
                    "domain": plat + ".com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                })
            except Exception:
                pass


class CloakBrowserEngine(BaseEngine):
    """CDP-backed interaction provider using CloakBrowser and its manager."""

    def __init__(self) -> None:
        self._base_url = (
            os.environ.get("CLOAK_BROWSER_BASE_URL", "http://127.0.0.1:9222") or ""
        ).rstrip("/")
        self._manager_base_url = (
            os.environ.get("CLOAK_MANAGER_BASE_URL", "http://127.0.0.1:8080") or ""
        ).rstrip("/")
        self._timeout = int(os.environ.get("CLOAK_MANAGER_TIMEOUT", "15"))
        super().__init__()

    @property
    def name(self) -> str:
        return "cloakbrowser"

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.INTERACT, Capability.FETCH}

    async def health_check(self) -> bool:
        if websockets is None:
            return False
        try:
            payload = await asyncio.to_thread(
                _request_json,
                f"{self._base_url}/json/version",
                timeout=self._timeout,
            )
            return bool(payload and payload.get("webSocketDebuggerUrl"))
        except Exception:
            return False

    async def fetch(self, url: str, *, timeout: int = 30, **opts: Any) -> FetchResult:
        result = await self._run_interaction(
            url,
            [],
            timeout=timeout,
            profile=str(opts.get("profile", "")),
            intent=str(opts.get("intent", "js_render") or "js_render"),
            require_login=bool(opts.get("require_login", False)),
        )
        return FetchResult(
            ok=result.ok,
            url=url,
            text=result.text,
            engine=self.name,
            error=result.error,
            duration_ms=result.duration_ms,
            metadata=result.metadata,
        )

    async def interact(
        self,
        url: str,
        actions: list[dict[str, Any]],
        *,
        timeout: int = 60,
        **opts: Any,
    ) -> InteractResult:
        return await self._run_interaction(
            url,
            actions,
            timeout=timeout,
            profile=str(opts.get("profile", "")),
            intent=str(opts.get("intent", "")),
            require_login=bool(opts.get("require_login", False)),
        )

    async def _run_interaction(
        self,
        url: str,
        actions: list[dict[str, Any]],
        *,
        timeout: int,
        profile: str,
        intent: str,
        require_login: bool,
    ) -> InteractResult:
        if websockets is None:
            return InteractResult(
                ok=False,
                url=url,
                engine=self.name,
                error="websockets not installed",
            )

        if not intent:
            return InteractResult(
                ok=False,
                url=url,
                engine=self.name,
                error="intent is required for CloakBrowser interactions",
            )

        if (intent == "login_required" or require_login) and not profile:
            return InteractResult(
                ok=False,
                url=url,
                engine=self.name,
                error="profile is required for login interactions",
            )

        started = asyncio.get_running_loop().time()
        try:
            effective_url = _rewrite_local_url_for_container(url, profile)
            ws_url = await asyncio.to_thread(self._resolve_page_websocket, profile)
            async with websockets.connect(
                ws_url,
                max_size=None,
                ping_interval=None,
                ping_timeout=None,
            ) as ws:
                cdp = _CDPSession(ws)
                await cdp.call("Page.enable")
                await cdp.call("Runtime.enable")
                # Inject stored cookies for the target domain
                await _inject_cookies_via_cdp(cdp, effective_url or url)

                if effective_url:
                    await cdp.call("Page.navigate", {"url": effective_url})
                    await asyncio.sleep(2.0)

                snapshot = ""
                for action in actions:
                    await self._apply_action(cdp, action, url)
                    if action.get("type") == "wait":
                        continue
                    await asyncio.sleep(0.25)
                    if action.get("type") == "screenshot":
                        shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
                        snapshot = shot.get("data", "")

                if intent == "screenshot" and not snapshot:
                    shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
                    snapshot = shot.get("data", "")

                eval_result = await cdp.call(
                    "Runtime.evaluate",
                    {
                        "expression": "document.body ? document.body.innerText : ''",
                        "returnByValue": True,
                    },
                )
                text = (
                    eval_result.get("result", {}).get("value", "")
                    if isinstance(eval_result, dict)
                    else ""
                )
                duration_ms = (asyncio.get_running_loop().time() - started) * 1000.0
                return InteractResult(
                    ok=True,
                    url=effective_url,
                    engine=self.name,
                    text=text,
                    snapshot=snapshot,
                    instance_id=profile,
                    duration_ms=duration_ms,
                    metadata={"intent": intent, "actions": actions},
                )
        except Exception as exc:
            duration_ms = (asyncio.get_running_loop().time() - started) * 1000.0
            return InteractResult(
                ok=False,
                url=effective_url if "effective_url" in locals() else url,
                engine=self.name,
                instance_id=profile,
                error=str(exc),
                duration_ms=duration_ms,
                metadata={"intent": intent, "actions": actions},
            )

    def _resolve_page_websocket(self, profile: str) -> str:
        if profile:
            profile_data = self._ensure_profile_running(profile)
            profile_id = profile_data["id"]
            list_url = (
                f"{self._manager_base_url}/api/profiles/"
                f"{urllib.parse.quote(profile_id)}/cdp/json/list"
            )
            pages = _request_json(list_url, timeout=self._timeout) or []
        else:
            pages = _request_json(
                f"{self._base_url}/json/list",
                timeout=self._timeout,
            ) or []

        page = next((item for item in pages if item.get("type") == "page"), None)
        if not page or not page.get("webSocketDebuggerUrl"):
            raise RuntimeError("No page-level CDP websocket available")
        return str(page["webSocketDebuggerUrl"])

    def _ensure_profile_running(self, profile_name: str) -> dict[str, Any]:
        profiles = _request_json(
            f"{self._manager_base_url}/api/profiles",
            timeout=self._timeout,
        ) or []
        profile = next((item for item in profiles if item.get("name") == profile_name), None)
        if not profile:
            raise RuntimeError(f"profile not found: {profile_name}")

        profile_id = str(profile["id"])
        if profile.get("status") != "running":
            _request_json(
                f"{self._manager_base_url}/api/profiles/{urllib.parse.quote(profile_id)}/launch",
                timeout=self._timeout,
                method="POST",
            )
            profile = _request_json(
                f"{self._manager_base_url}/api/profiles/{urllib.parse.quote(profile_id)}",
                timeout=self._timeout,
            )

        return profile

    async def _apply_action(
        self,
        cdp: _CDPSession,
        action: dict[str, Any],
        fallback_url: str,
    ) -> None:
        action_type = str(action.get("type", "")).lower()
        selector = str(action.get("selector", ""))
        value = action.get("value", "")

        if action_type == "navigate":
            target = str(value or action.get("url") or fallback_url)
            if target:
                await cdp.call("Page.navigate", {"url": target})
                await asyncio.sleep(2.0)
            return

        if action_type == "click":
            if not selector:
                raise RuntimeError("click action requires selector")
            await cdp.call(
                "Runtime.evaluate",
                {
                    "expression": (
                        f"(() => {{ const el = document.querySelector({json.dumps(selector)});"
                        " if (!el) throw new Error('selector not found');"
                        " el.click(); return true; }})()"
                    ),
                    "returnByValue": True,
                },
            )
            return

        if action_type in {"fill", "type"}:
            if not selector:
                raise RuntimeError("fill action requires selector")
            await cdp.call(
                "Runtime.evaluate",
                {
                    "expression": (
                        f"(() => {{ const el = document.querySelector({json.dumps(selector)});"
                        " if (!el) throw new Error('selector not found');"
                        f" el.focus(); el.value = {json.dumps(str(value))};"
                        " el.dispatchEvent(new Event('input', { bubbles: true }));"
                        " el.dispatchEvent(new Event('change', { bubbles: true }));"
                        " return true; }})()"
                    ),
                    "returnByValue": True,
                },
            )
            return

        if action_type == "scroll":
            direction = str(action.get("direction", "down")).lower()
            delta = -800 if direction == "up" else 800
            await cdp.call(
                "Runtime.evaluate",
                {
                    "expression": f"window.scrollBy(0, {delta}); true;",
                    "returnByValue": True,
                },
            )
            return

        if action_type == "wait":
            seconds = float(action.get("seconds", 1))
            await asyncio.sleep(max(seconds, 0))
            return

        if action_type == "screenshot":
            return

        raise RuntimeError(f"unsupported action type: {action_type}")
