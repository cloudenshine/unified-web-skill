# unified-web-skill 架构分析与重构计划

> 来源: unified-web-skill 源码深度分析 (2026-04-08)
> 目标: 厘清架构 → 发现问题 → 有条理地重构

---

## 一、现有架构梳理

### 核心架构图

```
MCP Server (mcp_server.py)
│
├─ web_fetch(url, task, mode)           ← 内容抓取（只读）
│   └─ UnifiedWebSkill.web_fetch()
│       ├─ auto_route() → mode          (heuristics.py)
│       └─ fetch_with_fallback()        (scrapling_engine.py)
│           ├─ HTTP (scrapling Fetcher + impersonation)
│           ├─ Dynamic (scrapling AsyncFetcher/Playwright)
│           └─ Stealth (scrapling StealthyFetcher)
│
├─ web_interact(url, task, actions)    ← 交互任务（登录/点击/填表）
│   └─ UnifiedWebSkill.web_interact()
│       └─ PinchTabClient.interact()    (pinchtab_client.py)
│           └─ PinchTab MCP API (browser_interact tool)
│
├─ research_and_collect(query, ...)     ← 完整研究流水线
│   └─ ResearchPipeline.run()
│       ├─ expand_queries()            (query_planner.py)
│       ├─ discover_from_queries()      (discovery.py, DuckDuckGo)
│       ├─ 并发抓取 _process_url()
│       │   ├─ _fetch_via_opencli()    (opencli_client.py)
│       │   └─ _fetch_via_scrapling()  (scrapling_engine.py)
│       ├─ 质量验证 deduplicate_by_hash + validate_content
│       └─ save_research() →落盘
│
└─ web_cli(site, command, args)         ← OpenCLI 命令
    └─ run_opencli()                    (opencli_client.py)
```

### 各模块职责与原理

| 模块 | 职责 | 原理 |
|------|------|------|
| `mcp_server.py` | MCP 协议入口，路由到 Service | JSON-RPC 2.0 |
| `services.py` | 统一服务层，封装 fetch/interact/cli | 门面模式 |
| `heuristics.py` | 路由决策：任务类型+站点特征→引擎选择 | 规则引擎 |
| `scrapling_engine.py` | 三层内容抓取消歇（HTTP→Dynamic→Stealth） | Tiered fetching |
| `pinchtab_client.py` | PinchTab HTTP API 客户端 | HTTP API + MCP |
| `opencli_client.py` | OpenCLI 子进程客户端 | 异步 subprocess |
| `discovery.py` | DuckDuckGo 搜索候选 URL | ddgs 封装 |
| `query_planner.py` | 查询词扩展（固定后缀模板） | 规则模板 |
| `extractor.py` | 正文/链接/日期提取 | CSS选择器+正则 |

### 两条核心路径（正交）

**路径A — web_fetch（内容抓取，只读）：**
```
URL → auto_route() → HTTP/Dynamic/Stealth → extract_text() → text
```
关键洞察：这条路的目标是"拿到内容"，scrapling 三层解决的是"怎么绕过反爬拿到内容"。

**路径B — web_interact（交互操作，模拟人类）：**
```
URL + Actions → PinchTab MCP API → Browser Instance → Snapshot/Text
```
关键洞察：这条路的目标是"模拟人类操作"，用于登录、点击加载、翻页等场景。

---

## 二、scrapling 三层原理详解

### HTTP tier (Fetcher)
- 用 `scrapling.fetchers.Fetcher`
- 特点：impersonation 头（伪装浏览器请求）
- 检测：状态码封锁 + body 内容封锁（Cloudflare 挑战页）

### Dynamic tier (AsyncFetcher/Playwright)
- 用 `scrapling.fetchers.AsyncFetcher`
- 特点：Playwright 驱动，完整 JS 渲染
- 检测：同上

### Stealth tier (StealthyFetcher)
- 用 `scrapling.fetchers.StealthyFetcher`
- 特点：最高隐蔽性，最慢，最可靠
- 额外处理：鼠标轨迹、随机延迟等反机器人特征

### 关键发现
scrapling 的 impersonation 能力来自 `impersonate` 库（底层用 Chrome DevTools Protocol）
- 这是与 bb-browser 完全不同的技术路线
- scrapling 是"用隐身HTTP"，bb-browser 是"用真实浏览器"

---

## 三、PinchTab 原理详解

### PinchTab 是什么
- 一个独立的浏览器自动化服务（类似 puppeteer/playwright 的远程 API）
- 提供 `browser_interact` 工具：导航、点击、填表、滚动、截图
- 通过 MCP 协议暴露工具给 AI Agent

### PinchTab vs scrapling
| | PinchTab | scrapling |
|--|---------|-----------|
| 用途 | 交互（登录/翻页/点击） | 内容抓取（读） |
| 技术 | 真实浏览器 | HTTP impersonation / 浏览器 |
| 速度 | 慢 | 快 |
| 反爬 | 最高（真实浏览器） | 中（impersonation） |
| 场景 | 需要 JS 执行 + 人类操作 | 只需获取内容 |

