# Engines — Unified Web Skill v3.0

6 引擎详细文档：安装、配置、能力、限制和使用示例。

---

## 引擎能力总览 / Capability Overview

| 引擎 | FETCH | SEARCH | INTERACT | STRUCTURED | 健康检查方式 |
|------|:-----:|:------:|:--------:|:----------:|-------------|
| **OpenCLI** | ✅ | ✅ | ❌ | ✅ | `opencli --version` |
| **Scrapling** | ✅ | ❌ | ❌ | ❌ | fetch httpbin.org |
| **Lightpanda** | ✅ | ❌ | ✅ | ❌ | CDP Browser.getVersion |
| **PinchTab** | ✅ | ❌ | ✅ | ❌ | HTTP GET base_url |
| **bb-browser** | ✅ | ✅ | ✅ | ✅ | `bb-browser status` |
| **CLIBrowser** | ✅ | ✅ | ❌ | ❌ | `clibrowser --version` |

---

## 1. OpenCLI

### 简介

OpenCLI 是命令行网站适配器框架，提供 100+ 站点的结构化数据访问。通过子进程调用 `opencli` 二进制文件，返回 JSON 格式的站点数据。

### 安装

```bash
npm install -g opencli

# 验证安装
opencli --version
```

### 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `OPENCLI_BIN` | `opencli` | 二进制路径 |
| `OPENCLI_TIMEOUT_SECONDS` | `30` | 超时秒数 |
| `RESEARCH_OPENCLI_ENABLED` | `true` | 启用/禁用 |

### 能力

- **FETCH**: 通过域名映射 (bilibili.com → bilibili) 将 URL 路由到对应的站点适配器
- **SEARCH**: 站点级搜索 (需指定 site 参数)，如 `opencli zhihu search "关键词"`
- **STRUCTURED**: 返回 JSON 格式数据，自动解析

### 支持的域名映射

| 域名 | 适配器名 |
|------|---------|
| bilibili.com | bilibili |
| zhihu.com | zhihu |
| news.ycombinator.com | hackernews |
| reddit.com | reddit |
| twitter.com / x.com | twitter |
| github.com | github |
| douban.com | douban |
| weibo.com | weibo |

### 退出码语义

| 退出码 | 含义 | 处理 |
|--------|------|------|
| 0 | 成功 | 解析 JSON 输出 |
| 66 | 无数据 | 返回 ok=false |
| 69 | 不可用 | 返回 ok=false |
| 75 | 临时故障 | 返回 ok=false |
| 77 | 需要认证 | 抛出 AuthRequiredError |
| 78 | 未找到 | 返回 ok=false |

### 限制

- 不支持通用 URL 抓取 (仅支持已映射域名)
- 不支持 INTERACT 能力
- 搜索需要显式指定 site 参数
- 依赖 Node.js 运行时

### 使用示例

```python
# 通过 web_cli 工具
{"site": "bilibili", "command": "hot"}              # B站热门
{"site": "zhihu", "command": "search", "args": "AI"} # 知乎搜索
{"site": "hackernews", "command": "hot"}             # HN 热帖
```

---

## 2. Scrapling

### 简介

Scrapling 是 Python HTTP 抓取库，提供 3 层自动降级：HTTP (最快) → Dynamic (Playwright 渲染) → Stealth (反检测)。作为 Python 依赖安装，无需额外二进制文件。

### 安装

```bash
pip install scrapling>=0.4.4

# Playwright 浏览器 (Dynamic / Stealth 层需要)
playwright install chromium
```

### 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `SCRAPLING_TIMEOUT_HTTP` | `10` | HTTP 层超时 (秒) |
| `SCRAPLING_TIMEOUT_DYNAMIC` | `30` | Dynamic 层超时 (秒) |
| `SCRAPLING_TIMEOUT_STEALTH` | `60` | Stealth 层超时 (秒) |

### 能力

- **FETCH**: 唯一能力，但通过 3 层降级实现高覆盖率

### 3 层抓取架构

```
┌──────────────┐     失败      ┌──────────────┐     失败      ┌──────────────┐
│  HTTP Tier   │ ──────────→  │ Dynamic Tier │ ──────────→  │ Stealth Tier │
│  Fetcher()   │              │AsyncFetcher()│              │StealthyFetch │
│  最快 ~10s   │              │ Playwright   │              │  反检测 ~60s │
│              │              │ auto_match   │              │  指纹伪装    │
│  stealthy_   │              │  ~30s        │              │              │
│  headers=True│              │              │              │              │
└──────────────┘              └──────────────┘              └──────────────┘
```

