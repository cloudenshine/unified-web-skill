# unified-web-skill

**AI Agent 无限制网络访问平台** — 环形模块化架构，任意网站均可到达，结构化输出。

An MCP server that gives AI agents unrestricted web access through a layered ring architecture — from simple HTTP to stealth browser automation with Cloudflare bypass.

---

## Architecture: Ring Model

```
Ring 3  Research Pipeline  (query expand -> concurrent fetch -> deduplicate -> save)
  Ring 2  CLI Engines      (bb-browser / opencli, absolute paths, 100+ sites)
    Ring 1  Browser        (patchright stealth > playwright, cookies, screenshot)
      Ring 0  HTTP         (httpx + ddgs, always available, zero binary deps)
```

Each ring probes its own dependencies at startup and degrades gracefully if missing.
Ring 0 is always available — the server never fully fails.

| Ring | Dependencies | Handles |
|------|-------------|---------|
| **R0 HTTP** | httpx, ddgs | Any public URL, DuckDuckGo/Bing search, link extraction |
| **R1 Browser** | patchright / playwright | JS SPAs, Cloudflare sites, cookie sessions, screenshots |
| **R2 CLI** | bb-browser, opencli | Structured social/content platform data (100+ sites) |
| **R3 Pipeline** | R0 + R1 | Multi-source research, query expansion, quality filtering, storage |

---

## MCP Tools (v2)

| Tool | Ring | Description |
|------|------|-------------|
| `fetch` | R0+R1 | Fetch any URL — auto HTTP or browser |
| `search` | R0 | Web search via DuckDuckGo/Bing, no API key |
| `browse` | R1 | Real Chromium with stealth and cookie support |
| `interact` | R1 | Browser automation: click, fill, scroll, screenshot |
| `site` | R2 | Structured commands: bilibili/hot, zhihu/trending, etc. |
| `crawl` | R0 | BFS crawl from seed URL, follow links |
| `research` | R3 | Full pipeline: expand -> search -> fetch -> filter -> save |
| `status` | -- | Ring availability and binary path report |

---

## Quick Start

### Prerequisites

```bash
# Python 3.11+
pip install -r requirements.txt

# Install browser binaries (one-time)
playwright install chromium
patchright install chromium

# Optional: CLI engines for structured social site data
npm install -g bb-browser opencli
```

### Diagnostic check

```bash
cd /path/to/unified-web-skill
python check_v2.py
```

Expected:
```
Ring 0 (HTTP):     [OK] online
Ring 1 (Browser):  [OK] online
Ring 2 (CLI):      [OK] online
Ring 3 (Pipeline): [OK] online
```

### Start server

```bash
# stdio mode (for OpenClaw / Claude Code MCP)
python server_v2.py --stdio

# HTTP mode
python server_v2.py
# -> http://127.0.0.1:8001
```

---

## Integration

### OpenClaw

Add to `~/.openclaw/openclaw.json`:

```json
{
  "mcp": {
    "servers": {
      "unified-web-skill": {
        "command": "C:\\Program Files\\Python312\\python.exe",
        "args": ["E:\\path\\to\\unified-web-skill\\server_v2.py", "--stdio"],
        "cwd": "E:\\path\\to\\unified-web-skill",
        "env": {
          "BB_BROWSER_BIN": "D:\\Programs\\npm\\bb-browser.CMD",
          "OPENCLI_BIN": "D:\\Programs\\npm\\opencli.CMD",
          "OUTPUT_DIR": "E:\\path\\to\\unified-web-skill\\outputs"
        }
      }
    }
  }
}
```

> **Critical**: Use absolute paths for `command` and binary env vars.
> Bare names like `"bb-browser"` fail when Node.js inherits a different PATH than your shell.
> `core/probe.py` handles this automatically via `shutil.which()` + Windows npm fallbacks.

### Claude Code

