# Architecture — Unified Web Skill v3.0

本文档描述 unified-web-skill 的系统架构、核心设计模式和数据流。

---

## 1. 系统总览 / System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI Agent / OpenClaw                          │
│                    (MCP Client — stdio or HTTP)                     │
└─────────────────────────┬───────────────────────────────────────────┘
                          │  MCP Protocol (JSON-RPC 2.0)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Server Layer                            │
│                                                                     │
│  ┌─────────────┐ ┌──────────┐ ┌─────────┐ ┌────────────────────┐   │
│  │ research_   │ │web_fetch │ │ web_cli │ │  web_interact      │   │
│  │ and_collect │ │          │ │         │ │                    │   │
│  └──────┬──────┘ └────┬─────┘ └────┬────┘ └─────────┬──────────┘   │
│  ┌──────┴──────┐ ┌────┴─────┐ ┌────┴────┐ ┌─────────┴──────────┐   │
│  │ web_search  │ │web_crawl │ │ engine_ │ │    /health         │   │
│  │   (NEW)     │ │  (NEW)   │ │ status  │ │   (HTTP sidecar)   │   │
│  └─────────────┘ └──────────┘ └─────────┘ └────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      Research Pipeline v3                           │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │ Intent   │→│  Query   │→│Multi-Source│→│ Concurrent Fetch │   │
│  │Classifier│  │ Planner  │  │ Discovery │  │  (semaphore)     │   │
│  └──────────┘  └──────────┘  └───────────┘  └────────┬─────────┘   │
│                                                       ▼             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │ Result   │←│  Dedup   │←│ Quality   │←│    Content       │   │
│  │ Storage  │  │ (hash)  │  │   Gate    │  │   Extractor      │   │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        Engine Manager                               │
│                                                                     │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────────────┐  │
│  │  SmartRouter  │  │SiteRegistry(67)│  │EngineHealthMonitor     │  │
│  │  (priority +  │  │domain→engine   │  │  (circuit breaker)     │  │
│  │   fallback)   │  │  mapping       │  │  (per-engine state)    │  │
│  └───────┬───────┘  └────────────────┘  └────────────────────────┘  │
│          │                                                          │
│  ┌───────┴───────────────────────────────────────────────────────┐  │
│  │                    DomainRateLimiter                           │  │
│  │                 (token bucket per domain)                      │  │
│  └───────────────────────────────────────────────────────────────┘  │
├────────┬────────┬────────┬────────┬────────┬────────────────────────┤
│        │        │        │        │        │                        │
│ OpenCLI│Scraplng│ Light  │ Pinch  │  bb-   │   CLIBrowser           │
│        │ 3-tier │ panda  │  Tab   │browser │                        │
│ CLI    │HTTP/PW │  CDP   │  MCP   │  CLI   │    CLI                 │
│ binary │/Stealt │  WS    │  HTTP  │ binary │   binary               │
│        │  h     │        │  RPC   │        │                        │
└────────┴────────┴────────┴────────┴────────┴────────────────────────┘
         ▼         ▼        ▼        ▼        ▼         ▼
     [ External engine binaries / services / libraries ]
```

---

## 2. Engine Protocol 设计 / Engine Protocol Design

### 2.1 Protocol 定义

所有引擎通过 `Engine` Protocol (structural typing) 统一接口，无需继承：

```python
@runtime_checkable
class Engine(Protocol):
    @property
    def name(self) -> str: ...              # 唯一标识 (e.g., "scrapling")

    @property
    def capabilities(self) -> set[Capability]: ...  # 能力声明

    async def health_check(self) -> bool: ...       # 健康探测

    async def fetch(self, url, *, timeout=30, **opts) -> FetchResult: ...
    async def search(self, query, *, max_results=10, language="zh", **opts) -> list[SearchResult]: ...
    async def interact(self, url, actions, *, timeout=60, **opts) -> InteractResult: ...
```

### 2.2 Capability 枚举

```python
class Capability(enum.Enum):
    FETCH      = "fetch"       # 抓取 URL 并返回内容
    SEARCH     = "search"      # 按关键词搜索
    INTERACT   = "interact"    # 浏览器交互（点击/填表/截图）
    CRAWL      = "crawl"       # 多页面爬取
    STRUCTURED = "structured"  # 返回结构化 JSON 数据
