"""config.py — 环境变量统一配置"""
import json
import os

# Lightpanda CDP endpoint
LP_CDP_URL: str = os.environ.get("LP_CDP_URL", "ws://lightpanda:9222")

# PinchTab HTTP API
PINCHTAB_BASE_URL: str = os.environ.get("PINCHTAB_BASE_URL", "")
PINCHTAB_MCP_ENDPOINT: str = os.environ.get("PINCHTAB_MCP_ENDPOINT", "/mcp")
PINCHTAB_TOKEN: str = os.environ.get("PINCHTAB_TOKEN", "")

# OpenCLI 配置
OPENCLI_BIN: str = os.environ.get("OPENCLI_BIN", "opencli")
OPENCLI_TIMEOUT_SECONDS: int = int(os.environ.get("OPENCLI_TIMEOUT_SECONDS", "30"))
_OPENCLI_ALLOWLIST_RAW: str = os.environ.get(
    "OPENCLI_ALLOWLIST_JSON",
    '{"bilibili": "hot", "zhihu": "trending", "hackernews": "top", "reddit": "hot"}'
)
try:
    OPENCLI_ALLOWLIST: dict[str, str] = json.loads(_OPENCLI_ALLOWLIST_RAW)
except Exception:
    OPENCLI_ALLOWLIST = {}

# Research 流水线开关
RESEARCH_OPENCLI_ENABLED: bool = os.environ.get("RESEARCH_OPENCLI_ENABLED", "true").lower() == "true"
RESEARCH_OPENCLI_FALLBACK: bool = os.environ.get("RESEARCH_OPENCLI_FALLBACK", "true").lower() == "true"
RESEARCH_PREFERRED_TOOL_ORDER: list[str] = os.environ.get(
    "RESEARCH_PREFERRED_TOOL_ORDER", "opencli,scrapling"
).split(",")

# Scrapling 超时 & 重试
SCRAPLING_TIMEOUT: int = int(os.environ.get("SCRAPLING_TIMEOUT", "30"))
MAX_PROXY_RETRIES: int = int(os.environ.get("MAX_PROXY_RETRIES", "3"))

# MCP 服务器
MCP_HOST: str = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT: int = int(os.environ.get("MCP_PORT", "8000"))