### 协同关系
```
research_pipeline 中：
1. 如果目标站需要登录 → web_interact 先登录 → 拿到 cookie/session
2. 登录后 → web_fetch 或 scrapling 抓内容
```
**重要洞察：PinchTab 不是 scrapling 的竞争者，是 scrapling 的前置步骤！**

---

## 四、opencli 定位

opencli 走的是**完全不同的路径**：subprocess 调用 CLI，每个站单独适配。
- 不经过 scrapling（无三层降级）
- 不经过 PinchTab（无浏览器）
- 直接发 HTTP 请求或调用站点 API

**架构中的位置：** 在 `research_pipeline._fetch_via_opencli()` 中被调用，是 scrapling 的快速替代。

---

## 五、现有问题定位

### 问题1：国内主流站抓取成功率低

**根因：** scrapling 的 HTTP tier（imperation）对付 Cloudflare 能力有限，Dynamic tier（Playwright）在某些站也被检测。

**解决方案：**
1. 在 `heuristics.py` 的 `_CN_ROUTE_DOMAINS` 基础上，对国内站优先 `dynamic` 而非 `http`
2. bb-browser 的 126 个 site adapters 封装了每个站的反爬策略，是更好的解

### 问题2：搜索结果质量差（中文）

**根因：** DuckDuckGo 中文 region (cn-tj) 无数据；query_planner 只做固定后缀叠加。

**解决方案：**
1. bb-browser 的 `baidu/search`、`bilibili/search`、`weibo/search` 等命令可替代 DuckDuckGo
2. query_planner 改为意图感知扩展

### 问题3：结构化输出能力弱

**根因：** `extractor.py` 只有通用 CSS 选择器，无领域适配。

**解决方案：**
按内容类型（article/video/social）设计提取 schema

### 问题4：PinchTab 与 scrapling 未协同

**现状：** research_pipeline 只用 opencli + scrapling，PinchTab 完全未接入。

**正确架构应该是：**
```
URL 候选
  ├─ 需要登录? → 先 PinchTab 交互 → cookie → scrapling
  ├─ 需要翻页/加载更多? → PinchTab 交互 → scrapling
  └─ 直接可抓 → scrapling 或 opencli
```

---

## 六、重构计划（有条理地分步）

### Phase 1: 架构修复（不破坏现有接口）

**Step 1.1 — 修复中文 DuckDuckGo region**
- discovery.py: `cn-tj` → `wt-wt`（cn-tj 无数据）
- 验证：中文 query 有搜索结果

**Step 1.2 — 在 research_pipeline 中接入 PinchTab**
- 新增 `_maybe_interact_for_cookies()`：检测是否需要登录
- 检测到需登录站时，先 PinchTab 操作，再 scrapling
- 不改变对外 API

**Step 1.3 — heuristics.py 完善国内站路由**
- 国内站默认 dynamic 而非 http
- 已知登录必需站标记 `LOGIN_REQUIRED`

### Phase 2: bb-browser 集成（扩展数据源）

**Step 2.1 — 新建 source_registry.py**
- 按内容类型维护高质量数据源（工具/教程/新闻/数据/社交）
- 每个源记录：URL pattern → 推荐工具
- bb-browser search commands 作为独立发现源

**Step 2.2 — discovery.py 改造**
- 同时支持多发现源：DuckDuckGo + bb-browser search + opencli search
- 按内容类型选择最优搜索源

**Step 2.3 — 新建 browser_bridge.py（在测试副本）**
- 封装 bb-browser / opencli / scrapling 三层选择逻辑
- 暂不修改原版，等验证稳定后合并

### Phase 3: 意图感知关键词

**Step 3.1 — 新建 intent_classifier.py**
- 规则判断 query 类型（informational/navigational/transactional/news）
- 不调用大模型，纯规则

**Step 3.2 — query_planner.py 改造**
- 接入 intent_classifier
- 意图感知的关键词扩展（不再只是加后缀）

### Phase 4: 结构化输出

**Step 4.1 — 新建 content_router.py**
- URL/标题→内容类型分类（article/video/social/paper）

**Step 4.2 — extractors/ 目录**
- 按内容类型的提取器

### 验证计划

| Phase | 验证 |
|-------|------|
| 1.1 | 中文 query 有搜索结果 |
| 1.2 | 需登录站测试（weibo/bilibili）|
| 1.3 | 国内站抓取成功率提升 |
| 2.1 | source_registry 覆盖主要内容类型 |
| 2.2 | bb-browser search 结果质量对比 |
| 2.3 | 端到端 pipeline 测试 |
| 3.1 | 意图分类准确性 |
| 3.2 | 关键词扩展质量 |
| 4.1+4.2 | 结构化输出完整性 |

---

## 七、现有测试副本状态

- 路径: `E:\claude_work\g\unified-web-skill-test\`
- 改动: `discovery.py`(ddgs兼容) + `browser_bridge.py`(新增) + `research_pipeline.py`(接入browser)
- 问题: `browser_bridge` 的 bb-browser URL 导航不稳定（daemon 模式 CDP fetch 失败）
- bb-browser **search commands 完美工作**（无需 URL）
- 建议：browser_bridge 中的 URL 导航回退到 scrapling，search commands 单独暴露为高效数据源