### 中文域名特殊处理

对中文域名 (bilibili, zhihu, baidu, weibo, douban 等)，默认优先使用 Dynamic 层：

```
中文域名: dynamic → http → stealth
其他域名: http → dynamic → stealth
```

### 反爬检测

自动检测以下反爬标记（返回 ok=false 并降级）：

- HTTP 状态码: 401, 403, 407, 429, 500, 502, 503, 504
- 内容标记: captcha, access denied, cloudflare, just a moment, not a robot, unusual traffic, bot detection 等

### 限制

- 不支持 SEARCH、INTERACT、STRUCTURED
- Dynamic/Stealth 层需要 Playwright 和 Chromium
- Stealth 层较慢 (60s 超时)
- 纯 HTTP 层对 JS-heavy 站点效果差

### 内容提取

Scrapling 的 `Adaptor` 类也用于内容提取阶段 (`ContentExtractor`)：

```python
from scrapling import Adaptor
page = Adaptor(html, auto_match=False)
# 尝试 CSS 选择器: article, main, .content, #content, .post-body, .article-body
elements = page.css("article")
text = elements[0].text
```

---

## 3. Lightpanda

### 简介

Lightpanda 是用 Zig 编写的超轻量 CDP 兼容浏览器，专为 AI Agent 设计。通过 WebSocket 连接到 Lightpanda CDP 服务器，支持页面抓取和交互。

官方宣称: **9x 速度**, **16x 省内存** (相比传统无头浏览器)。

### 安装

从 [lightpanda.io](https://lightpanda.io) 下载安装 Lightpanda 浏览器。

启动 CDP 服务：
```bash
lightpanda --host 127.0.0.1 --port 9222
```

Python 依赖：
```bash
pip install websockets>=12.0
```

### 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LP_CDP_URL` | `ws://127.0.0.1:9222` | CDP WebSocket 地址 |
| `LP_ENABLED` | `true` | 启用/禁用 |

### 能力

- **FETCH**: 通过 CDP 导航页面，支持 LP.getMarkdown (Markdown 输出) 和 LP.getSemanticTree (语义树)
- **INTERACT**: 支持 click (LP.clickNode)、fill (LP.fillNode)、evaluate (Runtime.evaluate)、wait

### CDP 命令

| CDP 命令 | 用途 |
|---------|------|
| `Page.navigate` | 导航到 URL |
| `Page.enable` | 启用页面事件 |
| `LP.getMarkdown` | 获取 Markdown 格式内容 (AI 优化输出) |
| `LP.getSemanticTree` | 获取语义树 |
| `LP.clickNode` | 点击节点 |
| `LP.fillNode` | 填写输入框 |
| `Runtime.evaluate` | 执行 JavaScript |
| `Browser.getVersion` | 获取浏览器版本 (健康检查) |

### 特色

- **LP.getMarkdown**: AI-native 的 Markdown 输出格式，无需额外 HTML→Text 转换
- **LP.getSemanticTree**: 页面结构化语义表示，存入 FetchResult.metadata

### 限制

- 不支持 SEARCH、STRUCTURED
- 需要独立运行 Lightpanda 进程
- WebSocket 连接可能不稳定
- 某些复杂 JS 站点可能不完全兼容
- 需要安装 `websockets` Python 包

---

## 4. PinchTab

### 简介

PinchTab 是远程浏览器 MCP 服务，通过 JSON-RPC 2.0 HTTP API 提供浏览器交互能力。适合需要云端无头浏览器的场景。

### 安装

PinchTab 是 SaaS 服务，无需本地安装。注册获取 API Token：[pinchtab.com](https://pinchtab.com)

Python 依赖：
```bash
pip install httpx>=0.27.0
```

### 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PINCHTAB_BASE_URL` | `""` | 服务地址 (**空=禁用引擎**) |
| `PINCHTAB_MCP_ENDPOINT` | `/mcp` | MCP 端点路径 |
| `PINCHTAB_TOKEN` | `""` | Bearer Token 认证 |
| `PINCHTAB_TIMEOUT` | `60` | 请求超时 (秒) |

### 能力

- **FETCH**: 通过 browser_interact 工具导航到 URL 并提取文本
- **INTERACT**: 完整浏览器交互：navigate, click, fill, submit, scroll, screenshot

### API 协议

使用 JSON-RPC 2.0 over HTTP POST：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "browser_interact",
    "arguments": {
      "url": "https://example.com",
      "task": "Extract page content",
      "actions": [{"type": "navigate", "url": "https://example.com"}],
      "return_text": true,
      "return_snapshot": true
    }
  }
}
```

### 会话管理

PinchTab 返回 `instance_id` 和 `tab_id`，可用于后续请求复用浏览器会话：

```json
{
  "instance_id": "abc123",
  "tab_id": "tab-001"
}
```

### 限制

- 不支持 SEARCH、STRUCTURED
- 需要网络连接到 PinchTab 服务
- 依赖第三方 SaaS 可用性
- 需要 API Token
- 需要安装 `httpx` Python 包
- `PINCHTAB_BASE_URL` 为空时引擎自动禁用

---

## 5. bb-browser

### 简介

bb-browser 是最全能的引擎，支持全部 4 种能力 (FETCH + SEARCH + INTERACT + STRUCTURED)，提供 126+ 站点适配器。通过子进程调用 `bb-browser` CLI 二进制文件。

### 安装

```bash
npm install -g bb-browser

