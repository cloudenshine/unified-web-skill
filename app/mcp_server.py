"""mcp_server.py — FastMCP 服务（4 个工具注册）"""
from __future__ import annotations

import logging
from typing import Any

from . import config

logger = logging.getLogger(__name__)


def create_app():
    """创建并返回 FastMCP app 实例"""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        from mcp import FastMCP  # type: ignore

    mcp = FastMCP("unified-web-skill")

    # ── Tool 1: research_and_collect ─────────────────────────────────────────
    @mcp.tool()
    async def research_and_collect(
        query: str,
        language: str = "zh",
        max_sources: int = 20,
        max_pages: int = 20,
        max_depth: int = 2,
        max_queries: int = 5,
        trusted_mode: bool = True,
        min_credibility: float = 0.55,
        min_text_length: int = 200,
        output_format: str = "json",
        output_path: str = "outputs/research",
        timeout_seconds: int = 60,
        task_id: str | None = None,
        opencli_enabled: bool = True,
        opencli_preferred_sites: list[str] | None = None,
        opencli_fallback: bool = True,
        preferred_tool_order: list[str] | None = None,
        domain_qps: float = 1.0,
        max_concurrency: int = 4,
        time_window_days: int = 0,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """从关键词出发完成完整网络研究流水线：查询扩展→搜索发现→可信度评分→多引擎抓取→内容提取→结构化落盘。支持 OpenCLI 主路由+Scrapling 降级。"""
        from .research_models import ResearchTask
        from .research_pipeline import ResearchPipeline

        task = ResearchTask(
            query=query,
            language=language,
            max_sources=max_sources,
            max_pages=max_pages,
            max_depth=max_depth,
            max_queries=max_queries,
            trusted_mode=trusted_mode,
            min_credibility=min_credibility,
            min_text_length=min_text_length,
            output_format=output_format,
            output_path=output_path,
            timeout_seconds=timeout_seconds,
            task_id=task_id,
            opencli_enabled=opencli_enabled,
            opencli_preferred_sites=opencli_preferred_sites or [],
            opencli_fallback=opencli_fallback,
            preferred_tool_order=preferred_tool_order or ["opencli", "scrapling"],
            domain_qps=domain_qps,
            max_concurrency=max_concurrency,
            time_window_days=time_window_days,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
        )
        pipeline = ResearchPipeline()
        result = await pipeline.run(task)
        return result.model_dump()

    # ── Tool 2: web_fetch ────────────────────────────────────────────────────
    @mcp.tool()
    async def web_fetch(
        url: str,
        task: str = "",
        mode: str = "auto",
        prefer_text: bool = True,
        max_chars: int = 4000,
    ) -> dict[str, Any]:
        """单 URL 抓取，自动路由 HTTP→Dynamic→Stealth 三级引擎"""
        from .services import UnifiedWebSkill
        skill = UnifiedWebSkill()
        return await skill.web_fetch(url=url, task=task, mode=mode,
                                      prefer_text=prefer_text, max_chars=max_chars)

    # ── Tool 3: web_cli ──────────────────────────────────────────────────────
    @mcp.tool()
    async def web_cli(
        site: str,
        command: str,
        args: list[str] | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """直接调用 OpenCLI 站点命令（bilibili/zhihu/hackernews/reddit 等）"""
        from .opencli_client import run_opencli
        return await run_opencli(site=site, command=command,
                                  args=args, timeout_seconds=timeout_seconds)

    # ── Tool 4: web_interact ─────────────────────────────────────────────────
    @mcp.tool()
    async def web_interact(
        url: str | None = None,
        task: str | None = None,
        instance_id: str | None = None,
        tab_id: str | None = None,
        actions: list[dict] | None = None,
        return_snapshot: bool = True,
        return_text: bool = True,
    ) -> dict[str, Any]:
        """PinchTab 浏览器交互：登录、点击、填表、翻页、截图、文本提取"""
        from .services import UnifiedWebSkill
        skill = UnifiedWebSkill()
        return await skill.web_interact(
            url=url, task=task,
            instance_id=instance_id, tab_id=tab_id,
            actions=actions,
            return_snapshot=return_snapshot,
            return_text=return_text,
        )

    return mcp


def main():
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    mcp = create_app()

    # Build Starlette/ASGI app from FastMCP
    try:
        asgi_app = mcp.get_asgi_app()
    except AttributeError:
        asgi_app = mcp.streamable_http_app()  # type: ignore

    # Wrap with FastAPI to add /health
    fast_app = FastAPI(title="unified-web-skill")

    @fast_app.get("/health")
    async def health():
        return JSONResponse({"status": "ok", "service": "unified-web-skill"})

    fast_app.mount("/", asgi_app)

    uvicorn.run(
        fast_app,
        host=config.MCP_HOST,
        port=config.MCP_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
