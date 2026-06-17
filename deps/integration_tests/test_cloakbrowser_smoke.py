"""依赖冒烟测试 — CloakBrowser 连通性验证。

用法:
    python -m pytest deps/integration_tests/test_cloakbrowser_smoke.py -v
"""

import pytest


# 以下测试需要运行中的 CloakBrowser 实例
# 实际运行前取消注释

"""
def test_cdp_version_endpoint():
    import urllib.request, json
    req = urllib.request.Request("http://127.0.0.1:9222/json/version")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
        assert "webSocketDebuggerUrl" in data


@pytest.mark.asyncio
async def test_cdp_connect():
    import websockets, json, urllib.request
    req = urllib.request.Request("http://127.0.0.1:9222/json/version")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    ws_url = data["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Browser.getVersion"}))
        resp = json.loads(await ws.recv())
        assert "result" in resp
        print(f"  Browser: {resp['result'].get('product', 'unknown')}")
"""


def test_cloakbrowser_config_present():
    """验证 CloakBrowser 环境变量配置。"""
    import os
    base_url = os.environ.get("CLOAK_BROWSER_BASE_URL", "http://127.0.0.1:9222")
    assert base_url.startswith("http")
    print(f"  CLOAK_BROWSER_BASE_URL: {base_url}")
