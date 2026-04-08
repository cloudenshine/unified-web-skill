# API Reference — Unified Web Skill v3.0

Complete reference for all 7 MCP tools. All tools return JSON dicts and **never raise exceptions** to the client.

---

## 通用约定 / Conventions

- **所有工具返回 `ok: bool`** — `true` 表示成功，`false` 表示失败
- **失败时返回 `error: string`** — 描述错误原因
- **时间戳** — `duration_ms` (毫秒) 或 `duration_s` (秒)
- **逗号分隔列表** — 多值参数（如 `include_domains`, `engines`）使用逗号分隔字符串

---

## 1. research_and_collect

完整研究管线：意图分类 → 查询扩展 → 多源发现 → 并发抓取 → 质量验证 → 去重 → 结构化输出。

### 参数 / Parameters

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|:----:|--------|------|------|
| `query` | string | ✅ | — | — | 研究主题或问题 |
| `language` | string | | `"zh"` | `"zh"` / `"en"` | 目标语言 |
| `max_sources` | int | | `30` | 1–500 | 最大发现来源数 |
| `max_pages` | int | | `20` | 1–200 | 最大抓取页面数 |
| `max_queries` | int | | `8` | 1–30 | 最大扩展查询数 |
| `trusted_mode` | bool | | `false` | — | 仅抓取高可信度来源 |
| `output_format` | string | | `"json"` | `"json"` / `"ndjson"` / `"md"` | 输出格式 |
| `min_text_length` | int | | `100` | ≥0 | 最小文本长度 |
| `min_credibility` | float | | `0.3` | 0.0–1.0 | 最小可信度分数 |
| `time_window_days` | int | | `0` | ≥0 | 时间窗口天数 (0=不限) |
| `include_domains` | string | | `""` | 逗号分隔 | 域名白名单 |
| `exclude_domains` | string | | `""` | 逗号分隔 | 域名黑名单 |
| `preferred_engines` | string | | `""` | 逗号分隔 | 偏好引擎列表 |
| `search_engines` | string | | `""` | 逗号分隔 | 搜索引擎列表 |
| `enable_stealth` | bool | | `false` | — | 启用隐身抓取 |
| `max_concurrency` | int | | `5` | 1–20 | 最大并发抓取数 |

### 返回值 / Return Value

```json
{
  "ok": true,
  "query": "AI 芯片最新进展",
  "records": [
    {
      "url": "https://arxiv.org/abs/2401.xxxxx",
      "title": "Next-Generation AI Accelerator Architecture",
      "text": "This paper surveys recent advances...",
      "summary": "This paper surveys recent advances in AI chip design...",
      "published_at": "2024-01-15",
      "language": "en",
      "content_hash": "a1b2c3d4e5f6g7h8",
      "text_length": 4523,
      "fetch_engine": "scrapling",
      "fetch_mode": "scrapling-http",
      "fetch_duration_ms": 1234.5,
      "credibility": 0.85,
      "source_type": "search",
      "tool_chain": ["scrapling"],
      "extra": {}
    }
  ],
  "stats": {
    "total_discovered": 30,
    "total_collected": 15,
    "total_skipped": 15,
    "skipped_quality": 5,
    "skipped_duplicate": 3,
    "skipped_blocked": 7,
    "engines_used": {"scrapling": 10, "opencli": 5},
    "search_engines_used": ["bb-browser:google/search"],
    "fallback_count": 2,
    "avg_fetch_ms": 1500.0,
    "total_duration_s": 45.2
  },
  "queries_used": [
    "AI 芯片最新进展",
    "AI 芯片最新进展 论文",
    "AI 芯片最新进展 研究",
    "AI 芯片最新进展 综述"
  ],
  "output_files": ["outputs/research_2024xxxx_xxxxxx.json"],
  "duration_ms": 45234.5
}
```

### 失败返回

```json
{
  "ok": false,
  "error": "Pipeline error: No search engines available",
  "duration_ms": 123.4
}
```

### 示例调用 / Example

```json
{
  "tool": "research_and_collect",
  "arguments": {
    "query": "2024 年大语言模型技术趋势",
    "language": "zh",
    "max_sources": 50,
    "max_pages": 30,
    "trusted_mode": true,
    "output_format": "json",
    "exclude_domains": "csdn.net,jianshu.com",
    "max_concurrency": 10
  }
}
```

---

## 2. web_fetch

单 URL 抓取，自动路由到最优引擎，支持多级降级。