```json
{
  "mcpServers": {
    "unified-web-skill": {
      "command": "python",
      "args": ["server_v2.py", "--stdio"],
      "cwd": "/path/to/unified-web-skill"
    }
  }
}
```

---

## Tool Reference

### `fetch` — Universal URL fetch

```python
fetch(
    url: str,
    mode: str = "auto",        # auto | http | browser
    timeout: int = 20,
    screenshot: bool = False,
    extra_headers: str = "",   # JSON string {"X-Header": "value"}
)
# Returns: {ok, url, title, text, html, engine, duration_ms, error}
```

`mode=auto` uses HTTP for most sites, switches to browser for known JS-heavy domains (bilibili, zhihu, twitter, notion, etc.).

---

### `search` — Web search (no API key)

```python
search(
    query: str,
    max_results: int = 10,  # max 30
    language: str = "zh",   # zh | en
)
# Returns: {ok, results: [{url, title, snippet, rank, source}], total, duration_ms}
```

Supports DuckDuckGo operators: `site:`, `filetype:`, `intitle:`, `"exact phrase"`.

---

### `browse` — Stealth browser fetch

```python
browse(
    url: str,
    timeout: int = 30,
    screenshot: bool = False,
    wait_for: str = "networkidle",  # networkidle | domcontentloaded | load
    js_eval: str = "",              # JS expression, result prepended to text
    cookies: str = "",              # JSON array string OR file path to JSON
    stealth: bool = True,           # patchright Cloudflare bypass (default on)
)
# Returns: {ok, url, title, text, html, screenshot_b64, engine, duration_ms}
```

Cookie format for login-required pages:
```json
[{"name": "session_id", "value": "abc123", "domain": ".example.com", "path": "/"}]
```

---

### `interact` — Browser automation

```python
interact(
    url: str,
    actions: str,           # JSON array of action objects
    timeout: int = 60,
    screenshot: bool = True,
    cookies: str = "",
    stealth: bool = True,
)
# Returns: {ok, url, title, text, screenshot_b64, engine, duration_ms}
```

Supported actions:
```json
[
  {"action": "click",    "selector": "#login-btn"},
  {"action": "fill",     "selector": "input[name=email]",    "value": "user@example.com"},
  {"action": "fill",     "selector": "input[name=password]", "value": "secret"},
  {"action": "press",    "selector": "input[name=password]", "value": "Enter"},
  {"action": "wait_for", "selector": ".dashboard"},
  {"action": "scroll",   "value": "800"},
  {"action": "wait",     "wait_ms": 1500},
  {"action": "navigate", "value": "https://example.com/data"},
  {"action": "evaluate", "value": "document.querySelector('.price').textContent"},
  {"action": "type",     "selector": "textarea", "value": "hello world"}
]
```

---

### `site` — Structured platform data

```python
site(
    name: str,      # bilibili | zhihu | hackernews | reddit | youtube | xiaohongshu | ...
    command: str,   # hot | trending | top | search | user-videos | ranking | ...
    args: str = ""  # comma-separated arguments
)
# Returns: {ok, site, command, data, engine, duration_ms}
```

Examples:
```
site("bilibili",   "hot")
site("zhihu",      "trending")
site("hackernews", "top")
site("bilibili",   "search", "AI agent 2025")
```

Engine priority: bb-browser first (richer adapters), opencli fallback.

---

### `crawl` — BFS web crawl

```python
crawl(
    url: str,
    max_pages: int = 10,      # max 50
    max_depth: int = 2,
    same_domain: bool = True,
    timeout: int = 15,
    save: bool = False,
    format: str = "json",     # json | md | ndjson
)
# Returns: {ok, pages: [{url, title, text, depth}], total_pages, duration_s, output_files}
```

---

### `research` — Full research pipeline

