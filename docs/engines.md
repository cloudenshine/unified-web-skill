# Engines — Unified Web Skill v3.0

3 引擎详细文档：安装、配置、能力、限制和使用示例。

---

## 引擎能力总览 / Capability Overview

| 引擎 | FETCH | SEARCH | INTERACT | STRUCTURED | 健康检查方式 |
|------|:-----:|:------:|:--------:|:----------:|-------------|
| **OpenCLI** | ✅ | ✅ | ❌ | ✅ | `opencli --version` |
| **Scrapling** | ✅ | ✅ | ❌ | ❌ | fetch httpbin.org |
| **CloakBrowser** | ✅ | ❌ | ✅ | ❌ | CDP Browser.getVersion |

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

## 引擎注册优先级 / Engine Registration Order

在 `mcp_server.py` 中，引擎按以下顺序注册（决定默认优先级）：

```
2. opencli        (if OPENCLI_ENABLED)
3. scrapling      (always — Python 依赖，无需外部二进制)

```

可通过 `ENGINE_PRIORITY` 环境变量自定义：
```
ENGINE_PRIORITY=opencli,scrapling,cloakbrowser
```

---

## 引擎选择指南

总原则：同等结果质量下，优先选择更轻、更稳定、依赖更少的路径。`opencli`
daemon 已恢复，但它应作为结构化 adapter、动态浏览器和交互会话的强能力补位层，
不应成为所有复杂网页的默认入口。

| 网页/数据类型 | 首选路径 | fallback | 理由 |
|------|---------|----------|------|
| 官方 API / JSON endpoint | scrapling HTTP | 无或站点 API provider | 成本最低、结构最稳定、最适合批量验证 |
| RSS / Atom feed | scrapling HTTP | 无 | 新闻和更新流最稳定的全球覆盖主干 |
| 官方文档 / 静态页面 / 百科 | scrapling | opencli（若有结构化 adapter） | 资源占用小，文本提取稳定 |
| 包注册表 / 学术元数据 / 金融公开数据 | scrapling HTTP | opencli 或专用 API provider | 通常有稳定 API 或静态页面 |
| 已有站点 adapter 且 opencli 能返回同等质量 | opencli | scrapling | 无 daemon 依赖，资源更小 |
| 已有站点 adapter 且 CloakBrowser 覆盖更好 | CloakBrowser | opencli, scrapling | 结构化输出更好，但需要 daemon 健康 |
| JS 渲染但无需登录的公开页面 | scrapling dynamic/stealth 或 CloakBrowser | opencli | 仅在 HTTP 不足时进入浏览器路径 |
| 需要点击、滚动、表单、截图 | CloakBrowser | scrapling_pw | 需要 INTERACT 能力和会话状态 |
| 需要登录/cookie 的页面 | CloakBrowser + credential 模块 | 无 | 必须显式依赖用户 session 或凭证 |
| CAPTCHA、短信验证、严格反爬、付费墙 | 记录 boundary | 官方 API 或用户凭证 | 不作为可靠自治路线 |
| CI/CD 或低资源默认环境 | scrapling HTTP | opencli | 尽量避免 daemon、浏览器进程和外部服务 |

---

## 健康检查机制 / Health Check Summary

| 引擎 | 检查方式 | 超时 | 降级策略 |
|------|---------|------|---------|
| OpenCLI | `opencli --version` | 10s | 跳过 |
| Scrapling | `fetch("https://httpbin.org/get")` | 15s | 始终可用 (Python 库) |
| CloakBrowser | CDP Browser.getVersion via WebSocket | 5s | 跳过 |






