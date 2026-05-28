# unified-web-skill

**Local-first Web Access MCP Router for AI agents** — global resource discovery, retrieval, browser interaction, and research bundling through pluggable providers.

一个面向 AI Agent 的本地优先 MCP 路由层：统一搜索、抓取、浏览器交互、站点适配器和研究流水线，并通过可选 provider 做能力扩展。

---

## Architecture

The project now has one runtime architecture: the v3 engine-manager MCP router in `app/`.

```
AI Agent / MCP Client
  -> app.mcp_server
    -> EngineManager
      -> default providers: bb-browser, opencli, scrapling
      -> opt-in providers: lightpanda, pinchtab, clibrowser
    -> research pipeline: intent -> discovery -> fetch -> extract -> quality -> storage
```

Each provider declares its capabilities, reports health/version state, and participates in health-aware fallback. The default install works with the local baseline; browser/session and hosted providers are optional extensions.

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `research_and_collect` | Full pipeline: classify -> discover -> fetch -> filter -> save |
| `web_fetch` | Fetch one URL through provider routing and fallback |
| `web_cli` | Structured site commands through bb-browser/opencli |
| `web_interact` | Browser automation: click, fill, scroll, screenshot |
| `web_search` | Multi-provider search and deduplication |
| `web_crawl` | BFS crawl from a seed URL |
| `engine_status` | Provider health and capability report |

---

## Quick Start

### Prerequisites

```bash
# Python 3.12 recommended (3.11+ supported)
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install browser binaries (one-time)
playwright install chromium
patchright install chromium

# Optional: CLI engines for structured social site data
npm install -g bb-browser opencli

# Verification
python -m ruff check app tests
python -m pytest -q
```

### Diagnostic check

```bash
cd /path/to/unified-web-skill
python check.py
```

Expected:
```
Architecture: v3 engine-manager MCP router
Registered engines:
  scrapling: fetch, search
...
Critical dependency checks passed.
```

### Source matrix regression

周期性回归验证使用固定 profile，避免每次手工拼接长参数。promoted 批次使用
`--fail-on-unverified`，一旦出现 weak/failed 即返回非零退出码；boundary/special
/rate-limited watch 只产出证据，不自动提升 ProductHunt、Amazon、arXiv API、Open Food Facts 等
特殊源等级。

```bash
# promoted HTTP/RSS/API + structured adapter + browser-first regression
python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified
python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified
python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified

# boundary/special/rate-limited evidence watch，不影响默认通过线
python verify_source_matrix.py --regression-profile special-watch
python verify_source_matrix.py --regression-profile rate-limited-watch
```

在提供 `make` 的 POSIX 环境里，也可以继续使用 `make source-matrix-regression`
和 `make source-matrix-watch` 作为快捷入口。

### Start server

```bash
# stdio mode (for OpenClaw / Claude Code MCP)
python -m app.mcp_server --stdio

# HTTP mode
python -m app.mcp_server
# -> http://127.0.0.1:8000

```

---

## Integration

### Step 1 — Find your paths

Before editing any config, run these commands to get the correct values for your machine:

```bash
# Python executable (use this as "command")
where python          # Windows
which python3         # macOS / Linux

# Project directory (use this as "cwd")
cd /path/to/unified-web-skill && pwd

# bb-browser binary (if installed)
where bb-browser      # Windows
which bb-browser      # macOS / Linux

# opencli binary (if installed)
where opencli         # Windows
which opencli         # macOS / Linux
```

> **Why absolute paths?**
> OpenClaw and most GUI launchers spawn the MCP server as a subprocess with a minimal PATH
> that often differs from your shell's PATH. Bare names like `"bb-browser"` work in the
> terminal but silently fail when launched from a GUI. `python check.py` reports the
> providers that the v3 router can actually initialize; explicit paths are the reliable fallback.

---

### OpenClaw (`~/.openclaw/openclaw.json`)

```json
{
  "mcp": {
    "servers": {
      "unified-web-skill": {
        "command": "<absolute path to python or python3>",
        "args": ["-m", "app.mcp_server", "--stdio"],
        "cwd": "<absolute path to the unified-web-skill directory>",
        "env": {
          "OUTPUT_DIR": "<absolute path to unified-web-skill/outputs>"
        }
      }
    }
  }
}
```

If bb-browser / opencli are **not** on the system PATH of the process that launches OpenClaw,
add their paths explicitly:

```json
"env": {
  "BB_BROWSER_BIN": "<absolute path to bb-browser or bb-browser.CMD>",
  "OPENCLI_BIN":    "<absolute path to opencli or opencli.CMD>",
  "OUTPUT_DIR":     "<absolute path to unified-web-skill/outputs>"
}
```

**Platform examples:**

<details>
<summary>Windows</summary>

```json
{
  "mcp": {
    "servers": {
      "unified-web-skill": {
        "command": "C:\\Python312\\python.exe",
        "args": ["-m", "app.mcp_server", "--stdio"],
        "cwd": "C:\\Projects\\unified-web-skill",
        "env": {
          "BB_BROWSER_BIN": "C:\\Users\\YourName\\AppData\\Roaming\\npm\\bb-browser.cmd",
          "OPENCLI_BIN":    "C:\\Users\\YourName\\AppData\\Roaming\\npm\\opencli.cmd",
          "OUTPUT_DIR":     "C:\\Projects\\unified-web-skill\\outputs"
        }
      }
    }
  }
}
```

