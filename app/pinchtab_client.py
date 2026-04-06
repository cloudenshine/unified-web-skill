"""pinchtab_client.py — PinchTab HTTP API 异步客户端"""
from __future__ import annotations

import logging
from typing import Any

from . import config

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """PinchTab 未配置时抛出"""


class PinchTabClient:
    """
    封装 PinchTab HTTP API（httpx AsyncClient）。
    若 PINCHTAB_BASE_URL 未配置则在调用时抛出 ConfigError。
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = (base_url or config.PINCHTAB_BASE_URL or "").rstrip("/")
        self._token = token or config.PINCHTAB_TOKEN
        self._timeout = timeout
        self._endpoint = config.PINCHTAB_MCP_ENDPOINT

    def _check_config(self) -> None:
        if not self._base_url:
            raise ConfigError(
                "PINCHTAB_BASE_URL is not configured. "
                "Set the environment variable to enable PinchTab."
            )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def interact(
        self,
        url: str | None = None,
        task: str | None = None,
        instance_id: str | None = None,
        tab_id: str | None = None,
        actions: list[dict] | None = None,
        return_snapshot: bool = True,
        return_text: bool = True,
    ) -> dict[str, Any]:
        """
        发送交互指令到 PinchTab MCP 端点。
        返回 {"ok": bool, "engine": "pinchtab", ...}
        """
        self._check_config()
        try:
            import httpx
        except ImportError as e:
            raise ImportError("httpx is required for PinchTabClient") from e

        payload: dict[str, Any] = {
            "method": "tools/call",
            "params": {
                "name": "browser_interact",
                "arguments": {
                    "url": url,
                    "task": task,
                    "instance_id": instance_id,
                    "tab_id": tab_id,
                    "actions": actions or [],
                    "return_snapshot": return_snapshot,
                    "return_text": return_text,
                },
            },
        }

        endpoint = f"{self._base_url}{self._endpoint}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(endpoint, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        result = data.get("result", {})
        return {
            "ok": True,
            "engine": "pinchtab",
            "instance_id": result.get("instance_id"),
            "tab_id": result.get("tab_id"),
            "snapshot": result.get("snapshot"),
            "text": result.get("text"),
            "raw": result,
        }

    async def close(self) -> None:
        pass  # httpx client is managed per-request


# 模块级单例（懒加载）
_client: PinchTabClient | None = None


def get_client() -> PinchTabClient:
    global _client
    if _client is None:
        _client = PinchTabClient()
    return _client
