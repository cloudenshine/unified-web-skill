# Phase 3 Global Source Coverage Matrix Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the first verified structure for a global source coverage matrix without destabilizing the v3 provider router.

**Architecture:** Keep runtime routing in `SiteRegistry` and add a separate source coverage matrix under `app.discovery`. The matrix records representative source metadata, verification URLs, provider expectations, difficulty, and validation status; routing promotion remains a later explicit step.

**Tech Stack:** Python dataclasses, JSON seed file, pytest, existing `app.discovery` package.

---

## File Structure

- Create `app/discovery/source_matrix.py`: dataclasses and loader for coverage matrix entries.
- Create `app/discovery/global_sources.json`: seed matrix with representative global sources.
- Create `tests/unit/test_source_matrix.py`: matrix loading, validation, and coverage tests.
- Modify `docs/architecture.md`: document Phase 3 source matrix role.
- Modify `PLAN.md`: mark Phase 3 seed as current execution target.
- Modify `docs/superpowers/reports/2026-05-14-phase-1-2-execution-report.md`: append Phase 3 update after verification.

---

### Task 1: Source Matrix Model

**Files:**
- Create: `tests/unit/test_source_matrix.py`
- Create: `app/discovery/source_matrix.py`

- [x] **Step 1: Write failing tests**

Create tests that import `SourceMatrix`, load builtins, assert at least 20 seed sources, and require coverage across docs, code, academic, news, social, finance, commerce, search, and video.

Run: `pytest -q tests/unit/test_source_matrix.py`

Expected before implementation: fails with `ModuleNotFoundError` or missing file.

- [x] **Step 2: Implement source matrix loader**

Add `SourceEntry` and `SourceMatrix` with:

- `load_builtin()`
- `all_sources()`
- `coverage_summary()`
- `verified_sources()`
- `sources_by_category(category)`

- [x] **Step 3: Verify focused tests**

Run: `pytest -q tests/unit/test_source_matrix.py`

Expected: tests pass.

---

### Task 2: Global Seed Data

**Files:**
- Create: `app/discovery/global_sources.json`
- Modify: `tests/unit/test_source_matrix.py`

- [x] **Step 1: Add seed source data**

Create 20 representative entries across categories, regions, languages, and difficulty levels. Each entry must include:

- `source_id`
- `site_id`
- `display_name`
- `category`
- `region`
- `languages`
- `difficulty`
- `verification_url`
- `expected_provider`
- `requires_auth`
- `status`
- `notes`

- [x] **Step 2: Validate seed quality**

Tests should ensure:

- all source ids are unique;
- all verification URLs are absolute HTTPS URLs;
- all entries have status `seeded`;
- at least 8 categories are covered;
- at least 3 regions are covered.

Run: `pytest -q tests/unit/test_source_matrix.py`

Expected: pass.

---

### Task 3: Documentation

**Files:**
- Modify: `docs/architecture.md`
- Modify: `PLAN.md`

- [x] **Step 1: Document source matrix boundary**

State that the matrix is a measurement and promotion layer, not runtime routing.

- [x] **Step 2: Update roadmap status**

Mark Phase 3 seed matrix as the current active next step.

---

### Task 4: Verification

**Files:**
- No new edits unless verification exposes a defect.

- [x] **Step 1: Run diagnostics**

Run: `python check.py`

Expected: exit `0`, `3/3` default providers available.

- [x] **Step 2: Run unit tests**

Run: `pytest -q tests/unit`

Expected: all unit tests pass.

- [x] **Step 3: Run default full tests**

Run: `pytest -q`

Expected: deterministic tests pass.

- [x] **Step 4: Run live integration tests**

Run: `$env:RUN_INTEGRATION='1'; pytest -q`

Expected: live tests pass or skip dependency-limited cases.

---

### Task 5: Live Verification Capture

**Files:**
- Create: `app/discovery/source_verifier.py`
- Create: `tests/unit/test_source_verifier.py`
- Create: `verify_source_matrix.py`
- Runtime output: `outputs/source_matrix_verification_seed.json`

- [x] **Step 1: Write failing verifier tests**

Run: `pytest -q tests/unit/test_source_verifier.py`

Expected before implementation: fails because `app.discovery.source_verifier`
does not exist.

- [x] **Step 2: Implement source verifier**

Add `SourceVerificationResult`, `verify_source()`, `verify_sources()`, and
`select_sources()`.