</details>

<details>
<summary>macOS / Linux</summary>

```json
{
  "mcp": {
    "servers": {
      "unified-web-skill": {
        "command": "/usr/local/bin/python3",
        "args": ["-m", "app.mcp_server", "--stdio"],
        "cwd": "/home/yourname/projects/unified-web-skill",
        "env": {
          "OUTPUT_DIR": "/home/yourname/projects/unified-web-skill/outputs"
        }
      }
    }
  }
}
```

On macOS/Linux, `shutil.which()` usually finds bb-browser/opencli automatically if they
are in `/usr/local/bin` or `~/.npm-global/bin`. Only add `BB_BROWSER_BIN` / `OPENCLI_BIN`
if `python check.py` reports CLI provider as offline.

</details>

---

### Claude Code (`.mcp.json` or project settings)

```json
{
  "mcpServers": {
    "unified-web-skill": {
      "command": "python3",
      "args": ["-m", "app.mcp_server", "--stdio"],
      "cwd": "/path/to/unified-web-skill"
    }
  }
}
```

Claude Code typically inherits the shell PATH, so bare `python3` usually works.
Use the absolute Python path if you get "command not found" errors.

---

### Verify after configuration

```bash
python check.py
```

If CLI providers show offline, set `BB_BROWSER_BIN`
and `OPENCLI_BIN` to the absolute paths found with `where` / `which`.

Optional browser providers are disabled by default for a clean local baseline.
Enable them only after their backing service or binary is installed:

```bash
LP_ENABLED=true
CLIBROWSER_ENABLED=true
PINCHTAB_BASE_URL=http://127.0.0.1:PORT
```

---

## Tool Reference

See [docs/api.md](docs/api.md) for the full v3 MCP API reference.

The runtime tools are:

- `research_and_collect`
- `web_fetch`
- `web_cli`
- `web_interact`
- `web_search`
- `web_crawl`
- `engine_status`

---

## 推荐工具搭配

同等结果质量下，优先选择更轻、更稳定、依赖更少的 provider。API/RSS/静态页是
全球覆盖主干；`bb-browser` 是结构化 adapter、动态浏览器和交互会话的强能力补位层。

| 数据需求 | 首选路径 |
|-----------|-----------|
| GitHub repos / code / issues | **GitHub MCP**（权威结构化数据） |
| Library docs / API reference | **Context7 MCP**（最新官方文档） |
| Wikipedia / deep encyclopedic | **DeepWiki MCP** |
| 官方 API / RSS / JSON endpoint | `fetch` via `scrapling` |
| 静态或半静态公开网页 | `fetch` via `scrapling` |
| 已有结构化站点 adapter | 优先 `opencli`，必要时 `bb-browser site` |
| 实时搜索 | `search` |
| Bilibili / Reddit / YouTube / HN 等 adapter 站点 | `site`，并单独验证 adapter 健康 |
| JS 渲染公开页面 | 浏览器 provider，仅在 HTTP 不足时启用 |
| 需要登录/cookie 的页面 | `browse` 或 `interact`，显式传入 session 假设 |
| 多源研究 | `research` |
| 多页面站点抓取 | `crawl` |
| 表单、点击、滚动、截图 | `interact` |

GitHub、Context7、DeepWiki 等专用 MCP 在各自领域优先于 scraping，因为它们通常能提供更权威、更稳定的结构化数据。

---

## Access Boundaries

| Blocker | Status |
|---------|--------|
| Cloudflare JS challenge | Best-effort via browser providers; success depends on site policy and provider capability |
| Bot-detection fingerprinting | Best-effort via stealth/browser providers; not guaranteed |
| Login-gated content | Supported when valid cookies, user session, or credentials are provided |
| SMS / CAPTCHA verification | Requires human |
| Paid subscription paywalls | Requires valid credentials |

---

## Project Structure

```
unified-web-skill/
|-- check.py              Diagnostic: verify v3 providers and live smoke checks
|-- verify_source_matrix.py  Source matrix live verification and regression profiles
|-- requirements.txt
|
|-- app/                  Single v3 MCP router implementation
|   |-- mcp_server.py     Runtime entry: 7 MCP tools, 6-engine architecture
|   |-- engines/          Scrapling, bb-browser, opencli, lightpanda, pinchtab, clibrowser
|   |-- pipeline/         Research pipeline
|   `-- discovery/        Intent classifier + source registry
|
|-- docs/                 API, architecture, engine docs, implementation plans
|-- tests/                Unit, integration, and e2e tests
`-- outputs/              Research outputs (gitignored)
```

---

## Changelog

### v3.0.0 (2026-05-13)

- **Single runtime**: v3 `app.mcp_server` is the only supported MCP server.
- **Removed**: historical ring runtime and duplicate entry points.
- **Updated**: diagnostics now run through the v3 EngineManager.
- **Clarified**: access boundaries are provider-dependent and best-effort.

---

## License

MIT
