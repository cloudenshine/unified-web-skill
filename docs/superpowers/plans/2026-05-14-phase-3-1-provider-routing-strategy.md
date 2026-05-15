# Phase 3.1 Provider Routing Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将现有 50 个全球 source 从“URL 清单”升级为可驱动路由决策的策略矩阵。

**Architecture:** 保持 `SourceMatrix` 作为测量与晋升层，不直接改变运行时 `sites.json` 路由。先扩展 `SourceEntry` schema 和测试，再给现有 50 个源补齐访问类型、首选 provider、fallback、成本、稳定性和晋升状态，最后更新中文文档。

**Tech Stack:** Python dataclasses, JSON seed matrix, pytest, existing `app.discovery` package.

---

## 文件结构

- Modify `app/discovery/source_matrix.py`: 增加策略字段与枚举常量导出。
- Modify `app/discovery/global_sources.json`: 为现有 50 个 source 补齐策略字段。
- Modify `tests/unit/test_source_matrix.py`: 添加字段有效性、provider 合法性、promotion 边界和低成本主干测试。
- Modify `docs/superpowers/specs/2026-05-14-provider-routing-strategy-design.md`: 转为中文主文档。
- Modify `docs/architecture.md`: 记录 Phase 3.1 的矩阵边界。
- Modify `docs/engines.md`: 更新 provider 选择指南。
- Modify `PLAN.md`: 更新近期执行顺序。
- Modify `docs/superpowers/reports/2026-05-14-phase-1-2-execution-report.md`: 追加 Phase 3.1 执行结果。

---

### Task 1: 策略字段测试

**Files:**
- Modify: `tests/unit/test_source_matrix.py`

- [x] **Step 1: 写失败测试**

添加测试：

```python
def test_builtin_matrix_entries_include_routing_strategy_fields():
    matrix = SourceMatrix.load_builtin()

    for source in matrix.all_sources():
        assert source.access_type in VALID_ACCESS_TYPES
        assert source.preferred_provider in VALID_PROVIDERS
        assert all(provider in VALID_PROVIDERS for provider in source.fallback_providers)
        assert source.cost_tier in VALID_COST_TIERS
        assert source.stability_tier in VALID_STABILITY_TIERS
        assert source.promotion_status in VALID_PROMOTION_STATUSES
        assert all(mode in VALID_FAILURE_MODES for mode in source.failure_modes)
```

Run: `pytest -q tests\unit\test_source_matrix.py`

Expected: FAIL because `SourceEntry` does not yet expose the new fields.

---

### Task 2: SourceEntry schema

**Files:**
- Modify: `app/discovery/source_matrix.py`

- [x] **Step 1: 实现最小 schema**

导出这些常量：

```python
VALID_ACCESS_TYPES = {"api", "rss", "static_html", "structured_adapter", "dynamic_browser", "interactive_session", "boundary"}
VALID_PROVIDERS = {"scrapling", "opencli", "bb-browser", "lightpanda", "pinchtab", "clibrowser"}
VALID_COST_TIERS = {"low", "medium", "high"}
VALID_STABILITY_TIERS = {"stable", "variable", "fragile"}
VALID_PROMOTION_STATUSES = {"matrix_only", "verified_candidate", "promoted", "blocked"}
VALID_FAILURE_MODES = {"timeout", "blocked", "auth_required", "captcha", "empty_content", "adapter_changed", "parser_changed", "dynamic_required", "rate_limited"}
```

给 `SourceEntry` 增加：

```python
access_type: str
preferred_provider: str
fallback_providers: list[str]
cost_tier: str
stability_tier: str
promotion_status: str
failure_modes: list[str]
```

- [x] **Step 2: 运行测试确认数据仍失败**

Run: `pytest -q tests\unit\test_source_matrix.py`

Expected: FAIL because JSON entries do not yet include the new fields.

---

### Task 3: 50 源策略分类

**Files:**
- Modify: `app/discovery/global_sources.json`

- [x] **Step 1: 补齐现有 50 个 source**

分类规则：

- API endpoint: `access_type="api"`, `preferred_provider="scrapling"`, `cost_tier="low"`, `stability_tier="stable"`.
- RSS feed: `access_type="rss"`, `preferred_provider="scrapling"`, `cost_tier="low"`, `stability_tier="stable"`.
- 静态文档/页面: `access_type="static_html"`, `preferred_provider="scrapling"`, `cost_tier="low"`, `stability_tier="stable"` or `variable`.
- 已验证站点适配器目标: `access_type="structured_adapter"`, provider 为 `opencli` 或 `bb-browser`。
- JS/搜索/平台页面: `access_type="dynamic_browser"`, browser provider 作为 fallback，不作为默认主干。
- 登录或强反爬目标: `access_type="interactive_session"` or `boundary`，`promotion_status="matrix_only"` or `blocked`。

- [x] **Step 2: 运行字段测试**

Run: `pytest -q tests\unit\test_source_matrix.py`

Expected: PASS.

---

### Task 4: 文档中文化与路线同步

**Files:**
- Modify: `docs/superpowers/specs/2026-05-14-provider-routing-strategy-design.md`
- Modify: `docs/architecture.md`
- Modify: `docs/engines.md`
- Modify: `PLAN.md`

- [x] **Step 1: 中文化 strategy spec**

将 spec 改为中文主文档，保留必要英文术语如 provider、source、fallback。

- [x] **Step 2: 更新架构和引擎文档**

写明：

- HTTP/API/RSS 是全球覆盖主干。
- `opencli` 优先用于同等质量的结构化适配器。
- `bb-browser` 是强能力补位和交互层，不是默认重型路径。
- 浏览器/交互 verification 单独跑。

- [x] **Step 3: 更新 roadmap**

将 Phase 3 下一步从“扩到 100”调整为“先完成 Phase 3.1 路由策略分类，再继续扩展”。

---

### Task 5: 完整验证

**Files:**
- Modify if verification exposes defects.

- [x] **Step 1: 跑 focused tests**

Run: `pytest -q tests\unit\test_source_matrix.py`

Expected: PASS.

- [x] **Step 2: 跑默认诊断**

Run: `python check.py`

Expected: exit `0`, default providers available or accurately reported.

- [x] **Step 3: 跑完整测试**

Run: `pytest -q`

Expected: deterministic tests pass.

---

### Task 6: 执行报告

**Files:**
- Modify: `docs/superpowers/reports/2026-05-14-phase-1-2-execution-report.md`

- [x] **Step 1: 追加 Phase 3.1 结果**

记录：

- 新增矩阵策略字段。
- 50 个 source 已完成路由分类。
- provider 选择策略改为轻量优先。
- 验证命令与结果。

---

## Self-Review

Spec coverage:

- Provider cost/stability strategy: Task 1, Task 2, Task 3.
- Existing 50 source classification before further expansion: Task 3.
- Chinese-first documentation: Task 4.
- Verification evidence: Task 5 and Task 6.

No placeholders remain. The plan intentionally avoids promoting all matrix
entries into `sites.json`; promotion stays explicit and verified.