- [x] **Step 3: Add CLI runner**

Add `verify_source_matrix.py` to run selected source ids/categories through the
current v3 `EngineManager` and save JSON results under `outputs/`.

- [x] **Step 4: Run first live capture**

Run:

```powershell
python verify_source_matrix.py --ids docs_mdn_css_grid,docs_python_asyncio,academic_arxiv_cs_ai,news_bbc_world,social_hackernews_frontpage --limit 5 --timeout 25 --output outputs\source_matrix_verification_seed.json
```

Expected: 5 results saved; public easy/medium sources should verify through
`scrapling-http`.

- [x] **Step 5: Verify after capture**

Run:

```powershell
pytest -q tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py
pytest -q
python check.py
$env:RUN_INTEGRATION='1'; pytest -q
```

---

### Task 6: Hard Source Failure-Mode Capture

**Files:**
- Runtime output: `outputs/source_matrix_verification_hard.json`
- Modify: `docs/superpowers/reports/2026-05-14-phase-1-2-execution-report.md`

- [x] **Step 1: Run browser/CDP precheck**

Run:

```powershell
node C:\Users\Admin\.agents\skills\web-access\scripts\check-deps.mjs
```

Expected: Node, Chrome, and proxy available.

- [x] **Step 2: Run high-difficulty source batch**

Run:

```powershell
python verify_source_matrix.py --ids social_reddit_programming,commerce_amazon_search,video_youtube_search,video_bilibili_search,social_zhihu_topic --limit 5 --timeout 30 --output outputs\source_matrix_verification_hard.json
```

Expected: capture pass/fail evidence for hard social/video/commerce sources.

- [x] **Step 3: Verify focused tests and diagnostics**

Run:

```powershell
pytest -q tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py
python check.py
```

Expected: focused tests pass and default providers remain healthy or accurately
degraded when a provider dependency is unavailable.

---

### Task 7: Site Adapter Verification Capture

**Files:**
- Create: `app/discovery/adapter_verifier.py`
- Create: `tests/unit/test_adapter_verifier.py`
- Create: `tests/unit/test_verify_site_adapters_cli.py`
- Create: `verify_site_adapters.py`
- Modify: `app/engines/bb_browser.py`
- Runtime output: `outputs/source_adapter_verification_hard.json`

- [x] **Step 1: Write failing adapter verifier tests**

Run:

```powershell
pytest -q tests\unit\test_adapter_verifier.py
```

Expected before implementation: fails because
`app.discovery.adapter_verifier` does not exist.

- [x] **Step 2: Implement adapter verifier**

Add `AdapterTarget`, `AdapterVerificationResult`, `verify_adapter()`, and
`verify_adapters()` for concrete `bb-browser site` adapter commands.

- [x] **Step 3: Add CLI runner**

Add `verify_site_adapters.py` to run concrete site adapters without DDGS
fallback, so adapter health is measured separately from generic URL fetch.

- [x] **Step 4: Update bb-browser community adapters**

Run:

```powershell
bb-browser site update
```

Expected: latest community adapter library installed.

- [x] **Step 5: Run hard adapter capture**

Run:

```powershell
python verify_site_adapters.py --timeout 45 --min-results 1 --output outputs\source_adapter_verification_hard.json
```

Expected: capture real adapter command evidence for `reddit/search`,
`youtube/search`, and `bilibili/search`.

- [x] **Step 6: Fix provider health diagnosis**

Add tests proving `Daemon not running` is not a healthy `bb-browser` state, then
update `BBBrowserEngine.health_check()` accordingly.

- [x] **Step 7: Verify focused tests and diagnostics**

Run:

```powershell
pytest -q tests\unit\test_adapter_verifier.py tests\unit\test_verify_site_adapters_cli.py tests\unit\test_bb_browser_command.py tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py
python check.py
```

Expected: focused tests pass; diagnostics exit `0` with the current provider
health accurately reported.

---

### Task 8: Low-Friction Global Expansion

**Files:**
- Modify: `app/discovery/global_sources.json`
- Modify: `tests/unit/test_source_matrix.py`
- Runtime output: `outputs/source_matrix_verification_expansion.json`
- Runtime output: `outputs/source_matrix_verification_expansion_supplement.json`

- [x] **Step 1: Write failing expansion tests**