```

### 2.3 数据传输对象 (DTOs)

| DTO | 关键字段 | 用途 |
|-----|---------|------|
| `FetchResult` | ok, url, text, html, title, engine, route, duration_ms, content_hash, metadata | 单页抓取结果 |
| `SearchResult` | url, title, snippet, source, rank, credibility, metadata | 搜索命中项 |
| `InteractResult` | ok, url, text, snapshot (base64), instance_id, engine, duration_ms | 交互结果 |

### 2.4 BaseEngine ABC

提供默认（异常抛出）实现的抽象基类，具体适配器只需覆盖声明能力对应的方法：

```
BaseEngine
  ├── OpenCLIEngine      (FETCH, SEARCH, STRUCTURED)
  ├── ScraplingEngine     (FETCH)
  ├── LightpandaEngine    (FETCH, INTERACT)
  ├── PinchTabEngine      (FETCH, INTERACT)
  ├── BBBrowserEngine     (FETCH, SEARCH, INTERACT, STRUCTURED)
  └── CLIBrowserEngine    (FETCH, SEARCH)
```

辅助方法：
- `_timed()` — 异步计时上下文管理器，自动记录 elapsed_ms
- `_run_subprocess(cmd, timeout)` — 异步子进程执行，超时保护，返回 (returncode, stdout, stderr)

---

## 3. SmartRouter 算法 / SmartRouter Algorithm

SmartRouter 是纯函数容器（只读），不修改引擎状态。它依赖 SiteRegistry 和 HealthMonitor 做决策。

### 3.1 Fetch 路由优先级

```
resolve_fetch_order(url, available_engines, preferred) → list[str]
```

**决策流程：**

```
1. 用户指定 preferred_engines?
   ├── 是 → 使用 preferred 列表
   └── 否 → 2. SiteRegistry 匹配?
              ├── 是 → 使用注册表引擎列表
              └── 否 → 3. 中文域名?
                         ├── 是 → 中文优先序列:
                         │        lightpanda → scrapling_pw →
                         │        scrapling_stealth → scrapling → clibrowser
                         └── 否 → 默认序列:
                                  scrapling → lightpanda → scrapling_pw →
                                  scrapling_stealth → clibrowser

过滤: 仅保留 (已注册 ∩ 支持 FETCH ∩ 健康) 的引擎
补充: 追加其余健康 FETCH 引擎
```

### 3.2 Interact 路由

```
resolve_interact_engine(url, available_engines, preferred) → str | None
```

优先级固定序列: `pinchtab → bb_browser → lightpanda → scrapling_pw`

过滤条件: 支持 INTERACT + HealthMonitor 可用

### 3.3 Fallback 链

EngineManager.fetch_with_fallback 实现逐引擎降级：

```
for engine_name in router.resolve_fetch_order(url):
    result = engine.fetch(url)
    if result.ok:
        health_monitor.record_success(engine_name)
        return result
    else:
        health_monitor.record_failure(engine_name)
        continue  # try next engine

return FetchResult(ok=False, error="All engines exhausted")
```

**关键语义：**
- 方法**永不抛异常** — 总是返回 FetchResult/InteractResult
- 每次成功/失败都更新 HealthMonitor
- NotImplementedError 被静默跳过（不计入失败）

---

## 4. SiteRegistry 设计 / SiteRegistry Design

### 4.1 数据模型

```python
@dataclass
class SiteCapability:
    site_id: str              # "bilibili"
    display_name: str         # "哔哩哔哩"
    domains: list[str]        # ["bilibili.com", "b23.tv"]
    engines: list[str]        # ["bb-browser", "opencli"]  (优先级顺序)
    commands: dict[str, str]  # {"search": "bilibili/search", "hot": "bilibili/hot"}
    auth_required: bool       # 是否需要认证
    auth_engine: str          # 认证引擎 ("pinchtab" / "bb-browser")
    content_type: str         # video / article / social / news / paper / code / finance / shopping / search / jobs
    country: str              # cn / global / us / jp
    default_fetch_mode: str   # http / dynamic / stealth / auto
    notes: str                # 备注