### 参数 / Parameters

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|------|------|:----:|--------|------|------|
| `url` | string | ✅ | — | 有效 URL | 目标 URL |
| `task` | string | | `""` | — | 抓取目的描述 (用于日志) |
| `mode` | string | | `"auto"` | `auto` / `http` / `dynamic` / `stealth` | 路由模式 |
| `prefer_text` | bool | | `true` | — | `true`=提取文本, `false`=原始 HTML |
| `timeout` | int | | `30` | — | 超时秒数 |
| `engine` | string | | `""` | 已注册引擎名 | 强制指定引擎 |

### 返回值 / Return Value

```json
{
  "ok": true,
  "url": "https://example.com/article",
  "text": "Article content extracted as clean text...",
  "html": "",
  "title": "Example Article Title",
  "engine": "scrapling",
  "mode": "auto",
  "duration_ms": 856.3,
  "error": ""
}
```

### mode 说明

| mode | 行为 |
|------|------|
| `auto` | SmartRouter 自动决定引擎优先级（推荐） |
| `http` | 强制仅使用 HTTP 层 (最快, 但可能被拦截) |
| `dynamic` | 强制使用动态渲染 (Playwright / CDP) |
| `stealth` | 强制使用隐身模式 (StealthyFetcher) |

### 示例调用

```json
{
  "tool": "web_fetch",
  "arguments": {
    "url": "https://www.zhihu.com/question/123456",
    "mode": "dynamic",
    "prefer_text": true,
    "timeout": 60
  }
}
```

---

## 3. web_cli

直接调用站点适配器 (bb-browser 优先, OpenCLI 降级) 执行站点命令。

### 参数 / Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `site` | string | ✅ | — | 站点适配器名 |
| `command` | string | ✅ | — | 执行的命令 |
| `args` | string | | `""` | 命令参数 (逗号分隔) |

### 返回值 / Return Value

```json
{
  "ok": true,
  "site": "bilibili",
  "command": "hot",
  "data": [
    {"title": "热门视频1", "url": "...", "view_count": 1000000},
    {"title": "热门视频2", "url": "...", "view_count": 500000}
  ],
  "engine": "bb_browser",
  "duration_ms": 2345.6
}
```

### 常用站点命令 / Common Site Commands

| 站点 | 命令 | 说明 | 示例 args |
|------|------|------|----------|
| `bilibili` | `hot` | B站热门 | — |
| `bilibili` | `search` | B站搜索 | `"关键词"` |
| `zhihu` | `hot` | 知乎热榜 | — |
| `zhihu` | `search` | 知乎搜索 | `"关键词"` |
| `hackernews` | `hot` | HN 热帖 | — |
| `twitter` | `search` | 推特搜索 | `"关键词"` |
| `twitter` | `trending` | 推特热搜 | — |
| `reddit` | `hot` | Reddit 热帖 | — |
| `reddit` | `search` | Reddit 搜索 | `"关键词"` |
| `weibo` | `hot` | 微博热搜 | — |
| `github` | `trending` | GitHub 趋势 | — |
| `youtube` | `search` | YouTube 搜索 | `"关键词"` |
| `arxiv` | `search` | arXiv 搜索 | `"关键词"` |
| `producthunt` | `hot` | PH 今日推荐 | — |
| `xueqiu` | `hot` | 雪球热帖 | — |
| `v2ex` | `hot` | V2EX 热帖 | — |

### 示例调用

```json
{
  "tool": "web_cli",
  "arguments": {
    "site": "bilibili",
    "command": "search",
    "args": "大语言模型"
  }
}
```

---

## 4. web_interact

浏览器交互操作：导航、点击、填表、滚动、截图。使用最佳可用交互引擎 (PinchTab → bb-browser → Lightpanda)。

### 参数 / Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `url` | string | | `""` | 目标 URL |
| `task` | string | | `""` | 交互目标的自然语言描述 |
| `actions` | string | | `""` | JSON 编码的动作列表 |
| `instance_id` | string | | `""` | 复用已有浏览器会话 |
| `return_snapshot` | bool | | `true` | 返回 base64 截图 |
| `return_text` | bool | | `true` | 返回页面文本 |
| `timeout` | int | | `60` | 超时秒数 |
| `engine` | string | | `""` | 强制指定引擎 |

### Actions 格式

actions 是一个 JSON 数组，每个元素包含 `type` 和相应参数：

```json
[
  {"type": "click", "selector": "#login-btn"},
  {"type": "fill", "selector": "#username", "value": "user@example.com"},
  {"type": "fill", "selector": "#password", "value": "secret"},
  {"type": "click", "selector": "#submit"},
  {"type": "wait", "seconds": 2},
  {"type": "scroll", "direction": "down"},
  {"type": "screenshot"},
  {"type": "evaluate", "expression": "document.title"}
]
```

