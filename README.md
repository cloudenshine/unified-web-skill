# Unified Web Skill — 统一 Web 研究技能 v2.0

> 统一 Web 研究技能（OpenResearch Skill v2.0）— 关键词研究任务完整流水线。整合 OpenCLI（主路由）+ Scrapling+Lightpanda（批量抓取）+ PinchTab（交互）+ MCP 网关，供 OpenClaw/Agent 以 4 个 MCP 工具调用。

## 系统架构

```
[OpenClaw / Agent]
        |
        v
[MCP 网关 — app.mcp_server]        ← 统一入口
        |
  ┌─────┴──────────────────────────────┐
  │           任务路由策略              │
  └──┬──────────┬────────────┬─────────┘
     │          │            │
[OpenCLI]  [Scrapling+LP] [PinchTab]
 主路由      批量/降级      交互任务
```

## 快速启动

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 MCP 服务
python -m app.mcp_server
```

### Docker Compose

```bash
cp .env.sample .env
# 编辑 .env 填写 PinchTab 等配置
docker compose -f docker-compose.final.yml up
```

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LP_CDP_URL` | Lightpanda CDP WebSocket 地址 | `ws://lightpanda:9222` |
| `PINCHTAB_BASE_URL` | PinchTab MCP 服务地址 | 空（未启用） |
| `PINCHTAB_MCP_ENDPOINT` | PinchTab MCP 端点路径 | `/mcp` |
| `PINCHTAB_TOKEN` | PinchTab 认证 Token | 空 |
| `OPENCLI_BIN` | OpenCLI 二进制路径 | `opencli` |
| `OPENCLI_TIMEOUT_SECONDS` | OpenCLI 超时秒数 | `30` |
| `OPENCLI_ALLOWLIST_JSON` | OpenCLI 站点白名单（JSON） | bilibili/zhihu/hackernews/reddit |
| `RESEARCH_OPENCLI_ENABLED` | 是否启用 OpenCLI 主路由 | `true` |
| `RESEARCH_OPENCLI_FALLBACK` | OpenCLI 失败后降级到 Scrapling | `true` |
| `RESEARCH_PREFERRED_TOOL_ORDER` | 工具优先顺序（逗号分隔） | `opencli,scrapling` |
| `SCRAPLING_TIMEOUT` | Scrapling 请求超时秒数 | `30` |
| `MAX_PROXY_RETRIES` | 最大代理重试次数 | `3` |
| `MCP_HOST` | MCP 服务监听地址 | `0.0.0.0` |
| `MCP_PORT` | MCP 服务监听端口 | `8000` |

## MCP 工具说明

### 1. `research_and_collect` — 完整研究流水线

从关键词出发完成完整网络研究：查询扩展 → 搜索发现 → 可信度评分 → 多引擎抓取 → 内容提取 → 结构化落盘。

```json
{
  "query": "中国对外贸易政策 2026",
  "language": "zh",
  "max_sources": 30,
  "max_pages": 20,
  "trusted_mode": true,
  "output_format": "json"
}
```

### 2. `web_fetch` — 单 URL 抓取

自动路由 HTTP → Dynamic → Stealth 三级引擎，返回结构化文本和 HTML。

```json
{
  "url": "https://example.com/article",
  "task": "抓取文章正文",
  "mode": "auto",
  "prefer_text": true
}
```

### 3. `web_cli` — OpenCLI 站点命令

直接调用 OpenCLI 执行站点原生命令（bilibili/zhihu/hackernews 等）。

```json
{
  "site": "bilibili",
  "command": "hot",
  "args": []
}
```

### 4. `web_interact` — PinchTab 浏览器交互

通过 PinchTab 执行登录、点击、填表、翻页等 DOM 交互操作。

```json
{
  "url": "https://site.com/login",
  "task": "登录后获取数据",
  "actions": [
    {"kind": "fill", "ref": "e3", "value": "username"},
    {"kind": "click", "ref": "e5"}
  ]
}
```

## 运行测试

```bash
pytest -v tests/
```

## 健康检查

服务启动后访问 `http://localhost:8000/health` 确认服务状态。

## 路由策略

| 条件 | 路由目标 |
|------|----------|
| 任务含交互关键词（点击/登录/填写等） | PinchTab |
| URL 含 JS 框架特征（`__next`/`react`等） | Scrapling Dynamic |
| 其他普通 URL | Scrapling HTTP |

## 内容质量控制

- `min_text_length`：最短正文字数过滤
- `time_window_days`：时效性过滤（0 = 不过滤）
- `min_credibility`：可信度阈值（gov/edu/org 域名自动加分）
- 内容 hash 去重（SHA-1 前 16 位）

## 许可证

MIT
