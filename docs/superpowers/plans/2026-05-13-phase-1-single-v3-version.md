# Phase 1 Single V3 Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the v2 ring implementation and leave one complete v3 MCP router version with stable diagnostics, docs, and tests.

**Architecture:** The sole runtime entry point is `python -m app.mcp_server`. The v3 `app/` package owns provider routing, health checks, fetch/search/interact/crawl/research tools, and storage. Historical v2 ring files are deleted instead of kept as compatibility paths.

**Tech Stack:** Python 3.11+, FastMCP, pytest, existing `app.engines`, `app.pipeline`, `app.discovery`, and Markdown docs.

---

## File Structure

- Create `check.py`: v3 diagnostic script for the single version.
- Create `tests/unit/test_check.py`: unit tests for diagnostic classification.
- Delete `check_v2.py` and `tests/unit/test_check_v2.py`.
- Delete `server_v2.py`.
- Delete `core/`.
- Delete historical v2 deployment artifacts: `test_deploy_v2.py`, `test_results_v2.json`.
- Modify `README.md`: remove ring model and compatibility references.
- Modify `docs/api.md`: remove v2 compatibility note.
- Modify `docs/architecture.md`: remove v2 migration note.
- Modify `requirements.txt`: rename ring comments to provider comments.
- Keep `app/` as the only implementation tree.

---

### Task 1: Introduce Single-Version Diagnostics

**Files:**
- Create: `check.py`
- Create: `tests/unit/test_check.py`
- Delete: `check_v2.py`
- Delete: `tests/unit/test_check_v2.py`

- [ ] **Step 1: Write the new diagnostic tests**

`tests/unit/test_check.py` should import `classify_smoke` from `check` and verify OK, WARN, and FAIL semantics.

- [ ] **Step 2: Run the new tests before implementation**

Run: `pytest -q tests/unit/test_check.py`

Expected before implementation: FAIL because `check.py` does not exist.

- [ ] **Step 3: Create `check.py` from the v3 engine manager**

`check.py` should import `_get_engine_manager` from `app.mcp_server`, run `health_check_all()`, report registered engines, and run a low-cost fetch/search smoke through the v3 manager.

- [ ] **Step 4: Remove old diagnostic files**

Delete `check_v2.py` and `tests/unit/test_check_v2.py`.

- [ ] **Step 5: Verify diagnostic tests and script**

Run:

```powershell
pytest -q tests/unit/test_check.py
python check.py
```

Expected: tests pass; `python check.py` exits `0` when core v3 dependencies are importable.

---

### Task 2: Delete V2 Runtime Implementation

**Files:**
- Delete: `server_v2.py`
- Delete: `core/`
- Delete: `test_deploy_v2.py`
- Delete: `test_results_v2.json`

- [ ] **Step 1: Search references before deletion**

Run:

```powershell
rg -n "server_v2|check_v2|core\\.rings|from core|Ring 0|Ring 1|Ring 2|Ring 3" . --glob "!web-access-source/**" --glob "!outputs/**"
```

- [ ] **Step 2: Delete the v2 files**

Remove the files listed above.

- [ ] **Step 3: Verify no production imports refer to v2**

Run:

```powershell
rg -n "server_v2|check_v2|core\\.rings|from core" app tests README.md docs requirements.txt
```

Expected: no results except historical notes in `docs/superpowers/` if those docs are intentionally archival.

---

### Task 3: Rewrite User-Facing Docs For One Version

**Files:**
- Modify: `README.md`
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `requirements.txt`

- [ ] **Step 1: README**

The README should say the main entry point is `python -m app.mcp_server --stdio`, diagnostics are `python check.py`, and the project has one v3 provider-router architecture.

- [ ] **Step 2: API docs**

Remove wording that v2 tool names remain available. State that v3 is the MCP API surface.

- [ ] **Step 3: Architecture docs**

Remove wording that v2 ring model is retained during migration. State that v3 EngineManager is the implementation.

- [ ] **Step 4: Requirements comments**

Replace "Ring 0" and "Ring 1" section labels with "HTTP provider", "content extraction", and "browser provider".

- [ ] **Step 5: Scan docs**

Run:

```powershell
rg -n "server_v2|check_v2|Ring 0|Ring 1|Ring 2|Ring 3|compatibility entry point|v2 compatibility" README.md docs requirements.txt
```

Expected: no active user-facing references to v2 runtime.

---

### Task 4: Phase 1 Verification

**Files:**
- No new edits unless verification exposes a defect.

- [ ] **Step 1: Unit tests**

Run: `pytest -q tests/unit`

Expected: all pass.

- [ ] **Step 2: Default full tests**

Run: `pytest -q`

Expected: deterministic tests pass; integration/e2e tests skip unless explicitly enabled.

- [ ] **Step 3: Full live tests**

Run: `$env:RUN_INTEGRATION='1'; pytest -q`

Expected: live integration/e2e tests pass or skip with explicit dependency reason.

- [ ] **Step 4: Diagnostics**

Run: `python check.py`

Expected: v3 diagnostic exits `0`, reports engine manager status, and labels optional live smoke failures as warnings.

---

## Self-Review

Spec coverage:

- Remove v2 conflict: Tasks 1, 2, 3.
- One complete version: Tasks 1, 3.
- Phase 1 reliable local MVP groundwork: Tasks 1, 4.
- Complete testing: Task 4.

No placeholders remain. All commands and files are explicit.