```

### 4.2 站点覆盖

67 个内置站点按类别分布：

| 类别 | 数量 | 示例 |
|------|------|------|
| 中文社交/内容 | 20 | bilibili, zhihu, weibo, xiaohongshu, douyin, tieba, v2ex, jike |
| 中文财经/商业 | 8 | xueqiu, eastmoney, taobao, jd, pinduoduo, smzdm, ctrip, boss |
| 全球社交 | 10 | twitter, reddit, facebook, instagram, tiktok, discord, telegram, bluesky, linkedin, mastodon |
| 全球技术 | 10 | github, stackoverflow, hackernews, medium, dev.to, npm, pypi, arxiv, gitlab, mdn |
| 全球内容/媒体 | 13 | youtube, wikipedia, bbc, reuters, producthunt, imdb, amazon, nytimes, cnn, spotify, twitch, quora |
| 搜索引擎 | 5 | google, bing, duckduckgo, sogou, yandex |

### 4.3 查找机制

```
lookup_by_url(url) → SiteCapability | None

1. 提取 hostname
2. 精确匹配 domain_index
3. 逐级剥离子域名后缀匹配 (www.bilibili.com → bilibili.com)
```

### 4.4 Singleton 模式

```python
registry = SiteRegistry.get_instance()
registry.load_builtin()  # 加载 67 个内置站点
```

支持从外部 JSON 文件扩展: `registry.load_from_file("custom_sites.json")`

---

## 5. Research Pipeline 阶段 / Pipeline Stages

### 完整流程

```
                    ┌────────────────┐
                    │  User Query    │
                    │ "AI 芯片最新进展" │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 1 │ Intent Classify │
                    │ → ACADEMIC     │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 2 │ Query Expand   │  max_queries=8
                    │ → 6 variants   │  intent-aware
                    │ "AI 芯片 论文"   │
                    │ "AI 芯片 研究"   │
                    │ "AI 芯片 综述"   │
                    │ ...            │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 3 │ Multi-Source    │  parallel search
                    │ Discovery      │  across engines
                    │ → 30 URLs      │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 4 │ Domain Filter  │  include/exclude
                    │ → 25 URLs      │  domain lists
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 5 │ Concurrent     │  asyncio.Semaphore
                    │ Fetch (×5)     │  EngineManager.fetch_with_fallback
                    │ Rate-limited   │  DomainRateLimiter
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 6 │ Content Extract│  scrapling Adaptor → regex fallback
                    │ + Quality Gate │  min_length, boilerplate, freshness
                    │ → 18 records   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 7 │ Deduplicate    │  content_hash (SHA-1)
                    │ → 15 records   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
            Stage 8 │ Storage        │  JSON / NDJSON / Markdown
                    │ → outputs/     │
                    └────────────────┘
```

### 各阶段详解

#### Stage 1: Intent Classification

`IntentClassifier` 使用 130+ 条 regex 模式（中英双语）将查询分为 9 类意图：

| 意图 | 中文关键词示例 | 英文关键词示例 |
|------|--------------|--------------|
| INFORMATIONAL | 什么是, 如何, 怎么, 教程 | how to, what is, guide |
| NEWS | 新闻, 最新, 今日, 热点 | news, breaking, latest |
| ACADEMIC | 论文, 研究, 学术, 文献 | paper, research, arxiv |
| CODE | 代码, 编程, 报错, 框架 | code, github, api, npm |
| FINANCE | 股票, 基金, 行情, 财报 | stock, market, earnings |
| SOCIAL | 微博, 抖音, 评论, 粉丝 | tweet, reddit, viral |
| TRANSACTIONAL | 购买, 价格, 下载, 优惠 | buy, price, download |
| NAVIGATIONAL | 官网, 登录, 首页 | official site, login |
| LOCAL | 附近, 餐厅, 地址, 导航 | nearby, near me, directions |

每个意图有对应的推荐搜索引擎列表 (`_SOURCE_MAP`)，按语言区分。

#### Stage 2: Query Expansion

`QueryPlanner` 根据意图生成查询变体，原始查询始终排首位：

```
原始: "Transformer 架构"
意图: ACADEMIC
扩展:
  1. "Transformer 架构"         (原始)
  2. "Transformer 架构 论文"     (学术后缀)
  3. "Transformer 架构 研究"
  4. "Transformer 架构 综述"
  5. "Transformer 架构 最新进展"
  6. "Transformer 架构 学术"
