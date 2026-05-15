# Phase 2 Provider Plugin Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a provider metadata and configuration layer so local and hosted web providers can be added without expanding the MCP tool surface.

**Architecture:** Keep `app.engines.manager.EngineManager` as the router. Add declarative provider profiles for readiness, diagnostics, and later external provider registration while preserving the existing concrete engine adapters.

**Tech Stack:** Python 3.11+, dataclasses, pytest, existing `app.engines`, FastMCP diagnostics.

---

## File Structure

- Create `app/engines/provider_config.py`: built-in provider profile metadata.
- Modify `app/engines/manager.py`: keep provider profiles alongside registered engines.
- Modify `app/mcp_server.py`: expose provider profile status from `engine_status`.
- Modify `check.py`: show provider profile status in local diagnostics.
- Create `tests/unit/test_provider_config.py`: provider profile unit tests.
- Modify `tests/unit/test_engine_manager.py`: manager provider metadata tests.
- Modify `PLAN.md`: current roadmap.
- Modify `README.md`: remove stale deleted-runtime references.

---

### Task 1: Provider Profile Foundation

**Files:**
- Create: `app/engines/provider_config.py`
- Create: `tests/unit/test_provider_config.py`
- Modify: `tests/unit/test_engine_manager.py`
- Modify: `app/engines/manager.py`

- [x] **Step 1: Write failing provider profile tests**

Run: `pytest -q tests/unit/test_provider_config.py`

Expected before implementation: collection fails with `ModuleNotFoundError: No module named 'app.engines.provider_config'`.

- [x] **Step 2: Implement provider profile metadata**

Add `ProviderProfile`, `default_provider_profiles()`, and `enabled_provider_names()`.

- [x] **Step 3: Verify provider profile tests**

Run: `pytest -q tests/unit/test_provider_config.py`

Expected: `3 passed`.

- [x] **Step 4: Add EngineManager provider metadata test**

Run: `pytest -q tests/unit/test_engine_manager.py::TestEngineManagerRegistration::test_list_provider_profiles`

Expected before implementation: fails with unexpected `provider_profiles` argument.

- [x] **Step 5: Add EngineManager provider metadata support**

Store provider profiles in `EngineManager` and expose `list_provider_profiles()`.

- [x] **Step 6: Verify focused provider tests**

Run: `pytest -q tests/unit/test_provider_config.py tests/unit/test_engine_manager.py::TestEngineManagerRegistration::test_list_provider_profiles`

Expected: all focused tests pass.

---

### Task 2: Provider-Aware Diagnostics

**Files:**
- Modify: `app/mcp_server.py`
- Modify: `check.py`

- [x] **Step 1: Add provider profiles to `engine_status`**

Return `providers: em.list_provider_profiles()` alongside current `engines`.

- [x] **Step 2: Add provider profile display to `check.py`**

Print each provider name, category, enabled state, and registration state before health checks.

- [x] **Step 3: Verify diagnostics**

Run: `python check.py`

Expected: exit `0`; output includes `Provider profiles:` and no critical failures.

---

### Task 3: Project Cleanup Verification

**Files:**
- Modify: `PLAN.md`
- Modify: `README.md`
- Delete: `1000`

- [x] **Step 1: Replace obsolete roadmap**

Update `PLAN.md` so it matches the global Web Access MCP Router roadmap.

- [x] **Step 2: Remove stale deleted-runtime reference**

Update `README.md` so it no longer mentions `core/probe.py`.

- [x] **Step 3: Remove root junk file**

Delete zero-byte root file `1000`.

- [x] **Step 4: Scan for stale runtime references**

Run:

```powershell
rg -n "server_v2|check_v2|core\\.rings|from core|core/probe\\.py|Ring 0|Ring 1|Ring 2|Ring 3|ring model|compatibility entry point" README.md PLAN.md docs app tests Makefile requirements.txt test_deploy_v3.py --glob "!web-access-source/**"
```

Expected: no active runtime references.

---

### Task 4: Full Verification

**Files:**
- No new edits unless verification exposes a defect.

- [x] **Step 1: Unit tests**

Run: `pytest -q tests/unit`

Expected: all unit tests pass.

- [x] **Step 2: Default full tests**

Run: `pytest -q`

Expected: deterministic tests pass; live tests skip unless enabled.

- [x] **Step 3: Live integration tests**

Run: `$env:RUN_INTEGRATION='1'; pytest -q`

Expected: live integration/e2e tests pass or explicitly skip dependency-limited cases.

- [x] **Step 4: Deployment smoke**

Run: `python test_deploy_v3.py`

Expected: no FAIL rows; optional provider/network limitations may be WARN.

---

### Task 5: Stability and Latest Stable Tooling

**Files:**
- Modify: `app/config.py`
- Modify: `app/engines/base.py`
- Modify: `app/engines/bb_browser.py`
- Modify: `app/engines/clibrowser.py`
- Modify: `app/engines/opencli.py`
- Modify: `app/engines/scrapling_engine.py`
- Modify: `app/engines/manager.py`
- Modify: `app/mcp_server.py`
- Modify: `check.py`
- Modify: `README.md`
- Modify: `docs/api.md`
- Test: `tests/unit/test_engine_versions.py`
- Test: `tests/unit/test_bb_browser_command.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_engines_base.py`
- Test: `tests/unit/test_engine_manager.py`

- [x] **Step 1: Add provider version diagnostics with TDD**

Add `version_info()` to the engine base contract, provider status aggregation to
`EngineManager`, and version output in `check.py` / `engine_status`.

- [x] **Step 2: Upgrade active tools to latest stable versions**

Upgrade active npm CLI tools:

```powershell
npm install -g bb-browser@0.11.6 @jackwener/opencli@1.7.18
```

Upgrade and complete Python requirements:

```powershell
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade pip
python -m playwright install chromium
python -m patchright install chromium
```

- [x] **Step 3: Keep optional browser providers opt-in**

Set `LP_ENABLED=false` and `CLIBROWSER_ENABLED=false` by default. They register
only when explicitly enabled.

- [x] **Step 4: Adapt bb-browser command construction to latest stable CLI**

Plain URL fetches use `bb-browser fetch <url>`. Site adapters are used only
when a concrete command is supplied, such as `youtube/search`.

- [x] **Step 5: Re-run full verification**

Verified with:

```powershell
python check.py
pytest -q tests\unit
pytest -q
$env:RUN_INTEGRATION='1'; pytest -q
python test_deploy_v3.py
```
