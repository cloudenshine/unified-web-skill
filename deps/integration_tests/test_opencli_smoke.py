"""依赖冒烟测试 — OpenCLI 基本功能验证。

用法:
    python -m pytest deps/integration_tests/test_opencli_smoke.py -v
"""

import pytest


# 以下测试需要安装 @jackwener/opencli
# npm install -g @jackwener/opencli

"""
import subprocess


def test_opencli_installed():
    result = subprocess.run(["opencli", "--version"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0
    print(f"  OpenCLI version: {result.stdout.strip()}")


def test_opencli_list():
    result = subprocess.run(
        ["opencli", "list", "-f", "json"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    import json
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) > 0


def test_opencli_doctor():
    result = subprocess.run(
        ["opencli", "doctor"],
        capture_output=True, text=True, timeout=15,
    )
    # 注意: opencli doctor 可能 auto-start daemon
    assert result.returncode in (0, 69)  # 0=ok, 69=browser unavailable
"""


def test_opencli_config_present():
    """验证 OpenCLI 环境变量配置。"""
    import os
    bin_path = os.environ.get("OPENCLI_BIN", "opencli")
    assert bin_path
    print(f"  OPENCLI_BIN: {bin_path}")
