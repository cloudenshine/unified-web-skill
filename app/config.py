"""Centralized configuration from environment variables."""
import os
import json
import logging

_logger = logging.getLogger(__name__)

# === MCP Server ===
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))

# === OpenCLI ===
OPENCLI_BIN = os.environ.get("OPENCLI_BIN", "opencli")
OPENCLI_TIMEOUT = int(os.environ.get("OPENCLI_TIMEOUT_SECONDS", "30"))
OPENCLI_ENABLED = os.environ.get("RESEARCH_OPENCLI_ENABLED", "true").lower() == "true"

# === Scrapling ===
SCRAPLING_TIMEOUT_HTTP = int(os.environ.get("SCRAPLING_TIMEOUT_HTTP", "10"))
SCRAPLING_TIMEOUT_DYNAMIC = int(os.environ.get("SCRAPLING_TIMEOUT_DYNAMIC", "30"))
SCRAPLING_TIMEOUT_STEALTH = int(os.environ.get("SCRAPLING_TIMEOUT_STEALTH", "60"))

# === Lightpanda ===
LP_CDP_URL = os.environ.get("LP_CDP_URL", "ws://127.0.0.1:9222")
LP_ENABLED = os.environ.get("LP_ENABLED", "true").lower() == "true"

# === PinchTab ===
PINCHTAB_BASE_URL = os.environ.get("PINCHTAB_BASE_URL", "")
PINCHTAB_MCP_ENDPOINT = os.environ.get("PINCHTAB_MCP_ENDPOINT", "/mcp")
PINCHTAB_TOKEN = os.environ.get("PINCHTAB_TOKEN", "")
PINCHTAB_TIMEOUT = int(os.environ.get("PINCHTAB_TIMEOUT", "60"))

# === bb-browser ===
BB_BROWSER_BIN = os.environ.get("BB_BROWSER_BIN", "bb-browser")
BB_BROWSER_TIMEOUT = int(os.environ.get("BB_BROWSER_TIMEOUT", "30"))
BB_BROWSER_ENABLED = os.environ.get("BB_BROWSER_ENABLED", "true").lower() == "true"

# === CLIBrowser ===
CLIBROWSER_BIN = os.environ.get("CLIBROWSER_BIN", "clibrowser")
CLIBROWSER_TIMEOUT = int(os.environ.get("CLIBROWSER_TIMEOUT", "30"))
CLIBROWSER_ENABLED = os.environ.get("CLIBROWSER_ENABLED", "true").lower() == "true"

# === Research Defaults ===
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "zh")
DEFAULT_MAX_SOURCES = int(os.environ.get("DEFAULT_MAX_SOURCES", "30"))
DEFAULT_MAX_PAGES = int(os.environ.get("DEFAULT_MAX_PAGES", "20"))
DEFAULT_QPS = float(os.environ.get("DEFAULT_QPS", "2.0"))
MAX_PROXY_RETRIES = int(os.environ.get("MAX_PROXY_RETRIES", "3"))

# === Rate Limiting ===
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_DEFAULT_QPS = float(os.environ.get("RATE_LIMIT_DEFAULT_QPS", "2.0"))
RATE_LIMIT_PER_DOMAIN: dict[str, float] = {}
_rl_env = os.environ.get("RATE_LIMIT_DOMAINS", "")
if _rl_env:
    for pair in _rl_env.split(","):
        if "=" in pair:
            domain, qps = pair.strip().split("=", 1)
            try:
                RATE_LIMIT_PER_DOMAIN[domain.strip()] = float(qps.strip())
            except ValueError:
                pass

# === Cache ===
FETCH_CACHE_ENABLED = os.environ.get("FETCH_CACHE_ENABLED", "true").lower() == "true"
FETCH_CACHE_TTL = int(os.environ.get("FETCH_CACHE_TTL", "3600"))
FETCH_CACHE_MAX_MB = int(os.environ.get("FETCH_CACHE_MAX_MB", "100"))

# === Engine Priority (default order) ===
ENGINE_PRIORITY = os.environ.get("ENGINE_PRIORITY", "bb-browser,opencli,scrapling,lightpanda,clibrowser").split(",")

# === Output ===
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "outputs")

# === Site Registry ===
SITE_REGISTRY_PATH = os.environ.get("SITE_REGISTRY_PATH", "")
