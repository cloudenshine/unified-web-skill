# 🌐 Unified Web Skill v3.0

**AI Agent 统一网络研究平台** — 集成 6 大 Web 引擎，实现"没有 AI Agent 访问不了的数据源"。

An AI-agent-native web research platform that unifies 6 web engines behind a single MCP interface, enabling any AI agent to access virtually any data source on the web.

---

## 🚀 核心能力 / Key Features

- **6 引擎统一调度** — OpenCLI · Scrapling · Lightpanda · PinchTab · bb-browser · CLIBrowser
- **5 层智能降级** — SiteAdapter → HTTP → CDP → Dynamic → Stealth → CLIBrowser
- **7 个 MCP 工具** — `research_and_collect` / `web_fetch` / `web_cli` / `web_interact` / `web_search` / `web_crawl` / `engine_status`
- **67 内置站点注册表** — 自动匹配最优引擎，覆盖中英文主流站点
- **意图感知查询扩展** — 9 种查询意图 (Informational / News / Academic / Code / Finance / Social / Transactional / Navigational / Local)，130+ 关键词模式
- **熔断 + 限流 + 重试** — 每引擎独立健康监控，circuit-breaker 自动隔离故障引擎

---

## 📦 安装 / Installation

### 前置要求 / Prerequisites

