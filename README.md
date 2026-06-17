# Unified Web Skill v3

**AI Agent 的本地优先 Web 接入层** — 3 引擎统一 MCP 接口，覆盖搜索、抓取、浏览器交互、结构化站点适配、研究流水线和 Cookie 凭证管理。

---

## 项目定位

这不是一个普通的网页抓取工具，而是 **AI Agent 专设的 Web 接入基础设施**：

| 能力 | 说明 |
|------|------|
| **完整研究管线** | `research_and_collect` 一站式：意图分类 → 查询扩展 → 多源发现 → 并发抓取 → 质量评分 → 结构化输出 |
| **智能引擎路由** | SmartRouter + SiteRegistry 根据域名、健康状态、断路器状态动态选择最佳引擎链 |
| **全球化源矩阵** | 142 个来源经过 8 轮迭代验证，有 `sites.json` 做元数据管理，有 `verify_source_matrix.py` 做回归 |
| **3 引擎统一接口** | Scrapling（HTTP/JS/Stealth 三层）、OpenCLI（100+ 结构化站点）、CloakBrowser（隐身 Chromium） |
| **Cookie 凭证管理** | 浏览器 Cookie 提取 → 加密存储 → 引擎注入，支持跨平台 |
| **Agent 原生设计** | 13 个 MCP 工具，工具名即语义，Agent 无需操心底层引擎 |

---

## 架构

```
AI Agent / MCP Client
  └─ app.mcp_server (13 MCP tools)
       ├─ EngineManager → 3 engines
       │   ├─ Scrapling     — HTTP/JS/Stealth 三层抓取
       │   ├─ OpenCLI       — 100+ 结构化站点适配器
       │   └─ CloakBrowser  — 隐身 Chromium（57 C++ 反检测补丁）
       ├─ ResearchPipeline  — 意图→发现→抓取→提取→质量→存储
       ├─ CredentialStore   — 加密存储 + 浏览器提取 + 引擎注入
       └─ SiteRegistry      — 142 站点元数据 + 回归验证
```

### 引擎选择逻辑

```
          ┌─ 结构化站点 (bilibili/zhihu/weibo/…)
          │    └─ OpenCLI（精确适配器）
目标 URL ─┼─ 静态/半静态网页
          │    └─ Scrapling HTTP → Dynamic → Stealth 三级降级
          └─ JS 渲染/交互需求
               └─ CloakBrowser（CDP + 隐身指纹）
```

---

## 13 MCP 工具

| # | 工具 | 用途 |
|---|------|------|
| 1 | `research_and_collect` | 完整研究管线：分类 → 发现 → 抓取 → 过滤 → 保存 |
| 2 | `web_fetch` | 单 URL 抓取，自动引擎路由和降级 |
| 3 | `web_cli` | 通过 OpenCLI 执行结构化站点命令 |
| 4 | `web_interact` | 浏览器自动化：点击、填写、滚动、截图 |
| 5 | `web_search` | 多引擎搜索和去重 |
| 6 | `web_crawl` | 从种子 URL BFS 爬取 |
| 7 | `web_profile_list` | 列出可用 CloakBrowser 配置 |
| 8 | `web_profile_use` | 切换活动 CloakBrowser 配置 |
| 9 | `engine_status` | 引擎健康和能力报告 |
| 10 | `credential_status` | 各平台凭证状态报告 |
| 11 | `credential_inject` | 从 Cookie-Editor JSON 注入 Cookie |
| 12 | `credential_extract` | 从浏览器或 Agent Reach 提取 Cookie |
| 13 | `credential_refresh` | 清除平台凭证以供重新提取 |

---

## 快速开始

### 环境要求

```bash
# Python 3.12 推荐
python -m venv .venv
pip install -r requirements.txt

# 浏览器二进制（一次性）
playwright install chromium

# 结构化站点 CLI（可选但推荐）
npm install -g @jackwener/opencli
```

### 启动

```bash
# stdio 模式（OpenClaw / Claude Code）
python -m app.mcp_server --stdio

# HTTP 模式（端口 8000）
python -m app.mcp_server
# → http://127.0.0.1:8000
```

### 验证

```bash
python check.py
python -m pytest tests/unit/ -q
```

---

