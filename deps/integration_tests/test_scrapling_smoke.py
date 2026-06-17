"""依赖冒烟测试 — Scrapling 基本功能验证。

每次依赖升级后，作为第一道防线运行。
用法:
    cd /path/to/unified-web-skill
    python -m pytest deps/integration_tests/test_scrapling_smoke.py -v
"""

import pytest


# 以下为示例性测试结构，需要项目 venv 环境
# 实际运行前请取消注释并根据当前 Scrapling API 适配

"""
from scrapling import Fetcher, DynamicFetcher


def test_fetcher_import():
    """验证 Fetcher 类可导入。"""
    assert Fetcher is not None


def test_fetcher_basic_get():
    """基本 HTTP GET 请求。"""
    resp = Fetcher.get("https://httpbin.org/get", timeout=10, stealthy_headers=True)
    assert resp is not None
    assert resp.status == 200
    assert resp.html_content is not None


def test_fetcher_block_detection():
    """blocked 页面检测不应误报正常页面。"""
    resp = Fetcher.get("https://example.com", timeout=10, stealthy_headers=True)
    assert resp.status < 400


def test_dynamic_fetcher():
    """DynamicFetcher 的基本用法。"""
    import asyncio
    async def _test():
        resp = await DynamicFetcher.async_fetch("https://httpbin.org/get", timeout=10000)
        assert resp is not None
        assert resp.status == 200
    asyncio.run(_test())


@pytest.mark.skip(reason="需要网络环境")
def test_dynamic_fetcher_js_render():
    """测试 JS 渲染页面获取。"""
    import asyncio
    async def _test():
        resp = await DynamicFetcher.async_fetch(
            "https://httpbin.org/get",
            timeout=15000,
        )
        text = resp.get_all_text(" ")
        assert text and len(text) > 0
    asyncio.run(_test())
"""


def test_scrapling_version_detected():
    """占位测试 — 验证测试框架可运行。"""
    import importlib.metadata
    try:
        ver = importlib.metadata.version("scrapling")
        print(f"  Scrapling version: {ver}")
        assert ver >= "0.4.0"
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("scrapling not installed in this environment")