| 工具 Tool | 安装 Install | 用途 Purpose | 必要性 |
|-----------|-------------|--------------|--------|
| **Python 3.11+** | [python.org](https://python.org) | 运行环境 Runtime | ✅ 必须 |
| **OpenCLI** | `npm i -g opencli` | 100+ 站点适配器 | ⭐ 强烈建议 |
| **bb-browser** | `npm i -g bb-browser` | 126+ 站点适配器，最全能引擎 | ⭐ 强烈建议 |
| **CLIBrowser** | [github.com/anthropics/clibrowser](https://github.com/anthropics/clibrowser) | Rust 隐身浏览器，终极降级引擎 | 推荐 |
| **Lightpanda** | [lightpanda.io](https://lightpanda.io) | 超轻 CDP 浏览器 (Zig) | 可选 |
| **PinchTab** | [pinchtab.com](https://pinchtab.com) | 远程浏览器 MCP | 可选 |

> 💡 OpenCLI 和 bb-browser 为核心引擎，提供绝大部分站点的结构化数据访问。其余引擎按需安装。

### Python 依赖 / Python Dependencies

```
mcp>=1.0.0              # MCP server framework
scrapling>=0.4.4        # 3-tier HTTP fetcher
pydantic>=2.0.0         # Data validation
httpx>=0.27.0           # Async HTTP (PinchTab)
duckduckgo-search>=6.0  # DuckDuckGo search fallback
fastapi>=0.111.0        # Health endpoint
uvicorn>=0.30.0         # ASGI server
websockets>=12.0        # Lightpanda CDP
```

### 快速开始 / Quick Start

```bash
# Clone & install
git clone https://github.com/anthropics/unified-web-skill.git
cd unified-web-skill
pip install -r requirements.txt

# Configure (optional)
cp .env.sample .env
# Edit .env with your engine paths and preferences

# Run MCP server (stdio mode for AI agents)
python -m app.mcp_server --stdio

# Run MCP server (HTTP/SSE mode with /health endpoint)
python -m app.mcp_server
```

### Docker

```bash
cp .env.sample .env
# Edit .env with your configuration
docker compose -f docker-compose.final.yml up
```

---

## 🏗 架构 / Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         MCP Server                            │
│   7 Tools: research / fetch / cli / interact / search /       │
│            crawl / status                                     │
│   Transport: stdio (AI agents) | HTTP/SSE (web clients)       │
├──────────────────────────────────────────────────────────────┤
│                     Research Pipeline v3                       │
│   Intent Classify → Query Expand → Multi-Source Discover →    │
│   Concurrent Fetch → Content Extract → Quality Gate →         │
│   Deduplicate → Structured Storage                            │
├──────────────────────────────────────────────────────────────┤
│                      Engine Manager                           │
│   SmartRouter ←── SiteRegistry (67 built-in sites)           │
│   HealthMonitor (circuit breaker per engine)                  │
│   DomainRateLimiter (token bucket per domain)                 │
├────────┬────────┬────────┬────────┬────────┬─────────────────┤
│OpenCLI │Scrplng │ Light  │ Pinch  │  bb-   │ CLIBrowser      │
│ 100+   │ 3-tier │  CDP   │  MCP   │browser │   Rust          │
│ sites  │ fetch  │  Zig   │ remote │ 126+   │  stealth        │
│ struct │HTTP/PW │9x fast │ API    │ sites  │  fallback       │
│ data   │/Stlth  │16x mem │browser │ full   │  zero-dep       │
└────────┴────────┴────────┴────────┴────────┴─────────────────┘
```

> 详细架构文档 → [docs/architecture.md](docs/architecture.md)

---

## 🔧 MCP Tools

7 个工具覆盖从单页抓取到完整研究管线的全部场景：

### 1. `research_and_collect`

完整研究管线：查询扩展 → 多源发现 → 并发抓取 → 质量验证 → 去重 → 结构化输出。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | *必填* | 研究主题或问题 |
| `language` | string | `"zh"` | 目标语言 (zh / en) |
| `max_sources` | int | `30` | 最大发现来源数 (1–500) |
| `max_pages` | int | `20` | 最大抓取页面数 (1–200) |
| `max_queries` | int | `8` | 最大扩展查询数 (1–30) |
| `trusted_mode` | bool | `false` | 仅抓取高可信度来源 |
| `output_format` | string | `"json"` | 输出格式: json / ndjson / md |
| `min_text_length` | int | `100` | 最小文本长度 |
| `min_credibility` | float | `0.3` | 最小可信度 (0.0–1.0) |
| `time_window_days` | int | `0` | 时间窗口 (天数, 0=不限) |
| `include_domains` | string | `""` | 域名白名单 (逗号分隔) |
| `exclude_domains` | string | `""` | 域名黑名单 (逗号分隔) |
| `preferred_engines` | string | `""` | 偏好引擎 (逗号分隔) |
| `search_engines` | string | `""` | 搜索引擎 (逗号分隔) |
| `enable_stealth` | bool | `false` | 启用隐身/反检测抓取 |
| `max_concurrency` | int | `5` | 最大并发数 (1–20) |

### 2. `web_fetch`

单 URL 抓取，自动路由到最优引擎。支持 `mode`: auto / http / dynamic / stealth。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | *必填* | 目标 URL |
| `task` | string | `""` | 抓取目的描述 |
| `mode` | string | `"auto"` | 路由模式: auto / http / dynamic / stealth |
| `prefer_text` | bool | `true` | 返回提取文本 (false=原始 HTML) |
| `timeout` | int | `30` | 超时秒数 |
| `engine` | string | `""` | 强制指定引擎 (空=自动路由) |

### 3. `web_cli`

直接调用 OpenCLI / bb-browser 站点适配器命令，获取结构化数据。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `site` | string | *必填* | 站点适配器名 (如 "bilibili", "zhihu") |
| `command` | string | *必填* | 命令 (如 "hot", "search", "trending") |
| `args` | string | `""` | 命令参数 (逗号分隔) |

### 4. `web_interact`

浏览器交互：点击、填表、滚动、截图、提取文本。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | `""` | 目标 URL |
| `task` | string | `""` | 交互目标描述 |
| `actions` | string | `""` | JSON 动作列表 |
| `instance_id` | string | `""` | 复用浏览器会话 ID |
| `return_snapshot` | bool | `true` | 返回 base64 截图 |
| `return_text` | bool | `true` | 返回页面文本 |
| `timeout` | int | `60` | 超时秒数 |
| `engine` | string | `""` | 强制指定引擎 |

### 5. `web_search` *(NEW in v3.0)*

多引擎搜索聚合，结果自动去重排序。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | *必填* | 搜索关键词 |
| `max_results` | int | `10` | 最大结果数 |
| `language` | string | `"zh"` | 目标语言 |
| `engines` | string | `""` | 指定引擎 (逗号分隔, 空=全部) |
| `intent` | string | `""` | 搜索意图提示 |

### 6. `web_crawl` *(NEW in v3.0)*

从种子 URL 深度爬取，BFS 跟随链接。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | *必填* | 种子 URL |
| `max_pages` | int | `10` | 最大爬取页面数 |
| `max_depth` | int | `2` | 最大链接跟随深度 |
| `same_domain_only` | bool | `true` | 仅跟随同域链接 |
| `extract_links` | bool | `true` | 提取并跟随链接 |
| `timeout` | int | `30` | 单页超时秒数 |

### 7. `engine_status` *(NEW in v3.0)*

查看所有引擎健康状态和能力。无参数调用。

> 完整 API 参考 → [docs/api.md](docs/api.md)

---

## ⚙️ 配置 / Configuration

通过 `.env` 文件或环境变量配置：

### MCP Server

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MCP_HOST` | `0.0.0.0` | 监听地址 |
| `MCP_PORT` | `8000` | 监听端口 |

### Engine Enable/Disable

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESEARCH_OPENCLI_ENABLED` | `true` | 启用 OpenCLI |
| `BB_BROWSER_ENABLED` | `true` | 启用 bb-browser |
| `LP_ENABLED` | `true` | 启用 Lightpanda |
| `CLIBROWSER_ENABLED` | `true` | 启用 CLIBrowser |

### Engine Binaries & Timeouts

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLI_BIN` | `opencli` | OpenCLI 二进制路径 |
| `OPENCLI_TIMEOUT_SECONDS` | `30` | OpenCLI 超时 |
| `BB_BROWSER_BIN` | `bb-browser` | bb-browser 二进制路径 |
| `BB_BROWSER_TIMEOUT` | `30` | bb-browser 超时 |
| `CLIBROWSER_BIN` | `clibrowser` | CLIBrowser 二进制路径 |
| `CLIBROWSER_TIMEOUT` | `30` | CLIBrowser 超时 |

### Scrapling Timeouts

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SCRAPLING_TIMEOUT_HTTP` | `10` | HTTP 层超时 |
| `SCRAPLING_TIMEOUT_DYNAMIC` | `30` | Dynamic (Playwright) 层超时 |
| `SCRAPLING_TIMEOUT_STEALTH` | `60` | Stealth 层超时 |

### Lightpanda

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LP_CDP_URL` | `ws://127.0.0.1:9222` | CDP WebSocket 地址 |

### PinchTab

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PINCHTAB_BASE_URL` | `""` | PinchTab 服务地址 (空=禁用) |
| `PINCHTAB_MCP_ENDPOINT` | `/mcp` | MCP 端点路径 |
| `PINCHTAB_TOKEN` | `""` | Bearer 认证 Token |
| `PINCHTAB_TIMEOUT` | `60` | 请求超时 |

### Research Defaults

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_LANGUAGE` | `zh` | 默认语言 |
| `DEFAULT_MAX_SOURCES` | `30` | 默认最大来源数 |
| `DEFAULT_MAX_PAGES` | `20` | 默认最大页面数 |
| `DEFAULT_QPS` | `2.0` | 默认每域名 QPS |
| `MAX_PROXY_RETRIES` | `3` | 代理重试次数 |
| `ENGINE_PRIORITY` | `bb-browser,opencli,...` | 引擎优先级 |
| `OUTPUT_DIR` | `outputs` | 输出目录 |
| `SITE_REGISTRY_PATH` | `""` | 自定义站点注册表路径 |

---

## 📁 项目结构 / Project Structure

```
unified-web-skill/
├── app/
│   ├── __init__.py              # v3.0.0 版本声明
│   ├── mcp_server.py            # 7 MCP tools + HTTP/stdio 入口
│   ├── config.py                # 环境变量配置中心
│   ├── constants.py             # 域名 / 标记 / 关键词常量
│   ├── exceptions.py            # 异常层级 (8 种异常类型)
│   ├── models.py                # Pydantic v2 数据模型
│   ├── engines/                 # 6 引擎抽象层
│   │   ├── base.py              # Engine Protocol + BaseEngine ABC
│   │   ├── manager.py           # EngineManager + SmartRouter + SiteRegistry
│   │   ├── health.py            # EngineHealthMonitor (circuit breaker)
│   │   ├── opencli.py           # OpenCLI 引擎 (FETCH + SEARCH + STRUCTURED)
│   │   ├── scrapling_engine.py  # Scrapling 3-tier (HTTP → Dynamic → Stealth)
│   │   ├── lightpanda.py        # Lightpanda CDP 引擎 (FETCH + INTERACT)
│   │   ├── pinchtab.py          # PinchTab MCP 引擎 (FETCH + INTERACT)
│   │   ├── bb_browser.py        # bb-browser 引擎 (全能力: FETCH/SEARCH/INTERACT/STRUCTURED)
│   │   └── clibrowser.py        # CLIBrowser 引擎 (FETCH + SEARCH)
│   ├── discovery/               # 智能发现层
│   │   ├── site_registry.py     # 67 内置站点注册表 (singleton)
│   │   ├── intent_classifier.py # 9 类意图分类器 (130+ regex 模式)
│   │   ├── query_planner.py     # 意图感知查询扩展
│   │   └── multi_source.py      # 多源并发 URL 发现
│   ├── pipeline/                # 研究管线
│   │   ├── research.py          # ResearchPipeline v3 (8 阶段)
│   │   ├── extractor.py         # 内容提取 (scrapling Adaptor + regex 降级)
│   │   ├── quality.py           # 质量门控 + 去重 (content_hash)
│   │   └── storage.py           # 结果持久化 (JSON / NDJSON / Markdown)
│   └── utils/                   # 工具层
│       ├── rate_limiter.py      # 域名级令牌桶限流
│       ├── retry.py             # 重试策略
│       ├── heuristics.py        # 域名/内容启发式规则
│       └── scoring.py           # 来源可信度评分
├── tests/                       # 测试套件
├── data/                        # 站点注册表数据 (JSON)
├── outputs/                     # 研究输出目录
├── docs/                        # 文档
│   ├── architecture.md          # 架构设计
│   ├── api.md                   # API 参考
│   └── engines.md               # 引擎文档
├── .env.sample                  # 环境变量模板
├── requirements.txt             # Python 依赖
├── Dockerfile                   # Docker 镜像
├── docker-compose.final.yml     # Docker Compose
├── Makefile                     # 常用命令
└── README.md                    # 本文件
```

---

## 🧪 测试 / Testing

```bash
# 单元测试 Unit tests
python -m pytest tests/unit/ -v

# 集成测试 Integration tests (需要引擎已安装)
python -m pytest tests/integration/ -v

# 端到端测试 End-to-end tests
python -m pytest tests/e2e/ -v

# 全部测试 All tests
python -m pytest tests/ -v

# 带覆盖率 With coverage
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 📊 引擎能力矩阵 / Engine Capability Matrix

| 引擎 Engine | FETCH | SEARCH | INTERACT | STRUCTURED | 特色 Highlights |
|-------------|:-----:|:------:|:--------:|:----------:|-----------------|
| **OpenCLI** | ✅ | ✅ | ❌ | ✅ | 100+ 站点适配器，结构化 JSON 输出 |
| **Scrapling** | ✅ | ❌ | ❌ | ❌ | 3 层 HTTP 降级 (HTTP → Playwright → Stealth) |
| **Lightpanda** | ✅ | ❌ | ✅ | ❌ | 9x 速度, 16x 省内存, Markdown 输出 |
| **PinchTab** | ✅ | ❌ | ✅ | ❌ | 远程浏览器 MCP, 云端无头浏览器 |
| **bb-browser** | ✅ | ✅ | ✅ | ✅ | 126+ 适配器, 全能力引擎, 最丰富站点覆盖 |
| **CLIBrowser** | ✅ | ✅ | ❌ | ❌ | Rust 编写, 隐身模式, 零依赖终极降级 |

> 详细引擎文档 → [docs/engines.md](docs/engines.md)

---

## 📚 文档 / Documentation

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 架构设计、引擎协议、路由算法、管线阶段 |
| [docs/api.md](docs/api.md) | 完整 API 参考：7 个 MCP 工具的参数、返回值、示例 |
| [docs/engines.md](docs/engines.md) | 6 引擎详解：安装、配置、能力、限制 |

---

## 健康检查 / Health Check

HTTP 模式下访问 `http://localhost:8000/health` 查看服务状态：

```json
{
  "status": "ok",
  "service": "unified-web-skill",
  "version": "3.0.0",
  "engines": ["bb-browser", "opencli", "scrapling", "lightpanda", "clibrowser"]
}
```

---

## License

MIT