**支持的动作类型：**

| type | 参数 | 引擎支持 | 说明 |
|------|------|---------|------|
| `click` | `selector` | bb-browser, Lightpanda, PinchTab | 点击元素 |
| `fill` / `type` | `selector`, `value` | bb-browser, Lightpanda, PinchTab | 填写输入框 |
| `scroll` | `direction` | bb-browser, PinchTab | 滚动页面 |
| `wait` | `seconds` | all | 等待指定秒数 |
| `screenshot` | — | bb-browser, PinchTab | 截图 |
| `navigate` | `url` | PinchTab | 导航到 URL |
| `evaluate` | `expression` | Lightpanda | 执行 JS 表达式 |
| `submit` | `selector` | PinchTab | 提交表单 |

### 返回值 / Return Value

```json
{
  "ok": true,
  "url": "https://example.com/dashboard",
  "text": "Page content after interaction...",
  "snapshot": "data:image/png;base64,iVBOR...",
  "instance_id": "session-abc123",
  "engine": "pinchtab",
  "duration_ms": 5432.1,
  "error": ""
}
```

### 示例调用

```json
{
  "tool": "web_interact",
  "arguments": {
    "url": "https://zhihu.com/question/123456",
    "task": "展开全部回答并截图",
    "actions": "[{\"type\":\"scroll\",\"direction\":\"down\"},{\"type\":\"wait\",\"seconds\":2},{\"type\":\"click\",\"selector\":\".QuestionMainAction\"}]",
    "return_snapshot": true,
    "return_text": true,
    "timeout": 60
  }
}
```

---

## 5. web_search *(NEW in v3.0)*

多引擎搜索聚合。跨所有支持 SEARCH 能力的引擎并发搜索，结果按 URL 去重、按可信度排序。

### 参数 / Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `query` | string | ✅ | — | 搜索关键词 |
| `max_results` | int | | `10` | 最大结果数 |
| `language` | string | | `"zh"` | 目标语言 (`zh` / `en`) |
| `engines` | string | | `""` | 指定引擎 (逗号分隔, 空=全部 SEARCH 引擎) |
| `intent` | string | | `""` | 搜索意图提示 (保留) |

### 返回值 / Return Value

```json
{
  "ok": true,
  "results": [
    {
      "url": "https://arxiv.org/abs/2401.12345",
      "title": "Transformer Architecture Survey",
      "snippet": "This comprehensive survey covers...",
      "source": "bb-browser:google/search",
      "rank": 1,
      "credibility": 0.85
    },
    {
      "url": "https://github.com/example/transformer",
      "title": "Transformer Implementation",
      "snippet": "A PyTorch implementation of...",
      "source": "bb-browser:google/search",
      "rank": 2,
      "credibility": 0.6
    }
  ],
  "engines_used": ["bb-browser:google/search", "opencli:zhihu"],
  "total": 10,
  "duration_ms": 3456.7
}
```

### 搜索引擎路由

bb-browser 支持的搜索适配器：

| 适配器 | 语言偏好 | 说明 |
|--------|---------|------|
| `google/search` | en (默认英文) | Google 搜索 |
| `baidu/search` | zh (默认中文) | 百度搜索 |
| `bing/search` | — | 必应搜索 |
| `duckduckgo/search` | — | DuckDuckGo |
| `sogou/weixin` | zh | 搜狗微信搜索 |
| `twitter/search` | — | 推特搜索 |
| `reddit/search` | — | Reddit 搜索 |
| `bilibili/search` | zh | B站搜索 |
| `youtube/search` | — | YouTube 搜索 |
| `zhihu/search` | zh | 知乎搜索 |
| `github/issues` | — | GitHub Issues |
| `arxiv/search` | — | arXiv 论文搜索 |
| `stackoverflow/search` | en | Stack Overflow |

### 示例调用

```json
{
  "tool": "web_search",
  "arguments": {
    "query": "Rust async runtime comparison",
    "max_results": 20,
    "language": "en",
    "engines": "bb-browser,clibrowser"
  }
}
```

---

## 6. web_crawl *(NEW in v3.0)*

从种子 URL 出发，BFS 逐层跟随链接进行多页面爬取。

### 参数 / Parameters

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `url` | string | ✅ | — | 种子 URL |
| `max_pages` | int | | `10` | 最大爬取页面数 |
| `max_depth` | int | | `2` | 最大链接跟随深度 |
| `same_domain_only` | bool | | `true` | 仅跟随同域名链接 |
| `extract_links` | bool | | `true` | 从页面提取并跟随链接 |
| `timeout` | int | | `30` | 单页抓取超时秒数 |

