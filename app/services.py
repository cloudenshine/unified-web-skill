"""services.py — UnifiedWebSkill 服务层"""
from __future__ import annotations

import logging
from typing import Any

from .extractor import extract_text
from .heuristics import auto_route
from .scrapling_engine import fetch_with_fallback

logger = logging.getLogger(__name__)


class UnifiedWebSkill:
    """
    统一 Web 技能服务层。
    - web_fetch: 自动路由 HTTP/动态/Stealth，返回结构化结果
    - web_interact: PinchTab 交互任务
    """

    async def web_fetch(
        self,
        url: str,
        task: str = "",
        mode: str = "auto",
        prefer_text: bool = True,
        max_chars: int = 4000,
    ) -> dict[str, Any]:
        """
        单 URL 抓取。
        mode: auto | http | dynamic | stealth
        返回: {"ok": bool, "engine": str, "route": str, "text": str, "html": str, ...}
        """
        if mode == "auto":
            mode = auto_route(url, task)
            if mode == "pinchtab":
                # pinchtab 归 web_interact，这里降级到 http
                mode = "http"

        result = await fetch_with_fallback(
            url=url,
            task_text=task,
            first=mode,
            timeout=30,
        )

        text = ""
        if prefer_text and result.html:
            text = extract_text(result.html, max_chars=max_chars)

        return {
            "ok": result.ok,
            "engine": result.engine,
            "route": result.route,
            "status": result.status,
            "url": result.url,
            "text": text,
            "html": result.html if not prefer_text else "",
            "duration_ms": result.duration_ms,
            "error": result.error,
        }

    async def web_interact(
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
        PinchTab 交互任务。
        若 PinchTab 未配置，则降级到 scrapling http 抓取。
        """
        try:
            from .pinchtab_client import get_client, ConfigError
            client = get_client()
            return await client.interact(
                url=url,
                task=task,
                instance_id=instance_id,
                tab_id=tab_id,
                actions=actions,
                return_snapshot=return_snapshot,
                return_text=return_text,
            )
        except Exception as exc:
            logger.warning("PinchTab unavailable (%s); falling back to scrapling", exc)
            if url:
                result = await fetch_with_fallback(url=url, task_text=task or "")
                text = extract_text(result.html, max_chars=4000) if result.html else ""
                return {
                    "ok": result.ok,
                    "engine": f"scrapling-fallback:{result.engine}",
                    "route": result.route,
                    "status": result.status,
                    "url": result.url,
                    "text": text,
                    "snapshot": None,
                    "error": f"pinchtab_unavailable:{exc}",
                }
            return {
                "ok": False,
                "engine": "none",
                "error": f"pinchtab_unavailable:{exc}",
            }
