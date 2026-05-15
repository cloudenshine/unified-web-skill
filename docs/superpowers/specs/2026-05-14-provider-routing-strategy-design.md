# Phase 3.1 Provider 路由策略设计

## 目的

`unified-web-skill` 的目标是成为面向 AI Agent 的全球 Web Access MCP
Router。它不应只服务中文资源，也不应把所有复杂网页都交给重型浏览器路径。
正确方向是：在能得到同等结果质量时，始终选择更轻、更快、更稳定的 provider。

`bb-browser` daemon 已经修复，这恢复了高难度站点适配器和浏览器交互能力。
但它应该是强能力补位层，而不是默认主路径。全球资源覆盖的主干仍应建立在
API、RSS、JSON、静态 HTML 和稳定结构化适配器上。

## 核心原则

同等输出质量下，provider 优先级如下：

1. 公开 API、RSS、JSON endpoint，通过轻量 HTTP 获取。
2. 静态或半静态 HTML 页面，通过 `scrapling` 获取。
3. 已有站点结构化适配器，通过 `opencli` 或 `bb-browser site` 获取。
4. 需要 JavaScript 渲染的公开页面，进入动态浏览器抓取。
5. 需要登录、cookie、点击、滚动、表单或截图的页面，进入交互式浏览器会话。
6. CAPTCHA、短信验证、强指纹封锁、付费墙等场景只记录边界，不作为默认自动化目标。

这条顺序保证默认路线低资源、高吞吐、易测试，同时保留浏览器能力处理真正困难的网页。

## Provider 分层

### 轻量 HTTP 层

首选 provider：`scrapling`

适用场景：

- 官方 API、JSON endpoint。
- RSS / Atom feed。
- 官方文档、百科、静态页面。
- 包注册表、学术元数据 API、金融公开数据。
- 简单新闻页、参考资料页。

权衡：

- 成本最低，批量验证最稳定。
- 对依赖客户端 JavaScript 或用户 session 的页面能力有限。

### 结构化 CLI 适配器层

首选 provider：同等效果下优先 `opencli`。
补位 provider：当覆盖或质量更好时使用 `bb-browser`。

适用场景：

- Hacker News、Reddit、YouTube、Bilibili、arXiv 等已有 adapter 的站点。
- 需要结构化 JSON-like 输出，而不是普通页面文本的任务。

权衡：

- 比视觉浏览器抓取更稳定、更省资源。
- adapter 命令和输出 schema 可能变化，所以必须单独验证，不能被通用 URL fetch 掩盖。

### 动态浏览器抓取层

可用 provider：`lightpanda`、Scrapling dynamic/stealth tier、`bb-browser` 通用页面打开。

适用场景：

- HTTP 返回空内容或不完整内容的 JS 页面。
- 不需要登录、不需要复杂交互，但需要渲染后的公开内容。

权衡：

- CPU、内存和超时成本高于 HTTP。
- 依赖浏览器进程、CDP 或额外 runtime，稳定性更容易受环境影响。

### 交互式会话层

可用 provider：`bb-browser`、`pinchtab` 或其他交互型 browser provider。

适用场景：

- 用户提供有效 session/cookie 后访问登录态页面。
- 点击、滚动加载、表单、截图、状态保持。
- 页面状态本身就是任务目标的浏览器自动化。

权衡：

- 本地复杂度最高，也最脆弱。
- 不应进入默认批量 verification，只能作为单独 runtime 轨道。

### 边界场景

CAPTCHA、短信校验、强指纹检测、付费订阅墙等场景应明确记录为 access
boundary。系统可以报告限制、建议官方 API 或要求用户提供合法凭证，但不应假装这些路径能稳定自治完成。

## Source Matrix 变更

`app/discovery/global_sources.json` 不再只是代表 URL 清单，而应成为 provider
路由决策矩阵。

每个 source 需要补齐：

- `access_type`: `api`、`rss`、`static_html`、`structured_adapter`、
  `dynamic_browser`、`interactive_session`、`boundary`。
- `preferred_provider`: 正常情况下成本和稳定性最优的 provider。
- `fallback_providers`: 首选 provider 不可用或质量不足时的降级链。
- `cost_tier`: `low`、`medium`、`high`。
- `stability_tier`: `stable`、`variable`、`fragile`。
- `promotion_status`: `matrix_only`、`verified_candidate`、`promoted`、`blocked`。
- `failure_modes`: 稳定枚举，例如 `timeout`、`blocked`、`auth_required`、
  `captcha`、`empty_content`、`adapter_changed`、`parser_changed`、
  `dynamic_required`、`rate_limited`。

旧字段 `difficulty`、`expected_provider`、`requires_auth` 暂时保留，用于兼容现有验证工具。新字段是后续路由决策的主依据。

## 路由规则

运行时路由后续应逐步由已验证的 source/site profile 驱动：

- `api` / `rss`: HTTP first，通常是 `scrapling`。
- `static_html`: `scrapling` first。
- `structured_adapter`: 先用已验证 adapter provider，再根据需要 fallback 到 HTTP 或 browser。
- `dynamic_browser`: 只有在 HTTP 明确不足时才进入浏览器路径。
- `interactive_session`: 必须使用支持交互的 provider，并显式记录 session/cookie 假设。
- `boundary`: 不自动晋升到默认运行时路由。

`sites.json` 只接收已经验证且有意晋升的运行时规则。Source Matrix 可以包含大量 benchmark、研究候选和边界样本，它们不必也不应全部进入运行时路由。

## 验证策略

verification 必须分轨：

- HTTP/RSS/API 批次：验证全球覆盖主干和回归稳定性。
- 结构化 adapter 批次：直接验证 `opencli` 和 `bb-browser site` 命令。
- 浏览器 runtime 批次：验证 daemon、CDP、动态渲染和交互能力。
- 边界批次：记录失败模式，不把预期边界当作产品回归。

## Phase 3.1 成功标准

- Source Matrix schema 能表达 access type、首选 provider、fallback、成本、稳定性和晋升状态。
- 测试约束所有策略字段的合法枚举，禁止未知值。
- 现有 50 个 source 已完成分类，不降低现有覆盖测试。
- 文档说明何时选择 `scrapling`、`opencli`、`bb-browser`、浏览器 provider 或边界记录。
- schema 变更后，focused tests、`check.py` 和完整 deterministic tests 仍通过。

## 执行边界

Phase 3.1 不先扩展到 100 个 source。它先分类现有 50 个 source，更新测试和中文文档，然后再继续扩展。

这样后续每新增一个全球 source，都必须同时带上路由决策、成本预期、fallback 路径和晋升状态，避免项目再次进入“资源越堆越乱”的状态。
