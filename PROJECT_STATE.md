# Project State — Unified Web Skill

> **当前版本**：v3.0.0
> **最后更新**：2026-06-17

---

## 基线

| 指标 | 数值 |
|------|------|
| 引擎 | 3（Scrapling / OpenCLI / CloakBrowser） |
| MCP 工具 | 13 |
| 已验证源 | 142（6 个回归 profile） |
| 单元测试 | 379 全部通过 |
| 研究管线 | 7 步（分类→扩展→发现→抓取→提取→评分→捆绑） |
| 凭证平台 | 浏览器提取 + YAML 加密存储 + 引擎注入 |
| Provider 路由 | SmartRouter + SiteRegistry + 断路器 |
| 文档 | README / api.md / architecture.md / engines.md / ROUTING_POLICY.md |

---

## 架构

```
AI Agent / MCP Client
  └─ app.mcp_server (13 tools)
       ├─ EngineManager
       │   ├─ Scrapling (HTTP → Dynamic → Stealth 三级)
       │   ├─ OpenCLI (100+ 站点适配器)
       │   └─ CloakBrowser (隐身 Chromium CDP)
       ├─ ResearchPipeline
       ├─ CredentialStore
       └─ SiteRegistry (142 sources)
```

---

## 已完成 Phase

| Phase | 内容 |
|-------|------|
| 引擎精简 | 6→3 引擎，删除 bb-browser/lightpanda/pinchtab/clibrowser/searxng/cloak-manager |
| 全球化源矩阵 | 142 源，6 回归 profile，8 轮迭代验证 |
| 研究管线产品化 | Bundle 输出，结构化评分，去重，引用 |
| Cookie 管理 | 浏览器提取 → YAML 加密 → 引擎注入 |
| 文档同步 | 所有文档对齐 v3 |

---

## 验证快照

```bash
pytest tests/unit/ -q --tb=short                               # 379 passed
python check.py                                                  # exit 0, 3/3 engines
python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified         # 44/44
python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified    # 42/42
python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified       # 10/10
```

---

## 下一步（按优先级）

1. **Provider 插件 SDK** — 从 3 引擎到开放生态
2. **PyPI + Docker 发布** — 降低接入门槛
3. **自适应路由** — 基于成功率的动态路由
4. **500 源全球矩阵** — 数据壁垒
5. **多租户 + 审计** — 商业化基础