Raise the built-in matrix floor from 20 to 35 sources and require at least 28
low-friction candidates where `expected_provider == "scrapling"` and difficulty
is `easy` or `medium`.

Run:

```powershell
pytest -q tests\unit\test_source_matrix.py
```

Expected before data expansion: fails because the matrix has 20 sources and 15
low-friction candidates.

- [x] **Step 2: Expand source matrix**

Add representative global sources across docs, code, academic, news, finance,
commerce, search, video, and social categories. Prefer official docs, package
registries, public APIs, RSS feeds, and simple public pages over hard dynamic
browser targets.

- [x] **Step 3: Verify matrix tests**

Run:

```powershell
pytest -q tests\unit\test_source_matrix.py
```

Expected: all source matrix tests pass.

- [x] **Step 4: Run main expansion capture**

Run:

```powershell
python verify_source_matrix.py --ids docs_react_learn,docs_typescript_handbook,docs_kubernetes_concepts,docs_django_intro,code_pypi_requests,code_npm_react,code_crates_tokio,academic_crossref_works,news_npr_world,finance_fred_gdp,finance_worldbank_gdp,finance_ecb_rates --limit 12 --timeout 25 --output outputs\source_matrix_verification_expansion.json
```

Expected: new low-friction sources verify through `scrapling-http`.

- [x] **Step 5: Replace weak/failed endpoints**

If a source is weak, failed, or hangs, replace its verification URL with a
cleaner official API/RSS endpoint where available, then rerun the affected
subset.

- [x] **Step 6: Run supplement capture**

Run:

```powershell
python verify_source_matrix.py --ids academic_doaj_search,news_guardian_world_rss,commerce_ebay_search,search_brave_python,video_vimeo_categories,social_mastodon_explore --limit 6 --timeout 20 --output outputs\source_matrix_verification_expansion_supplement.json
```

Expected: supplemental expansion sources verify.

---

### Task 9: Reach 50 Global Sources

**Files:**
- Modify: `app/discovery/global_sources.json`
- Modify: `tests/unit/test_source_matrix.py`
- Modify: `PLAN.md`
- Runtime output: `outputs/source_matrix_verification_50.json`

- [x] **Step 1: Write failing 50-source tests**

Raise the built-in matrix floor from 35 to 50 sources and require at least 40
low-friction candidates.

Run:

```powershell
pytest -q tests\unit\test_source_matrix.py
```

Expected before data expansion: fails because the matrix has 38 sources and 33
low-friction candidates.

- [x] **Step 2: Add 12 additional global sources**

Add stable entries for official documentation, package registries, scholarly
metadata APIs, RSS feeds, finance APIs, search APIs, video APIs, and federated
social APIs.

- [x] **Step 3: Verify matrix tests**

Run:

```powershell
pytest -q tests\unit\test_source_matrix.py
```

Expected: all source matrix tests pass.

- [x] **Step 4: Run 50-source expansion capture**

Run:

```powershell
python verify_source_matrix.py --ids docs_nodejs_api,docs_rust_book,code_rubygems_rails,code_packagist_laravel,academic_openalex_works,academic_europepmc_search,news_un_global_rss,news_cbc_world_rss,finance_bankofcanada_fx,search_wikipedia_api,video_peertube_instances,social_lemmy_posts --limit 12 --timeout 20 --output outputs\source_matrix_verification_50.json
```

Expected: all 12 newly added sources verify through `scrapling-http`.

- [x] **Step 5: Replace blocked or hanging endpoints**

Replace endpoints that block or hang with more stable first-party RSS/API
equivalents. In this batch, BBC RSS was replaced with UN News RSS and Bluesky
search was replaced with Lemmy public API.

---

## Self-Review

Spec coverage:

- Global source matrix: Tasks 1 and 2.
- Avoid routing instability: separate matrix from `SiteRegistry`.
- Stepwise execution: 20-source seed first, 38-source expansion second,
  50-source matrix now, later expansion to 100.
- Verification: Task 4.

No placeholders remain. All commands and files are explicit. Current hard-source
evidence showed `bb-browser site` depends on a local daemon. That daemon issue
has now been repaired separately: the stale process occupying
`127.0.0.1:19824` was removed, the daemon was restarted, and the hard adapter
verification batch for Reddit, YouTube, and Bilibili now passes. Expansion can
continue through verified HTTP/RSS/API routes while browser-adapter sources stay
on their own live-verified runtime track.