# 验证安装
bb-browser status
# 或
bb-browser daemon status
```

### 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `BB_BROWSER_BIN` | `bb-browser` | 二进制路径 |
| `BB_BROWSER_TIMEOUT` | `30` | 超时秒数 |
| `BB_BROWSER_ENABLED` | `true` | 启用/禁用 |

### 能力

#### FETCH

两种模式：
1. **站点适配器**: 域名匹配后调用 `bb-browser site <adapter> --json`
2. **通用 URL**: 调用 `bb-browser open <url> --json`，然后 `bb-browser get text --json`

```
已知域名 → bb-browser site bilibili --json
未知域名 → bb-browser open https://example.com --json
           bb-browser get text --json
```

#### SEARCH

支持 5 个通用搜索引擎和 13 个站点搜索：

**通用搜索引擎：**

| 引擎 | 适配器 | 语言偏好 |
|------|--------|---------|
| Google | `google/search` | 英文默认 |
| Baidu | `baidu/search` | 中文默认 |
| Bing | `bing/search` | — |
| DuckDuckGo | `duckduckgo/search` | — |
| 搜狗微信 | `sogou/weixin` | 中文 |

**站点搜索：**

| 站点 | 适配器 |
|------|--------|
| Twitter | `twitter/search` |
| Reddit | `reddit/search` |
| Bilibili | `bilibili/search` |
| 小红书 | `xiaohongshu/search` |
| YouTube | `youtube/search` |
| 知乎 | `zhihu/search` |
| GitHub | `github/issues` |
| arXiv | `arxiv/search` |
| Hacker News | `hackernews/top` |
| 微博 | `weibo/search` |
| 豆瓣 | `douban/search` |
| V2EX | `v2ex/hot` |
| Stack Overflow | `stackoverflow/search` |

#### INTERACT

顺序执行浏览器动作：

1. `bb-browser open <url> --json` — 打开页面
2. 按序执行动作：
   - `bb-browser click <selector> --json`
   - `bb-browser fill <selector> <value> --json`
   - `bb-browser scroll <direction> --json`
   - `bb-browser screenshot --json`
   - `wait` (asyncio.sleep)
3. `bb-browser get text --json` — 获取最终页面文本

#### STRUCTURED

所有输出通过 `--json` 标志获取 JSON 格式，自动解析为 Python dict/list。

### 域名→适配器映射

| 域名 | 适配器 |
|------|--------|
| bilibili.com | bilibili |
| zhihu.com | zhihu |
| twitter.com / x.com | twitter |
| reddit.com | reddit |
| github.com | github |
| youtube.com | youtube |
| xiaohongshu.com | xiaohongshu |
| weibo.com | weibo |
| douban.com | douban |
| news.ycombinator.com | hackernews |
| arxiv.org | arxiv |
| stackoverflow.com | stackoverflow |
| v2ex.com | v2ex |

### 限制

- 依赖 Node.js 运行时
- 需要 bb-browser daemon 运行
- 某些站点需要认证 (auth_required)
- 子进程调用有启动开销

---

## 6. CLIBrowser

### 简介

CLIBrowser 是用 Rust 编写的命令行浏览器，零外部依赖，支持隐身模式。作为终极降级引擎，当所有其他引擎都失败时使用。

### 安装

从 [github.com/anthropics/clibrowser](https://github.com/anthropics/clibrowser) 下载或编译：

```bash
# 从 release 下载
# 或从源码编译
cargo install clibrowser