```

#### Stage 5: Concurrent Fetch

使用 `asyncio.Semaphore(max_concurrency)` 控制并发，`DomainRateLimiter` 控制每域名 QPS (默认 2.0)。

每个 URL 的抓取流程：
1. `rate_limiter.acquire(domain)` — 等待令牌
2. `engine_manager.fetch_with_fallback(url)` — 多引擎降级抓取
3. `extractor.extract(result)` — 内容提取
4. `quality.validate(extracted)` — 质量门控
5. 构建 `ResearchRecord`

#### Stage 6: Content Extraction

`ContentExtractor` 采用双策略：

1. **Scrapling Adaptor** (优先) — CSS 选择器提取 (`article`, `main`, `.content`, `#content`)
2. **Regex 降级** — 移除 script/style/comment，HTML 实体解码，标签剥离

额外提取：
- **标题**: og:title → `<title>` 标签
- **日期**: meta 标签 → `<time>` 元素 → 正文日期模式 (ISO-8601, YYYY-MM-DD, 中文日期)
- **链接**: `<a href>` 标签
- **语言**: CJK/Latin 字符比例启发式检测
- **哈希**: SHA-1 前 16 位

#### Stage 6b: Quality Gate

| 检查项 | 条件 | 动作 |
|--------|------|------|
| 文本长度 | `len(text) < min_text_length` | 拒绝 |
| 模板页面 | 包含 "access denied", "404" 等且 < 500 字 | 拒绝 |
| 时效性 | 发布日期早于 `time_window_days` | 拒绝 |

#### Stage 7: Deduplication

基于 `content_hash` (SHA-1 前 16 位) 去重，保留首次出现的记录。

---

## 6. 熔断器 / Circuit Breaker

`EngineHealthMonitor` 为每个引擎维护独立状态机：

```
        record_success()
  ┌──────────────────────────┐
  │                          │
  ▼                          │
HEALTHY ──failure──→ DEGRADED ──3 failures──→ UNHEALTHY
  ▲                     │                       │
  │                     │ success               │ 60s cooldown
  │                     ▼                       ▼
  └─────────── DEGRADED ←──────────── HALF-OPEN
                                    (1 probe allowed)
```

**参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `check_interval` | 300s | 健康检查最小间隔 |
| `failure_threshold` | 3 | 连续失败触发断路 |
| `circuit_open_duration` | 60s | 断路持续时间 |
| `half_open_probe_limit` | 1 | 半开状态允许的探测数 |

**SmartRouter 与 HealthMonitor 的交互：**

- `is_available(engine_name)` — 快速判断引擎是否可用（不触发实际探测）
- `record_success(name)` / `record_failure(name)` — 每次 fetch/search/interact 后更新
- `check(engine)` — 运行实际健康探测（受 check_interval 节流）
- `summary()` — 返回所有引擎健康状态的 JSON 快照

---

## 7. 限流 / Rate Limiting

`DomainRateLimiter` 使用令牌桶算法实现每域名 QPS 控制：

```python
limiter = DomainRateLimiter(default_qps=2.0)

# 请求前获取令牌
await limiter.acquire("bilibili.com")   # 自动等待 500ms 间隔
await limiter.acquire("bilibili.com")   # 如果间隔不足则 sleep
```

每个域名有独立的 `asyncio.Lock`，保证同域名请求的串行化。

---

## 8. 异常层级 / Exception Hierarchy

```
WebSkillError (base)
├── EngineError (engine, exit_code)
│   ├── EngineNotAvailableError   # 引擎未安装/不响应
│   ├── EngineTimeoutError        # 引擎超时
│   ├── AuthRequiredError         # 站点需认证
│   └── BlockedError              # 被反爬拦截
├── ConfigError                   # 配置错误
├── DiscoveryError                # URL 发现错误
├── ExtractionError               # 内容提取错误
└── StorageError                  # 结果存储错误
```

**设计原则：** MCP 工具层捕获所有异常，返回 `{"ok": false, "error": "..."}` — 永不向客户端抛出。

---

## 9. 可信度评分 / Credibility Scoring