## 核心优势

### 1. ResearchPipeline — 真正的杀手级特性

不是简单的搜 + 抓，而是完整管线：

```
用户查询
  └─ IntentClassifier（中文+英文意图分类）
       └─ QueryPlanner（查询扩展）
            └─ MultiSourceDiscovery（DDGS + 站点源混合发现）
                 └─ 并发抓取 + fallback 链
                      └─ ContentExtractor（正文/摘要 + 质量评分）
                           └─ Dedup（URL/标题/正文三级去重）
                                └─ Bundle（结构化输出 + stats）
```

### 2. SmartRouter + SiteRegistry — 真正的工程

不是静态"用 OpenCLI"，而是根据域名、健康状态、断路器状态、历史成功率动态选择最佳引擎链。

### 3. 全球化源矩阵

142 个来源，8 轮迭代验证，分类清晰：

- **promoted-http**（44 源）— API/RSS/静态页主干
- **promoted-structured**（42 源）— OpenCLI 结构化适配器
- **promoted-browser**（10 源）— 浏览器强依赖源
- **special-watch**（12 源）— 不稳定但有价值
- **boundary**（16 源）— 边界测试
- **rate-limited-watch**（18 源）— 限频观察

### 4. Cookie 凭证管理

```
Agent Reach / 浏览器 Cookie
  └─ CredentialExtractor（browser_cookie3 / Agent Reach 双通道）
       └─ CredentialStore（YAML 配置 + 可选 AES 加密 + 600 权限）
            └─ Engine Injection
                 ├─ OpenCLI → HTTP_COOKIE 环境变量
                 └─ CloakBrowser → CDP Cookie.set
```

---

## 平台覆盖

| 平台 | 方式 |
|------|------|
| Bilibili / 知乎 / 微博 / 小红书 / 抖音 | OpenCLI 适配器 |
| GitHub / Hacker News / Reddit / YouTube | OpenCLI 适配器 |
| arXiv / 学术检索 | Scrapling 搜索 + OpenCLI |
| 微信公众平台 | Cookie 注入 + CloakBrowser |
| 100+ 更多站点 | OpenCLI 适配器 + 持续增长 |

---

## 项目结构

```
unified-web-skill/
├── app/
│   ├── mcp_server.py        # 13 MCP 工具入口
│   ├── engines/             # 3 引擎 + 管理器 + 健康检查
│   ├── credential/          # 浏览器 Cookie 提取/加密/注入
│   ├── pipeline/            # 研究管线 + 质量评分 + 存储
│   └── discovery/           # 142 站点元数据 + 来源矩阵
├── docs/                    # 完整文档
├── tests/                   # 379 测试
├── check.py                 # 诊断检查
├── verify_source_matrix.py  # 来源矩阵回归
└── requirements.txt
```

---

## 近期路线图

### Phase 1 — Agent 完整案例评测套件
- [ ] 设计 20+ Agent 评测基准任务
- [ ] 覆盖：搜索、抓取、研究、交互、凭证、异常恢复
- [ ] 自动化评测脚本，输出评分卡

### Phase 2 — 启动自动恢复
- [ ] Windows 服务注册（自动重启 MCP 服务器）
- [ ] 引擎故障自动恢复 + 通知

### Phase 3 — 发布准备
- [ ] `pyproject.toml` + PyPI 发布
- [ ] GitHub Action CI（测试 + 回归验证）
- [ ] Docker 镜像一键部署

### Phase 4 — 能力扩展
- [ ] 更多站点适配器（持续增长 142+）
- [ ] 浏览器指纹轮换增强
- [ ] Agent Reach 凭证同步协议

---

## 变动记录

### v3.0.0 (2026-06-17)
- **3 引擎精简**：Scrapling + OpenCLI + CloakBrowser
- **已移除**：bb-browser、Lightpanda、PinchTab、CLIBrowser、SearXNG、Cloak-Manager
- **13 MCP 工具**：新增 credential 系列 + web_profile 系列
- **Cookie 凭证管理**：全新 credential 模块
- **引擎路由优化**：取消 6 引擎复杂降级链，改为 3 引擎精确路由
- **文档全面更新**：对齐当前架构
- **379 单元测试全部通过**

---

## License

MIT