# 验证安装
clibrowser --version
```

### 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `CLIBROWSER_BIN` | `clibrowser` | 二进制路径 |
| `CLIBROWSER_TIMEOUT` | `30` | 超时秒数 |
| `CLIBROWSER_ENABLED` | `true` | 启用/禁用 |

### 能力

#### FETCH

两步抓取流程：
1. `clibrowser get <url>` — 获取 HTML
2. `clibrowser markdown` — 转换为 Markdown (失败则返回原始 HTML)

支持的选项：
- `--session <name>` — 复用命名会话
- `--stealth` — 启用隐身模式

#### SEARCH

`clibrowser search <query>` — 内置搜索

输出解析策略：
1. 先尝试 JSON 解析 (structured)
2. 降级为行解析 (URL + title + snippet 启发式匹配)

### 健康检查

双策略：
1. `clibrowser --version` (优先)
2. `clibrowser get https://httpbin.org/get` (降级)

### 特色

- **零依赖**: 单二进制文件，无需 Node.js/Python/Chromium
- **Rust 性能**: 编译型语言，启动快
- **隐身模式**: `--stealth` 标志启用反检测
- **会话复用**: `--session` 保持 cookies/state
- **Markdown 输出**: 自动 HTML→Markdown 转换

### 限制

- 不支持 INTERACT、STRUCTURED
- 搜索结果质量依赖于内置搜索引擎
- 复杂 JS 渲染站点支持有限 (非浏览器引擎)
- 需要从源码编译或下载预编译 binary

---

## 引擎注册优先级 / Engine Registration Order

在 `mcp_server.py` 中，引擎按以下顺序注册（决定默认优先级）：

```
1. bb-browser     (if BB_BROWSER_ENABLED)
2. opencli        (if OPENCLI_ENABLED)
3. scrapling      (always — Python 依赖，无需外部二进制)
4. lightpanda     (if LP_ENABLED)
5. pinchtab       (if PINCHTAB_BASE_URL is set)
6. clibrowser     (if CLIBROWSER_ENABLED)
```

可通过 `ENGINE_PRIORITY` 环境变量自定义：
```
ENGINE_PRIORITY=bb-browser,opencli,scrapling,lightpanda,clibrowser
```

---

## 引擎选择指南 / Engine Selection Guide

| 场景 | 推荐引擎 | 理由 |
|------|---------|------|
| 获取 B站/知乎/微博等中文站点数据 | bb-browser, opencli | 站点适配器，结构化输出 |
| 通用网页抓取 | scrapling | 3 层降级，覆盖面广 |
| 反爬严格的站点 | scrapling (stealth), clibrowser (--stealth) | 反检测能力 |
| 需要登录的站点 | bb-browser, pinchtab | 支持认证会话 |
| 需要浏览器交互 | pinchtab, bb-browser, lightpanda | INTERACT 能力 |
| 搜索聚合 | bb-browser | 5+ 搜索引擎适配器 |
| 低资源环境 | clibrowser | 零依赖，单二进制 |
| 高性能批量抓取 | lightpanda | 9x 速度, 16x 省内存 |
| CI/CD 环境 | scrapling (http), clibrowser | 无需外部服务 |
| 云端部署 | pinchtab | 远程浏览器，无需本地浏览器 |

---

## 健康检查机制 / Health Check Summary

| 引擎 | 检查方式 | 超时 | 降级策略 |
|------|---------|------|---------|
| OpenCLI | `opencli --version` | 10s | 跳过 |
| Scrapling | `fetch("https://httpbin.org/get")` | 15s | 始终可用 (Python 库) |
| Lightpanda | WebSocket connect + `Browser.getVersion` | 5s | 跳过 |
| PinchTab | HTTP GET `PINCHTAB_BASE_URL` | 10s | 跳过 (需 < 500 status) |
| bb-browser | `bb-browser status` → `bb-browser daemon status` | 10s | 跳过 |
| CLIBrowser | `clibrowser --version` → `clibrowser get httpbin.org` | 10–15s | 跳过 |