`score_credibility(url, trusted_mode)` 返回 0.0–1.0 分数：

| 规则 | 加分 |
|------|------|
| 基准分 | 0.40 |
| HTTPS | +0.10 |
| 可信域名 (gov, edu, who.int, nature.com, arxiv.org 等) | +0.35 |
| 知名媒体 (nytimes, reuters, bbc 等) | +0.15 |
| 知名技术站 (github, stackoverflow 等) | +0.10 |
| 权威 TLD (.gov, .edu, .org, .mil) | +0.20 |
| 通用 TLD (.com, .net, .io) | +0.05 |

`trusted_mode=True` 时，分数 < 0.5 的来源额外乘以 0.8 惩罚系数。

---

## 10. 数据模型 / Data Models

### ResearchTask (输入)

```python
class ResearchTask(BaseModel):
    task_id: str              # UUID, 自动生成
    query: str                # 研究主题
    language: str = "zh"
    max_sources: int = 30     # 1–500
    max_pages: int = 20       # 1–200
    max_queries: int = 8      # 1–30
    max_concurrency: int = 5  # 1–20
    timeout_seconds: int = 30 # 5–300
    preferred_engines: list[str]
    search_engines: list[str]
    enable_site_adapters: bool = True
    enable_stealth: bool = False
    min_text_length: int = 100
    min_credibility: float = 0.3
    trusted_mode: bool = False
    time_window_days: int = 0
    include_domains: list[str]
    exclude_domains: list[str]
    output_format: str = "json"
    output_dir: str = "outputs"
```

### ResearchRecord (单条结果)

```python
class ResearchRecord(BaseModel):
    url: str
    title: str
    text: str
    summary: str              # 自动截取前 300 字
    published_at: str | None
    language: str
    content_hash: str         # SHA-1[:16]
    text_length: int          # 自动计算
    fetch_engine: str
    fetch_mode: str           # e.g., "opencli:bilibili/hot"
    fetch_duration_ms: float
    credibility: float
    source_type: str          # "search" | "site_adapter" | "direct"
    tool_chain: list[str]
    extra: dict
```

### ResearchResult (输出)

```python
class ResearchResult(BaseModel):
    task: ResearchTask
    records: list[ResearchRecord]
    stats: ResearchStats
    queries_used: list[str]
    output_files: list[str]
    created_at: str           # ISO-8601 UTC
```

### ResearchStats (统计)

```python
class ResearchStats(BaseModel):
    total_discovered: int
    total_collected: int
    total_skipped: int
    skipped_quality: int
    skipped_duplicate: int
    skipped_blocked: int
    engines_used: dict[str, int]   # engine_name → count
    search_engines_used: list[str]
    fallback_count: int
    avg_fetch_ms: float
    total_duration_s: float
```

---

## 11. Transport 模式 / Transport Modes

MCP Server 支持两种传输模式：

### stdio 模式 (推荐用于 AI Agent)

```bash
python -m app.mcp_server --stdio
# 或非 TTY 环境自动切换
```

适用于 OpenClaw bundle-mcp 等 MCP 客户端直接 pipe 调用。

### HTTP/SSE 模式 (推荐用于调试)

```bash
python -m app.mcp_server
# 默认 http://0.0.0.0:8000
```

附带 `/health` sidecar 端点。MCP 工具通过 SSE (Server-Sent Events) 或 Streamable HTTP 提供。

---

## 12. 设计决策 / Design Decisions

| 决策 | 理由 |
|------|------|
| Protocol (structural typing) 而非基类继承 | 引擎可以来自不同包，无需 import base |
| BaseEngine ABC 提供默认实现 | 减少样板代码，具体引擎只覆盖声明能力的方法 |
| `_run_subprocess` 统一子进程管理 | CLI 引擎 (opencli, bb-browser, clibrowser) 共享超时/错误处理 |
| 永不抛异常的 fetch/interact | MCP 工具层简化，始终返回结构化结果 |
| Singleton SiteRegistry | 全局共享站点数据，避免重复加载 |
| 每域名独立限流 | 避免某个域名被封导致全局受影响 |
| Circuit Breaker 而非简单重试 | 快速隔离故障引擎，避免级联超时 |
| Intent-aware query expansion | 不同意图需要完全不同的搜索策略 |