```python
research(
    query: str,
    language: str = "zh",
    max_sources: int = 15,
    max_pages: int = 10,
    max_queries: int = 4,      # sub-queries to generate
    max_concurrency: int = 5,
    timeout: int = 15,
    min_quality: float = 0.1,
    include_domains: str = "", # comma-separated allowlist
    exclude_domains: str = "", # comma-separated blocklist
    format: str = "json,md",   # output formats
)
# Returns: {ok, query, records, total, queries_used, duration_s, output_files, engines_used}
```

---

### `status` — Ring health report

```python
status()
# Returns: ring online/offline status, binary paths, capability details
```

---

## Recommended Tool Pairing

| Data need | Best tool |
|-----------|-----------|
| GitHub repos / code / issues | **GitHub MCP** (authoritative) |
| Library docs / API reference | **Context7 MCP** (up-to-date) |
| Wikipedia / deep encyclopedic | **DeepWiki MCP** |
| Any public webpage | `fetch` or `browse` |
| Real-time web search | `search` |
| Bilibili / Zhihu / XHS / HN | `site` |
| Cloudflare-protected sites | `browse` (stealth=True) |
| Login-required pages | `browse` or `interact` with `cookies` |
| Multi-source research | `research` |
| Multi-page site scraping | `crawl` |
| Browser forms / interaction | `interact` |

Use specialized MCPs (GitHub, Context7, DeepWiki) for their domains — they provide authoritative, structured data without scraping overhead.

---

## What Gets Bypassed

| Blocker | Status |
|---------|--------|
| Cloudflare JS challenge | Bypassed (patchright) |
| Bot-detection fingerprinting | Bypassed (patchright stealth) |
| Login-gated content | Supported (cookie injection) |
| SMS / CAPTCHA verification | Requires human |
| Paid subscription paywalls | Requires valid credentials |

---

## Project Structure

```
unified-web-skill/
|-- server_v2.py          Entry point: ring-based MCP server (8 tools)
|-- check_v2.py           Diagnostic: verify all rings before starting
|-- requirements.txt
|
|-- core/                 Ring architecture (v2)
|   |-- probe.py          Capability detection + binary path auto-discovery
|   |-- storage.py        Output: JSON / Markdown / NDJSON
|   `-- rings/
|       |-- r0_http.py    Ring 0: httpx + ddgs search + text extraction
|       |-- r1_browser.py Ring 1: patchright/playwright + cookie injection
|       |-- r2_cli.py     Ring 2: bb-browser/opencli (absolute paths)
|       `-- r3_pipeline.py Ring 3: query expansion + concurrent research
|
|-- app/                  Legacy v1 (backward compat)
|   |-- mcp_server.py     v1 entry: 7 tools, 6-engine architecture
|   |-- engines/          Scrapling, bb-browser, opencli, lightpanda adapters
|   |-- pipeline/         v1 research pipeline
|   `-- discovery/        Intent classifier + 67-site registry
|
`-- outputs/              Research outputs (gitignored)
```

---

## Changelog

### v2.0.0 (2026-04-22)

- **New**: Ring-based modular architecture (R0-R3), Ring 0 always guaranteed
- **New**: `server_v2.py` — 8 MCP tools, clean entry point
- **New**: patchright integration — Cloudflare / bot-detection bypass (`stealth=True`)
- **New**: Cookie injection support — login-required pages via `cookies` parameter
- **New**: `probe.py` — automatic binary path resolution (no PATH dependency)
- **New**: `ddgs` package (renamed from `duckduckgo-search`)
- **New**: `trafilatura` + `beautifulsoup4` for richer article extraction
- **Fix**: OpenClaw PATH issue — bb-browser/opencli now resolved to absolute paths
- **Fix**: Lightpanda default-enabled with Docker hostname causing startup errors
- **Keep**: Full `app/` v1 backward compatibility

### v1.x (prior)

- 6-engine: Scrapling, bb-browser, OpenCLI, Lightpanda, PinchTab, CLIBrowser
- 7 MCP tools via FastMCP
- 67-site registry, 9-type intent classifier, circuit-breaker health monitor

---

## License

MIT