### 返回值 / Return Value

```json
{
  "ok": true,
  "pages": [
    {
      "url": "https://docs.example.com/",
      "title": "Documentation Home",
      "text": "Welcome to the documentation...",
      "depth": 0
    },
    {
      "url": "https://docs.example.com/getting-started",
      "title": "Getting Started",
      "text": "To get started, first install...",
      "depth": 1
    },
    {
      "url": "https://docs.example.com/api-reference",
      "title": "API Reference",
      "text": "This page documents the public API...",
      "depth": 1
    }
  ],
  "total_pages": 3,
  "duration_s": 12.34
}
```

### 链接过滤规则

自动跳过以下链接类型：
- 非 HTTP(S) 协议 (mailto:, tel:, javascript:, data:)
- 锚点链接 (#)
- 静态资源 (.jpg, .png, .gif, .svg, .css, .js, .ico, .woff, .pdf, .zip, .mp3, .mp4 等)
- 已访问 URL (URL 去重，去除尾部 `/`)
- 非同域链接 (当 `same_domain_only=true`)

### BFS 行为

```
深度 0: seed URL
深度 1: seed 页面上的链接
深度 2: 深度 1 页面上的链接
...直到 max_depth 或 max_pages
```

### 示例调用

```json
{
  "tool": "web_crawl",
  "arguments": {
    "url": "https://docs.python.org/3/library/",
    "max_pages": 20,
    "max_depth": 2,
    "same_domain_only": true,
    "timeout": 15
  }
}
```

---

## 7. engine_status *(NEW in v3.0)*

查看所有已注册引擎的健康状态、可用性和能力列表。

### 参数 / Parameters

无参数。

### 返回值 / Return Value

```json
{
  "ok": true,
  "engines": [
    {
      "name": "bb-browser",
      "available": true,
      "capabilities": ["crawl", "fetch", "interact", "search", "structured"]
    },
    {
      "name": "opencli",
      "available": true,
      "capabilities": ["fetch", "search", "structured"]
    },
    {
      "name": "scrapling",
      "available": true,
      "capabilities": ["fetch"]
    },
    {
      "name": "lightpanda",
      "available": false,
      "capabilities": ["fetch", "interact"]
    },
    {
      "name": "clibrowser",
      "available": true,
      "capabilities": ["fetch", "search"]
    }
  ],
  "total": 5,
  "duration_ms": 5678.9
}
```

### 示例调用

```json
{
  "tool": "engine_status",
  "arguments": {}
}
```

---

## 错误码参考 / Error Reference

### 通用错误

| 错误 | 说明 |
|------|------|
| `"No engines available for FETCH"` | 所有 FETCH 引擎不可用 |
| `"No engines available for INTERACT"` | 所有 INTERACT 引擎不可用 |
| `"All engines exhausted. Last error: ..."` | 所有引擎均失败 |
| `"No CLI engine (bb-browser / opencli) available"` | web_cli 无可用引擎 |
| `"Invalid actions JSON: ..."` | web_interact 的 actions 参数 JSON 解析失败 |

### 引擎特定错误

| 引擎 | 错误 | 说明 |
|------|------|------|
| OpenCLI | `"unsupported domain for opencli: ..."` | URL 域名不在 OpenCLI 支持列表 |
| OpenCLI | `"auth_required: ..."` | 站点需要认证 (exit code 77) |
| OpenCLI | `"not_found: ..."` | 站点适配器不存在 (exit code 78) |
| Scrapling | `"blocked"` | 请求被反爬系统拦截 |
| Scrapling | `"all tiers failed"` | HTTP → Dynamic → Stealth 全部失败 |
| Lightpanda | `"websockets not installed"` | 缺少 websockets 依赖 |
| Lightpanda | `"CDP error: ..."` | Chrome DevTools Protocol 错误 |
| PinchTab | `"PINCHTAB_BASE_URL not configured"` | 未配置 PinchTab 服务地址 |
| PinchTab | `"httpx not installed"` | 缺少 httpx 依赖 |
| bb-browser | `"exit code N"` | bb-browser 进程异常退出 |
| CLIBrowser | `"binary not found: clibrowser"` | clibrowser 未安装 |

---

## 健康检查端点 / Health Endpoint

HTTP 模式下可通过 GET `/health` 检查服务状态：

```
GET http://localhost:8000/health
```

```json
{
  "status": "ok",
  "service": "unified-web-skill",
  "version": "3.0.0",
  "engines": ["bb-browser", "opencli", "scrapling", "lightpanda", "clibrowser"]
}
```
