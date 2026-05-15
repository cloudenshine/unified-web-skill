# Phase 1/2 Execution Report

Date: 2026-05-14
Workspace: `E:\claude_work\g\unified-web-skill`

## Goal

Converge the project into one clean v3 implementation, keep the default runtime
stable, upgrade active execution tools to their latest stable versions, and lay
the foundation for a provider plugin layer without expanding the MCP tool
surface.

## Completed Work

### Single Runtime Cleanup

- Removed historical v2 runtime files and duplicate deployment artifacts.
- Kept `python -m app.mcp_server --stdio` as the single MCP runtime entry point.
- Added `python check.py` as the single local diagnostic entry point.
- Rewrote `PLAN.md` around the global Web Access MCP Router direction.
- Updated README/API docs to describe the single v3 router and provider-aware
  diagnostics.

### Provider Plugin Layer Foundation

- Added `app/engines/provider_config.py` with declarative provider profiles.
- Added provider metadata storage and `provider_status()` to `EngineManager`.
- Added provider version diagnostics through `BaseEngine.version_info()`.
- Added version checks for:
  - `bb-browser`
  - `opencli`
  - `clibrowser`
  - `scrapling`
- Exposed provider status and version state through `engine_status`.
- Updated `check.py` to show provider enabled/registered/version state.

### Stability Defaults

- Default enabled providers are now the stable local baseline:
  - `bb-browser`
  - `opencli`
  - `scrapling`
- Optional browser/session providers now require explicit opt-in:
  - `LP_ENABLED=true`
  - `CLIBROWSER_ENABLED=true`
  - `PINCHTAB_BASE_URL=...`
- This avoids registering unavailable browser services or missing binaries in a
  clean default install.

### Latest Stable Tooling

Upgraded active CLI tools:

- `bb-browser`: `0.11.2` -> `0.11.6`
- `opencli`: `1.6.8` -> `1.7.18`

Upgraded/completed Python tooling and dependencies:

- `pip==26.1.1`
- `mcp==1.27.1`
- `ddgs==9.14.2`
- `trafilatura==2.0.0`
- `playwright==1.59.0`
- `patchright==1.59.1`
- `scrapling==0.4.8`
- `pydantic==2.13.4`
- `fastapi==0.136.1`
- `uvicorn==0.46.0`

Installed matching Chromium binaries for Playwright and Patchright.

### Latest bb-browser Compatibility

- Added `_build_fetch_command()` so latest `bb-browser` command construction is
  explicit and tested.
- Plain URL fetches use `bb-browser fetch <url>`.
- Site adapters are used only for concrete commands, for example
  `youtube/search`, avoiding invalid plain-platform adapters such as `youtube`.

## Tests Added

- `tests/unit/test_provider_config.py`
- `tests/unit/test_engine_versions.py`
- `tests/unit/test_bb_browser_command.py`
- Added provider status tests to `tests/unit/test_engine_manager.py`.
- Added version helper tests to `tests/unit/test_engines_base.py`.
- Added optional-provider default tests to `tests/unit/test_config.py`.

## Verification Evidence

Latest completed verification:

- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - Provider versions reported:
    - `bb-browser 0.11.6`
    - `opencli 1.7.18`
    - `scrapling 0.4.8`
- `pytest -q tests\unit`
  - `331 passed, 2 warnings`
- `pytest -q`
  - `331 passed, 34 skipped`
- `$env:RUN_INTEGRATION='1'; pytest -q`
  - `364 passed, 1 skipped, 17 warnings`
- `python test_deploy_v3.py`
  - `TOTAL: 31 | PASS: 27 | FAIL: 0 | WARN: 4 | SKIP: 0`

## Residual Warnings

- `bb-browser fetch` warns when the daemon does not start in time. The
  site-search path works, and `scrapling` fallback keeps default fetch/research
  operational.
- `opencli_fetch` warns for `https://httpbin.org/html` because that domain is
  intentionally unsupported by OpenCLI.
- MCP HTTP health warns when no HTTP server is running; the supported default
  entry point remains stdio.
- Some pytest warnings come from Windows asyncio subprocess cleanup and an
  upstream `lxml` deprecation warning.

## Current Outcome

The project now has one documented runtime, a cleaner default provider set,
provider-aware diagnostics with local versions, latest stable active CLI/Python
tooling, and a verified test baseline ready for the next phase.

## Phase 3 Update: Global Source Coverage Matrix Seed

Added the first coverage-matrix slice:

- `app/discovery/source_matrix.py`
- `app/discovery/global_sources.json`
- `tests/unit/test_source_matrix.py`

The seed matrix contains 20 representative global sources across:

- docs
- code
- academic
- news
- social
- finance
- commerce
- search
- video

The matrix is intentionally separate from `SiteRegistry`. It is a measurement
and verification layer; only verified rules should later be promoted into
`app/discovery/sites.json`.

Latest Phase 3 verification:

- `python check.py`
  - Exit `0`
  - `3/3` default providers available
- `pytest -q tests\unit`
  - `336 passed, 2 warnings`
- `pytest -q`
  - `336 passed, 34 skipped, 2 warnings`
- `$env:RUN_INTEGRATION='1'; pytest -q`
  - `369 passed, 1 skipped, 26 warnings`

Current next execution step: add live verification capture for a small subset of
the 20 seed sources, record success/failure metadata, then expand toward 50
representative sources.

## Phase 3 Update: First Live Verification Capture

Added live source verification tooling:

- `app/discovery/source_verifier.py`
- `tests/unit/test_source_verifier.py`
- `verify_source_matrix.py`

First live capture:

- Output: `outputs/source_matrix_verification_seed.json`
- Sources verified: 5
- Verified: 5
- Weak: 0
- Failed: 0
- Provider observed: `scrapling-http`

Verified source ids:

- `docs_mdn_css_grid`
- `docs_python_asyncio`
- `academic_arxiv_cs_ai`
- `news_bbc_world`
- `social_hackernews_frontpage`

Latest verification after adding live capture:

- `pytest -q tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py`
  - `11 passed`
- `pytest -q`
  - `342 passed, 34 skipped, 2 warnings`
- `python check.py`
  - Exit `0`
  - `3/3` default providers available
- `$env:RUN_INTEGRATION='1'; pytest -q`
  - `375 passed, 1 skipped, 23 warnings`

Current next execution step: run a second verification batch that includes hard
sources (`reddit`, `amazon`, `youtube`, `bilibili`, `zhihu`) to characterize
failure modes before promoting or expanding rules.

## Phase 3 Update: Hard Source Failure-Mode Capture

Ran the second live verification batch:

- Output: `outputs/source_matrix_verification_hard.json`
- Sources tested: 5
- Verified: 2
- Weak: 0
- Failed: 3

Verified:

- `commerce_amazon_search`
  - Provider observed: `scrapling-http`
  - Text length: 22395
- `video_bilibili_search`
  - Provider observed: `scrapling-http`
  - Text length: 4327

Failed:

- `social_reddit_programming`
  - Error: `All engines exhausted. Last error: blocked`
- `video_youtube_search`
  - Error: `All engines exhausted. Last error: blocked`
- `social_zhihu_topic`
  - Error: `All engines exhausted. Last error: blocked`

Observed failure pattern:

- `bb-browser` is registered and current (`0.11.6`) but generic browser fetch
  depends on its daemon path, which timed out during this batch.
- `opencli` does not support these generic URL fetches, and in the Reddit path
  also emitted local adapter validation warnings from `~/.opencli`.
- `scrapling` fallback reached the pages in several cases but classified
  Reddit, YouTube, and Zhihu as blocked after tier fallback.

Latest focused verification:

- `pytest -q tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py`
  - `11 passed`
- `python check.py`
  - Exit `0`
  - `3/3` default providers available

Current next execution step: improve hard-source routing evidence by testing
site-adapter commands where available (`youtube/search`, `bilibili/search`,
`reddit/search`) separately from generic URL fetch, and decide whether
`expected_provider` should distinguish `bb-browser site adapter` from
`bb-browser generic fetch`.

## Phase 3 Update: Site Adapter Verification Capture

Added concrete site-adapter verification tooling:

- `app/discovery/adapter_verifier.py`
- `tests/unit/test_adapter_verifier.py`
- `tests/unit/test_verify_site_adapters_cli.py`
- `verify_site_adapters.py`

This runner calls `bb-browser site <adapter> <query> --json` directly and does
not allow the normal DDGS fallback to hide adapter-level failures.

Updated external adapter state:

- Ran `bb-browser site update`
- Installed community adapter count reported by bb-browser: 141

Site adapter capture:

- Output: `outputs/source_adapter_verification_hard.json`
- Adapters tested: 3
- Verified: 0
- Weak: 0
- Failed: 3

Failed adapters:

- `reddit/search`
- `youtube/search`
- `bilibili/search`

Uniform failure:

```text
bb-browser: Daemon did not start in time.
Chrome CDP is reachable, but the daemon process failed to initialize.
Try: bb-browser daemon status
```

Additional checks:

- `bb-browser site info reddit/search --json`: adapter exists and signature is
  valid.
- `bb-browser site info youtube/search --json`: adapter exists and signature is
  valid.
- `bb-browser site info bilibili/search --json`: adapter exists and signature is
  valid.
- `bb-browser site arxiv/search ... --json` and `bb-browser site bbc/news ...`
  also failed with the same daemon error, confirming this is a local daemon
  dependency failure rather than a single-site block.

Provider health correction:

- Added tests that `Daemon not running` must not count as healthy.
- Updated `BBBrowserEngine.health_check()` and `_daemon_available()` to avoid
  reporting `bb-browser` as available when the daemon is down.

Latest focused verification:

- `pytest -q tests\unit\test_adapter_verifier.py tests\unit\test_verify_site_adapters_cli.py tests\unit\test_bb_browser_command.py tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py`
  - `24 passed`
- `python check.py`
  - Exit `0`
  - `2/3` registered engines available
  - `bb-browser` accurately marked degraded by health monitor
  - `scrapling` fetch smoke passed
  - search smoke passed with 2 results
- `pytest -q`
  - `353 passed, 34 skipped`

Current execution conclusion:

- Generic public-source verification is viable through `scrapling-http`.
- Hard social/video sites should not be promoted based on generic URL fetch.
- `bb-browser site` adapters are structurally present and current, but blocked
  by the local daemon startup path in this environment.
- Phase 3 expansion should proceed by adding more global sources with
  verifiable HTTP/RSS/API/search paths first, while treating `bb-browser daemon`
  repair as a separate provider-runtime task.

## Phase 3 Update: Low-Friction Global Expansion

Expanded the source matrix from 20 to 38 representative global sources while
keeping it separate from runtime routing.

Test guardrails added:

- Built-in matrix must contain at least 35 sources.
- Matrix must contain at least 28 low-friction candidates where
  `expected_provider == "scrapling"` and difficulty is `easy` or `medium`.

New coverage includes:

- React, TypeScript, Kubernetes, and Django documentation.
- PyPI, npm, and crates.io package data.
- Crossref and DOAJ academic sources.
- Guardian and NPR RSS news feeds.
- FRED, World Bank, and ECB finance sources.
- eBay, Brave Search, Vimeo, and Mastodon public endpoints.

Main expansion capture:

- Output: `outputs/source_matrix_verification_expansion.json`
- Sources tested: 12
- Verified: 12
- Weak: 0
- Failed: 0
- Provider observed: `scrapling-http`

Supplement expansion capture:

- Output: `outputs/source_matrix_verification_expansion_supplement.json`
- Sources tested: 6
- Verified: 6
- Weak: 0
- Failed: 0
- Provider observed: `scrapling-http`

Endpoint replacements made during verification:

- `code_crates_tokio`: switched from the crates.io HTML page to
  `https://crates.io/api/v1/crates/tokio`.
- `news_npr_world`: switched from NPR section HTML to
  `https://feeds.npr.org/1004/rss.xml`.
- `news_ap_top`: replaced with Guardian world RSS because AP homepage caused
  batch timeout.
- `social_mastodon_explore`: switched from Mastodon explore HTML to
  `https://mastodon.social/api/v1/trends/statuses`.

Current Phase 3 status:

- Total built-in matrix sources: 38
- Newly added sources in this step: 18
- Newly live-verified sources in this step: 18/18
- Latest focused verification:
  - `25 passed`
- Latest default full test:
  - `354 passed, 34 skipped, 2 warnings`
- Latest diagnostics:
  - `python check.py` exit `0`
  - `2/3` registered engines available
  - `bb-browser` remains accurately degraded due to daemon startup failure
  - `scrapling` fetch smoke passed
  - search smoke passed with 2 results
- Next clean expansion target: 50 sources, preserving API/RSS/static-page
  preference for baseline coverage and keeping hard browser-adapter sources in
  a separate runtime track.

## Phase 3 Update: 50-Source Matrix Milestone

Expanded the source matrix from 38 to 50 representative global sources.

Test guardrails updated:

- Built-in matrix must contain at least 50 sources.
- Matrix must contain at least 40 low-friction candidates where
  `expected_provider == "scrapling"` and difficulty is `easy` or `medium`.

New coverage added:

- Node.js and Rust official documentation.
- RubyGems and Packagist package metadata.
- OpenAlex and Europe PMC academic APIs.
- UN News and CBC public RSS feeds.
- Bank of Canada Valet finance API.
- Wikipedia search API.
- PeerTube instance API.
- Lemmy public forum API.

50-source expansion capture:

- Output: `outputs/source_matrix_verification_50.json`
- Sources tested: 12
- Verified: 12
- Weak: 0
- Failed: 0
- Provider observed: `scrapling-http`

Endpoint replacements made during verification:

- `news_bbc_world_rss`: replaced with `news_un_global_rss` because the BBC RSS
  endpoint hung in the current fetch pipeline.
- `social_bluesky_search`: replaced with `social_lemmy_posts` because Bluesky
  returned 403 to the current fetch path.

Current Phase 3 status:

- Total built-in matrix sources: 50
- Newly added sources in this step: 12
- Newly live-verified sources in this step: 12/12
- Latest focused verification:
  - `25 passed`
- Latest default full test:
  - `354 passed, 34 skipped, 2 warnings`
- Latest diagnostics:
  - `python check.py` exit `0`
  - `2/3` registered engines available
  - `bb-browser` remains accurately degraded due to daemon startup failure
  - `scrapling` fetch smoke passed
  - search smoke passed with 2 results
- Clean next target: expand from 50 toward 100 sources while keeping hard
  browser-adapter sources isolated until the `bb-browser` daemon issue is fixed.

## Provider Runtime Repair: bb-browser Daemon

Root cause:

- A stale Node process was still listening on `127.0.0.1:19824` and returned
  `401 Unauthorized`.
- `C:\Users\Admin\.bb-browser\daemon.json` was missing, so the local
  `bb-browser` CLI reported the daemon as not running but could not initialize a
  replacement process on the occupied port.

Repair performed:

- Stopped the stale port owner process.
- Restarted `bb-browser daemon`; it regenerated `daemon.json` and came up with
  CDP connected.
- Confirmed `bb-browser daemon status --json` and `bb-browser status --json`
  both report `running: true` and `cdpConnected: true`.

Verifier compatibility fix:

- Updated `verify_site_adapters.py` so `_items_from_json()` understands the
  latest `bb-browser site` success envelope:
  `{"success": true, "data": {"videos"|"posts"|"papers": [...]}}`.
- Added unit coverage for `videos`, `posts`, and `papers` envelopes.

Post-repair verification:

- `python check.py`: exit `0`, engine health `3/3 available`.
- Focused unit tests:
  `13 passed`.
- Hard adapter live verification:
  - Output: `outputs/source_adapter_verification_after_daemon_fix.json`
  - Total: 3
  - Verified: 3
  - Failed: 0
  - Adapters: `reddit/search`, `youtube/search`, `bilibili/search`

Current provider-runtime status:

- `bb-browser` is no longer degraded in this environment.
- Browser-adapter sources can be tested again, but should remain on a separate
  live-verification track from low-friction HTTP/RSS/API sources.

## Phase 3.1 Update: Provider Routing Strategy Classification

执行目标：

- 将现有 50 个全球 source 从“代表 URL 清单”升级为 provider 路由决策矩阵。
- 文档主语言调整为中文，保留必要英文术语如 provider、source、fallback。
- 暂停盲目扩展 source 数量，先明确哪些网页类型适合哪些 provider。

新增/更新的策略字段：

- `access_type`
- `preferred_provider`
- `fallback_providers`
- `cost_tier`
- `stability_tier`
- `promotion_status`
- `failure_modes`

当前 50-source 策略分布：

- `access_type`
  - `static_html`: 22
  - `api`: 11
  - `rss`: 4
  - `structured_adapter`: 4
  - `dynamic_browser`: 7
  - `interactive_session`: 1
  - `boundary`: 1
- `preferred_provider`
  - `scrapling`: 44
  - `bb-browser`: 5
  - `opencli`: 1
- `cost_tier`
  - `low`: 37
  - `medium`: 11
  - `high`: 2
- `promotion_status`
  - `verified_candidate`: 38
  - `matrix_only`: 11
  - `blocked`: 1

策略结论：

- 全球覆盖主干是 API/RSS/静态 HTML，首选 `scrapling`。
- 同等结构化质量下，`opencli` 优先于 `bb-browser`，因为资源占用更小且无
  daemon 依赖。
- `bb-browser` 保留给结构化 adapter 覆盖更好、需要动态浏览器或需要交互会话的场景。
- `dynamic_browser`、`interactive_session` 和 `boundary` source 不自动晋升到
  `sites.json`。

文档更新：

- `docs/superpowers/specs/2026-05-14-provider-routing-strategy-design.md`
  改为中文主文档。
- `docs/superpowers/plans/2026-05-14-phase-3-1-provider-routing-strategy.md`
  记录完整执行计划。
- `docs/architecture.md` 补充 SourceMatrix 与 SiteRegistry 的边界。
- `docs/engines.md` 更新引擎选择指南。
- `README.md` 更新推荐工具搭配。
- `PLAN.md` 将近期顺序调整为先完成 Phase 3.1，再继续从 50 扩到 100。

最新验证：

- `pytest -q tests\unit\test_source_matrix.py`
  - `9 passed`
- `pytest -q tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py`
  - `15 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - Provider versions:
    - `bb-browser 0.11.6`
    - `opencli 1.7.18`
    - `scrapling 0.4.8`
- `pytest -q`
  - `360 passed, 34 skipped, 2 warnings`

当前下一步：

- 基于 Phase 3.1 schema 继续扩展到 75/100 个全球 source。
- 每个新增 source 必须同时携带 access type、首选 provider、fallback、成本、
  稳定性和晋升状态。
- 浏览器 adapter 与 HTTP/RSS/API 继续分轨验证，避免重型 provider 污染默认批量路径。

## Phase 3.2 Update: 75-Source Clean Expansion

执行目标：

- 在 Phase 3.1 路由策略 schema 基础上，从 50 个 source 扩展到 75 个。
- 新增源优先选择 API、RSS 和官方静态文档，保持全球覆盖主干轻量稳定。
- 删除明确临时调试脚本，避免项目根目录继续堆积一次性排障文件。

清理动作：

- 删除 `debug_fetch.py`
- 删除 `debug_pipeline.py`
- 删除 `trace_fetch.py`
- 删除 `run_research.py`
- 删除 `show_results.py`

新增覆盖类型：

- 官方文档：Go、PHP、PostgreSQL、PyTorch、pandas、Keras。
- 包/代码注册表：Maven Central、NuGet、Docker Hub、Anaconda。
- 学术 API：DataCite、ClinicalTrials.gov、bioRxiv。
- 新闻 RSS：Al Jazeera、Deutsche Welle、France 24、ABC News。
- 金融 API：US Treasury FiscalData、Frankfurter、Open Exchange Rates。
- 商业/商品 API：Open Food Facts、iTunes Search。
- 搜索/档案 API：Internet Archive。
- 视频 API：Dailymotion。
- 社区 API：Stack Exchange。

首轮 25-source live verification：

- Output: `outputs/source_matrix_verification_75.json`
- Total: 25
- Verified: 20
- Failed: 5

失败并替换的源：

- `docs_tensorflow_tutorials` -> `docs_keras_getting_started`
- `academic_semantic_scholar_search` -> `academic_biorxiv_recent`
- `finance_imf_exchange_rates` -> `finance_frankfurter_rates`
- `finance_nasdaq_data_link_docs` -> `finance_open_exchange_rates_status`
- `commerce_mercadolibre_search` -> `commerce_itunes_search`

替换源 live verification：

- Output: `outputs/source_matrix_verification_75_replacements.json`
- Total: 5
- Verified: 5
- Failed: 0

当前 75-source 策略分布：

- `access_type`
  - `static_html`: 28
  - `api`: 26
  - `rss`: 8
  - `structured_adapter`: 4
  - `dynamic_browser`: 7
  - `interactive_session`: 1
  - `boundary`: 1
- `preferred_provider`
  - `scrapling`: 69
  - `bb-browser`: 5
  - `opencli`: 1
- `cost_tier`
  - `low`: 62
  - `medium`: 11
  - `high`: 2
- `promotion_status`
  - `verified_candidate`: 63
  - `matrix_only`: 11
  - `blocked`: 1

策略结论：

- 75-source 矩阵仍保持轻量主干：API/RSS/静态 HTML 合计 62 个低成本源。
- 失败、限流、OAuth redirect 或 blocked 的 endpoint 没有保留在矩阵中，已替换为更稳定的公开 API/文档源。
- `bb-browser` 仍只承担 5 个高能力 source 的首选路径，避免 daemon/browser 成本污染默认批量路线。

## Phase 3.3 Update: Project Hygiene Pass

执行目标：

- 继续推进“只保留一个完整版本”的代码库收口。
- 删除固定查询、固定输出路径、一次性排障用途的根目录脚本。
- 清理生成结果和缓存，避免后续执行时混淆正式入口与临时工具。

清理动作：

- 删除未跟踪临时脚本：
  - `call_research.py`
  - `call_research_stdio.py`
  - `direct_research.py`
  - `inspect_records.py`
  - `run_http.py`
  - `test_fetch.py`
- 删除已跟踪但过期的一次性调用脚本：
  - `research_call.py`
- 删除已跟踪生成结果：
  - `test_results_v3.json`
- 删除临时输出：
  - `outputs/subagent_result.json`
- 删除 Python 测试缓存：
  - root `__pycache__`
  - `app/**/__pycache__`
  - `tests/**/__pycache__`

保留原则：

- 保留正式诊断入口 `check.py`。
- 保留正式验证 CLI：
  - `verify_source_matrix.py`
  - `verify_site_adapters.py`
- 保留 `test_deploy_v3.py`，因为 Phase 2 文档仍把它作为部署级 smoke 验证脚本引用。
- 不批量删除 `outputs/` 历史研究结果；该目录已被 `.gitignore` 排除，且其中可能包含用户历史数据。
- `.pytest_cache` 当前为空目录，但 Windows ACL 拒绝删除；不为缓存目录强行改权限，避免引入无关风险。

## Phase 3.4 Update: Low-Friction Source Promotion

执行目标：

- 将已验证、低成本、免登录的 API/RSS/静态 HTML source 从
  `global_sources.json` 晋升到正式运行时站点规则 `sites.json`。
- 保持浏览器、交互会话、边界站点继续分轨验证，不让高成本 provider 污染默认
  HTTP/RSS/API 主干。
- 新增 `PROJECT_STATE.md`，作为后续低 token 继续执行的项目状态锚点。

晋升范围：

- 新增晋升站点：52 个。
- `sites.json` 站点数量：67 -> 119。
- `global_sources.json` 中对应 source 的 `promotion_status`：
  `verified_candidate` -> `promoted`。

晋升原则：

- 只晋升尚未在 `sites.json` 中注册的 source。
- 只晋升 `access_type` 为 `api`、`rss`、`static_html` 的 source。
- 只晋升 `preferred_provider == "scrapling"`、`cost_tier == "low"`、
  `requires_auth == false` 的 source。
- 不晋升 `dynamic_browser`、`interactive_session`、`boundary` source。

测试 guardrail：

- `tests/unit/test_site_registry.py` 要求内置站点数至少 100。
- 已晋升 source 必须能通过 `SiteRegistry` 找到。
- 已晋升 source 的首选 engine 必须与矩阵中的 `preferred_provider` 一致。
- 已晋升 source 必须保持免登录，并使用 `default_fetch_mode == "http"`。

当前已完成的 focused verification：

- `pytest -q tests\unit\test_site_registry.py tests\unit\test_source_matrix.py`
  - `35 passed`

完成前验证：

- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - Provider versions:
    - `bb-browser 0.11.6`
    - `opencli 1.7.18`
    - `scrapling 0.4.8`
  - `sites.json` loaded sites: 119
- `pytest -q`
  - `361 passed, 34 skipped, 2 warnings`

当前结论：

- Phase 3.4 的低摩擦来源晋升已完成。
- 默认运行时站点规则现在覆盖 119 个站点。
- 高成本动态浏览器、交互会话和边界站点仍未自动晋升，下一步应单独执行
  browser-adapter verification。

## Phase 3.5 Update: Browser Adapter Verification

执行目标：

- 在 `bb-browser` daemon 修复后，单独验证 hard browser-adapter 路线。
- 保持 browser adapter 与 HTTP/RSS/API 晋升分轨，避免混淆低成本抓取路径和
  高能力结构化 adapter 路径。
- 将已验证结构化 adapter 的矩阵状态与运行时站点路由对齐。

daemon 状态：

- `bb-browser daemon status --json`
  - `running: true`
  - `cdpConnected: true`
- `bb-browser status --json`
  - `running: true`
  - `cdpConnected: true`

live adapter verification：

- `python verify_site_adapters.py --output outputs\source_adapter_verification_phase_3_5_hard.json --timeout 60 --min-results 1`
  - Total: 3
  - Verified: 3
  - Failed: 0
  - Adapters: `reddit/search`, `youtube/search`, `bilibili/search`
- `python verify_site_adapters.py --target arxiv/search:"machine learning" --output outputs\source_adapter_verification_phase_3_5_arxiv.json --timeout 60 --min-results 1`
  - Total: 1
  - Verified: 1
  - Failed: 0
  - Adapter: `arxiv/search`

路由与矩阵调整：

- 将 4 个已验证 `structured_adapter` source 标记为 `promoted`：
  - `academic_arxiv_cs_ai`
  - `social_reddit_programming`
  - `video_youtube_search`
  - `video_bilibili_search`
- 修正 `youtube` 站点 runtime routing：
  - `engines`: `["bb-browser", "opencli", "scrapling"]`
- `dynamic_browser`、`interactive_session`、`boundary` source 仍未自动晋升。

focused verification：

- `pytest -q tests\unit\test_site_registry.py tests\unit\test_source_matrix.py tests\unit\test_adapter_verifier.py tests\unit\test_verify_site_adapters_cli.py`
  - `48 passed`

完成前验证：

- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 119
- `pytest -q`
  - `362 passed, 34 skipped, 2 warnings`

当前结论：

- Phase 3.5 的 browser-adapter 分轨验证已完成。
- 当前矩阵晋升分布：
  - `promoted`: 57
  - `verified_candidate`: 9
  - `matrix_only`: 8
  - `blocked`: 1
- 高成本 `dynamic_browser`、`interactive_session`、`boundary` source 仍保持
  `matrix_only` 或 `blocked`，未自动晋升。

## Phase 3.6 Update: Verified-Candidate Backlog Closure

执行目标：

- 处理剩余 9 个 `verified_candidate`，避免矩阵中继续保留含义模糊的中间状态。
- 已经存在正式 `sites.json` 规则的基线站点直接标记为 `promoted`。
- 保持运行时路由的既有 provider 顺序，不为了矩阵状态强制覆盖成熟站点路由。

处理结果：

- 9 个剩余 `verified_candidate` 均已归档为 `promoted`：
  - `code_github_fastapi`
  - `code_stackoverflow_python_asyncio`
  - `news_reuters_world`
  - `news_bbc_world`
  - `social_hackernews_frontpage`
  - `docs_wikipedia_ai`
  - `code_pypi_requests`
  - `code_npm_react`
  - `social_mastodon_explore`

测试 guardrail：

- `tests/unit/test_source_matrix.py` 新增约束：内置矩阵不应残留
  `verified_candidate`。
- `tests/unit/test_site_registry.py` 调整为：已晋升低摩擦 source 的
  `preferred_provider` 必须存在于站点 engine 列表中，但不强制排第一，以保留
  GitHub、npm、PyPI 等旧基线站点已有的 `opencli` 优先路由。

focused verification：

- `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py`
  - `37 passed`

完成前验证：

- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 119
- `pytest -q`
  - `363 passed, 34 skipped, 2 warnings`

当前矩阵晋升分布：

- `promoted`: 66
- `matrix_only`: 8
- `blocked`: 1
- `verified_candidate`: 0

## Phase 3.7 Update: 100-Source Expansion

执行目标：

- 从 75 个代表性 source 扩展到 100 个。
- 新增 source 从一开始携带完整 routing strategy metadata。
- 继续优先 API/RSS/官方静态文档，保持默认路径轻量、稳定、低资源占用。
- 新增 source 必须完成 live verification；弱结果或失败 endpoint 不保留。

新增覆盖：

- 官方文档：Vite、FastAPI、Flask、SQLAlchemy、Ansible、Terraform。
- 代码/包生态：Hex.pm、Hackage、pkg.go.dev、MetaCPAN。
- 学术 API：NASA NTRS、PLOS、arXiv API。
- 新闻 RSS：NASA、WHO、ScienceDaily、ESA。
- 金融 API：CoinGecko、Kraken、BLS。
- 搜索/API：Wikidata、Common Crawl、Open Library。
- 视频/媒体 API：Wikimedia Commons。
- 社区 API：Discourse Meta。

首轮 25-source live verification：

- Output: `outputs/source_matrix_verification_100.json`
- Total: 25
- Verified: 22
- Weak: 2
- Failed: 1

替换与修正：

- `finance_stooq_aapl_csv` -> `finance_coincap_assets`
  - 原因：CSV 输出过短，低于抽取质量阈值。
- `search_datagov_packages` -> `search_openlibrary_books`
  - 原因：Data.gov API path 在当前抓取路径返回 404。
- `video_vimeo_oembed` -> `video_wikimedia_commons_search`
  - 原因：Vimeo oEmbed URL 返回 404/弱输出。
- `finance_coincap_assets` -> `finance_kraken_ticker`
  - 原因：CoinCap 在当前 TLS/CDP 路径失败。

最终 25-source live verification：

- Output: `outputs/source_matrix_verification_100_final.json`
- Total: 25
- Verified: 25
- Weak: 0
- Failed: 0

晋升结果：

- 新增 source：25 个。
- 新增 runtime site rules：25 个。
- `sites.json` 站点数量：119 -> 144。

当前 100-source 策略分布：

- `access_type`
  - `api`: 39
  - `static_html`: 36
  - `rss`: 12
  - `structured_adapter`: 4
  - `dynamic_browser`: 7
  - `interactive_session`: 1
  - `boundary`: 1
- `preferred_provider`
  - `scrapling`: 94
  - `bb-browser`: 5
  - `opencli`: 1
- `cost_tier`
  - `low`: 87
  - `medium`: 11
  - `high`: 2
- `promotion_status`
  - `promoted`: 91
  - `matrix_only`: 8
  - `blocked`: 1

focused verification：

- `pytest -q tests\unit\test_source_matrix.py`
  - `10 passed`
- `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py`
  - `37 passed`

完成前验证：

- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - `363 passed, 34 skipped`

当前结论：

- Phase 3.7 的 100-source 扩展已完成。
- 当前默认 runtime 站点规则覆盖 144 个站点。
- 轻量主干仍占主导：API/RSS/静态 HTML 合计 87 个低成本 source。

## Phase 4.1 Update: Research Bundle Baseline

执行目标：

- 开始 Phase 4 research-bundle productization。
- 在不破坏 `research_and_collect` 旧响应字段的前提下，新增结构化 `bundle`。
- 先实现可测试的最小闭环：accepted/rejected records、provider traces、failure
  stats 和确定性基础评分。

新增代码：

- `app/pipeline/bundle.py`
  - `ResearchBundleBuilder`
  - URL canonicalization：去掉 `utm_*`、`fbclid`、`gclid` 等跟踪参数。
  - accepted/rejected 分组：当前先按 canonical URL 去重。
  - provider trace：记录每条 accepted record 的 fetch engine、fetch mode、
    duration 和 tool chain。
  - failure stats：汇总 skipped quality、duplicate、blocked。
  - baseline score：综合 credibility、content length、published date、provider
    trace 是否存在。
- `app/mcp_server.py`
  - 新增 `_research_response_payload()`。
  - `research_and_collect` 返回中新增 `bundle` 字段。
  - 保留旧字段：`records`、`stats`、`queries_used`、`output_files`。

测试：

- `tests/unit/test_research_bundle.py`
  - 验证 canonical URL 去重与 rejected record。
  - 验证基础评分排序。
  - 验证 provider traces 与 failure stats。
- `tests/unit/test_mcp_research_response.py`
  - 验证 MCP research response 同时包含旧字段和新 `bundle`。

focused verification：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py`
  - `4 passed`

完成前验证：

- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - `367 passed, 34 skipped, 2 warnings`

当前结论：

- Phase 4.1 的 research bundle baseline 已接入 `research_and_collect`。
- 旧响应字段保持兼容，新响应额外提供 `bundle`，用于后续 ranking、
  deduplication、freshness 和 credibility scoring 增强。

## Phase 4.2 Update: Bundle Freshness and Citations

执行目标：

- 在 Phase 4.1 的 bundle baseline 上继续产品化 scoring。
- 让 freshness 评分不再只是“有日期即加分”，而是按发布时间新旧衰减。
- 输出可直接供回答层使用的 ranked citations，减少后续调用方再拼装引用字段。

新增能力：

- `ResearchBundleBuilder(now=...)`
  - 支持注入当前时间，保证测试和 benchmark 可复现。
- freshness score
  - 30 天内：`0.1`
  - 365 天内：`0.07`
  - 3 年内：`0.04`
  - 更旧：`0.01`
  - 无效或缺失日期：`0.0`
- `bundle["citations"]`
  - 跟随 accepted records 的排序。
  - 包含 title、url、canonical_url、published_at、provider、score、summary。

TDD 证据：

- 先新增失败测试：
  - 近期来源应排在同等条件的陈旧来源之前。
  - bundle 顶层应暴露 ranked citations。
- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`2 failed, 3 passed`
  - 失败原因：`ResearchBundleBuilder()` 尚不支持 `now` 参数，且无 citations 行为。
- GREEN：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`5 passed`

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py`
  - 结果：`6 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`369 passed, 34 skipped, 2 warnings`
- 测试后已清理可访问的 `__pycache__`；`.pytest_cache` 仍受 Windows ACL 限制，
  未强行改权限。

当前结论：

- Phase 4.2 的 freshness 与 citation 基础能力已经落地。
- 下一步应继续 credibility calibration：按 source type、官方域名、结构化
  adapter、已知低可信域名等维度细化可信度，而不是扩大无关代码面。

## Phase 4.3 Update: Bundle Credibility Calibration

执行目标：

- 在 Phase 4.2 的 freshness/citation 基础上继续增强 bundle scoring。
- 先做可解释、保守、低维护成本的可信度校准，不引入外部服务或大模型判断。
- 保持评分结构可测试、可复现，方便下一步建立 regression benchmark。

新增能力：

- credibility calibration 纳入原有 credibility 权重内部，避免总分无上限膨胀。
- `score_breakdown["credibility_calibration"]` 暴露校准贡献。
- 当前校准来源：
  - 权威域名后缀：`.gov`、`.edu`、`.mil`、`.int`
  - `source_type == "site_adapter"`
  - `fetch_mode` 以 `api` 或 `rss` 开头
- 单条记录校准上限为 `0.12`，最终 credibility 仍不超过 `1.0`。

TDD 证据：

- 先新增失败测试：
  - 同等内容长度、发布时间、provider 和基础 credibility 下，权威域名应排在普通域名前。
  - breakdown 应显式给出 `credibility_calibration`。
- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 5 passed`
  - 失败原因：当前评分只使用原始 `record.credibility`，不做域名/来源校准。
- GREEN：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`6 passed`

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py`
  - 结果：`7 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`370 passed, 34 skipped`

当前结论：

- Phase 4.3 已完成可信度校准的第一层确定性规则。
- 下一步应进入 regression benchmark fixtures：用固定输入验证排序、去重、
  citations 和 score breakdown 长期稳定。

## Phase 4.4 Update: Research Bundle Regression Benchmark

执行目标：

- 在 Phase 4.1 到 4.3 的 scoring、deduplication、citations 基础上增加长期回归样例。
- 用固定输入和固定 expected output 保护 bundle 行为，避免后续优化时无意改变排序、
  canonical 去重、引用顺序、score breakdown 或 stats。
- 先加入一个小而完整的全球政策研究样例，不引入运行时依赖或外部网络调用。

新增文件：

- `tests/unit/test_research_bundle_benchmarks.py`
  - 从 fixture 构造 `ResearchResult`。
  - 使用固定 `now` 调用 `ResearchBundleBuilder`。
  - 断言 accepted canonical order、rejected records、citation order、
    score breakdowns 和 stats。
- `tests/unit/fixtures/research_bundle_benchmarks/global_policy_research.json`
  - 覆盖权威 `.gov` API 来源、结构化 adapter 学术来源、陈旧普通来源和
    tracking 参数 canonical duplicate。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`1 failed`
  - 失败原因：`global_policy_research.json` fixture 尚不存在。
- GREEN：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`1 passed`

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`8 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`371 passed, 34 skipped, 2 warnings`
- 测试后已清理可访问的 `__pycache__`；`.pytest_cache` 仍不强行处理。

当前结论：

- Phase 4.4 已建立第一条 research bundle 回归 benchmark。
- 下一步可以继续增加 academic、package/code、news 三类 fixture；如果 fixture
  数量继续增长，再考虑增加轻量 benchmark summary CLI。

## Phase 4.5 Update: Expanded Bundle Benchmark Fixtures

执行目标：

- 继续扩展 Phase 4.4 的 fixed-output benchmark。
- 覆盖三类高频全球研究任务：academic literature、package/code、news。
- 保持 benchmark 仍运行在 unit test 中，不引入外部网络调用或运行时新入口。

新增/更新文件：

- `tests/unit/test_research_bundle_benchmarks.py`
  - 改为参数化测试。
  - 统一验证 4 个 fixture 的 accepted canonical order、rejected records、
    citation order、score breakdowns 和 stats。
- 新增 fixture：
  - `academic_literature_research.json`
  - `package_code_research.json`
  - `news_research.json`

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`3 failed, 1 passed`
  - 失败原因：academic、package/code、news 三个 fixture 尚不存在。
- GREEN：
  - 新增三个 fixture 后第一次运行：`1 failed, 3 passed`
  - 失败原因：package/code fixture 的 expected order 与当前确定性评分规则不一致。
  - 修正 expected order 后：
    `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`4 passed`

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`11 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`374 passed, 34 skipped, 2 warnings`
- 测试后已清理可访问的 `__pycache__`；`.pytest_cache` 仍不强行处理。

当前结论：

- Phase 4.5 已把 bundle 回归 benchmark 扩展到 4 个固定样例。
- 当前 benchmark 覆盖 global policy、academic、package/code、news 四类任务；
  后续如继续增加样例，可再判断是否需要轻量 benchmark summary helper。

## Phase 4.6 Update: Bundle Score Summary

执行目标：

- 继续做小范围 bundle behavior hardening。
- 在不破坏旧字段的前提下，让调用方可以快速读取 accepted records 的分数分布。
- 将新增统计也纳入 fixed-output benchmark，避免后续评分调整时无意漂移。

新增能力：

- `bundle["stats"]["score_summary"]`
  - `count`
  - `max`
  - `min`
  - `avg`
- 空 accepted records 时返回：
  - `{"count": 0, "max": 0.0, "min": 0.0, "avg": 0.0}`

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 6 passed`
  - 失败原因：`bundle["stats"]` 尚无 `score_summary`。
- GREEN：
  - 实现 `_score_summary()` 后：
    `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`7 passed`
- Benchmark 固化：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`4 failed`
  - 失败原因：4 个 fixture 的 expected stats 尚未包含 `score_summary`。
  - 更新 fixture 后：
    `pytest -q tests\unit\test_research_bundle.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`11 passed`

当前结论：

- Phase 4.6 已为 bundle stats 增加 score distribution summary。
- `score_summary` 已被直接单元测试和 4 个 benchmark fixture 同时覆盖。

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`12 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`375 passed, 34 skipped, 2 warnings`
- 测试后已清理可访问的 `__pycache__`；`.pytest_cache` 仍不强行处理。

## Phase 4.7 Update: Score Quality Buckets

执行目标：

- 继续增强 bundle stats 的调用方可观测性。
- 在 `score_summary` 中增加质量分档，不改变已有 score、排序或旧响应字段。
- 将分档纳入 benchmark fixture，确保后续评分规则调整时能看到质量分布变化。

新增能力：

- `bundle["stats"]["score_summary"]["quality_buckets"]`
  - `high`: score `>= 0.8`
  - `medium`: `0.6 <= score < 0.8`
  - `low`: score `< 0.6`
- 空 accepted records 时返回：
  - `{"high": 0, "medium": 0, "low": 0}`

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 6 passed`
  - 失败原因：`score_summary` 尚无 `quality_buckets`。
- GREEN：
  - 实现 quality bucket 统计后：
    `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`7 passed`
- Benchmark 固化：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`4 failed`
  - 失败原因：4 个 fixture 的 expected stats 尚未包含 `quality_buckets`。
  - 更新 fixture 后：
    `pytest -q tests\unit\test_research_bundle.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`11 passed`

当前结论：

- Phase 4.7 已为 `score_summary` 增加 high/medium/low 质量分档。
- 该行为由直接单元测试、MCP 兼容测试和 4 个 benchmark fixture 覆盖。

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`12 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`375 passed, 34 skipped`
- 测试后已清理可访问的 `__pycache__`；`.pytest_cache` 仍不强行处理。

## Phase 4.8 Update: Rejection Reason Stats

执行目标：

- 继续做小范围 bundle behavior hardening。
- 让调用方可以直接读取 rejected records 的原因分布，减少自行扫描明细记录的重复工作。
- 不改变 accepted records、score、排序、citations、legacy MCP response fields。

新增能力：

- `bundle["stats"]["rejection_reasons"]`
  - 当前覆盖：`{"duplicate_url": 1}` 等按 rejected record `reason` 聚合的计数。
  - 若未来出现其他拒绝原因，可自动按 reason 分组。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 6 passed`
  - 失败原因：`bundle["stats"]` 尚无 `rejection_reasons`。
- GREEN：
  - 实现 `_rejection_reason_counts()` 并接入 bundle stats 后：
    `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`7 passed`
- Benchmark 固化：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`4 failed`
  - 失败原因：4 个 fixture 的 expected stats 尚未包含 `rejection_reasons`。
  - 更新 fixture 后：
    `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`12 passed`

当前结论：

- Phase 4.8 已为 bundle stats 增加 rejected-record reason distribution。
- 该行为由直接单元测试、MCP 兼容测试和 4 个 benchmark fixture 覆盖。

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`12 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`375 passed, 34 skipped, 2 warnings`
- full pytest 的 2 条 warning 来自 Windows asyncio/subprocess transport
  cleanup，属于当前既有测试环境 warning；本次改动未新增相关异步路径。

## Phase 4.9 Update: Language Distribution Stats

执行目标：

- 继续做小范围 bundle behavior hardening。
- 面向全球资源目标，让调用方可以直接查看 accepted records 的语言分布。
- 不改变 accepted records、score、排序、citations、provider traces 或 legacy MCP
  response fields。

新增能力：

- `bundle["stats"]["language_distribution"]`
  - 按 accepted record 的 `language` 聚合计数。
  - 空语言值归入 `unknown`。
  - 当前 benchmark fixture 固定为：`{"en": 3}`。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 7 passed`
  - 失败原因：`bundle["stats"]` 尚无 `language_distribution`。
- GREEN：
  - 实现 `_language_distribution()` 并接入 bundle stats 后：
    `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`8 passed`
- Benchmark 固化：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`4 failed`
  - 失败原因：4 个 fixture 的 expected stats 尚未包含 `language_distribution`。
  - 更新 fixture 后：
    `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`13 passed`

当前结论：

- Phase 4.9 已为 bundle stats 增加 accepted-record language distribution。
- 该行为由直接单元测试、MCP 兼容测试和 4 个 benchmark fixture 覆盖。

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`13 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
- `pytest -q`
  - 结果：`376 passed, 34 skipped`

## Phase 4.10 Update: Provider/Source Distribution and Bundle Schema

执行目标：

- 继续收尾 Phase 4 的 bundle 产品化。
- 增加 accepted records 的 provider/source-type 分布，帮助调用方判断结果来自
  轻量 HTTP、CLI、结构化适配器或其他路径的比例。
- 在中文 API 文档中明确 `bundle` schema，使新增字段成为可交付接口契约。

新增能力：

- `bundle["stats"]["provider_distribution"]`
  - 按 accepted record 的实际 `fetch_engine` 聚合计数。
  - 空 provider 归入 `unknown`。
- `bundle["stats"]["source_type_distribution"]`
  - 按 accepted record 的 `source_type` 聚合计数。
  - 空 source type 归入 `unknown`。
- `docs/api.md`
  - 新增 `Research Bundle Schema` 小节。
  - 明确 `accepted_records`、`rejected_records`、`provider_traces`、`citations`
    和各类 stats 字段的含义。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 8 passed`
  - 失败原因：`bundle["stats"]` 尚无 `provider_distribution`。
- GREEN：
  - 实现通用 `_distribution()`，接入 `provider_distribution` 和
    `source_type_distribution` 后：
    `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`9 passed`
- Benchmark 固化：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`4 failed`
  - 失败原因：4 个 fixture 的 expected stats 尚未包含 provider/source-type
    distribution。
  - 更新 fixture 后：
    `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`14 passed`

当前结论：

- Phase 4.10 已补齐 provider/source-type observability。
- bundle schema 已在中文 API 文档中固化。
- 本次没有改变旧响应字段，也没有把内部 source type 元数据加入
  `accepted_records` 结构。

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`14 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
  - live httpbin smoke 前两次 transient timeout，重试后成功。
- `pytest -q`
  - 结果：`377 passed, 34 skipped`

## Phase 3.8 Update: 分批验证工具与低成本 Provider 刷新

执行目标：

- 回到 Phase 3，按 access type 和 provider path 分开做 live verification。
- 避免低成本 HTTP/RSS/API 批次被 browser/CLI fallback 混入，保证验证证据可解释。
- 本轮只处理验证工具与第一批低成本 scrapling 路径，不直接删除或降级源。

新增能力：

- `select_sources()` 支持按 `access_types`、`promotion_statuses`、
  `cost_tiers`、`preferred_providers` 过滤，保留原有 `ids/categories`
  选择能力。
- `verify_source_matrix.py` 增加对应 CLI 参数：
  `--access-types`、`--promotion-statuses`、`--cost-tiers`、
  `--preferred-providers`。
- `EngineManager.fetch_with_fallback()` 和 `SmartRouter.resolve_fetch_order()`
  增加 `allow_fallback_engines`，默认 `True`，保持现有运行时行为不变。
- `verify_source_matrix.py --strict-preferred-provider` 在严格验证时直接调用
  指定 provider，避免同一批次中 EngineManager 的 fallback 和 circuit state
  污染结果。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_source_verifier.py`
  - 初始结果：`1 failed, 6 passed`
  - 失败原因：`select_sources()` 尚不接受 strategy filter 参数。
- GREEN：
  - 增加选择器过滤参数后：
    `pytest -q tests\unit\test_source_verifier.py`
  - 结果：`7 passed`
- RED：
  - `pytest -q tests\unit\test_engine_manager.py -k "implicit_fallback or disable_implicit"`
  - 初始结果：`2 failed`
  - 失败原因：路由器和 fetch 管理层仍会追加隐式 fallback。
- GREEN：
  - 增加 `allow_fallback_engines` 后：
    `pytest -q tests\unit\test_engine_manager.py -k "implicit_fallback or disable_implicit"`
  - 结果：`2 passed, 27 deselected`
- RED：
  - `pytest -q tests\unit\test_verify_source_matrix_cli.py`
  - 初始结果：import error，脚本尚无 `_fetch_matrix_url()`。
- GREEN：
  - 严格 provider helper 接入后：
    `pytest -q tests\unit\test_verify_source_matrix_cli.py`
  - 结果：`2 passed`

Live verification：

- 非严格低成本批次：
  - 命令：
    `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --cost-tiers low --preferred-providers scrapling --limit 20 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_low_cost.json`
  - 结果：`20 total, 17 verified, 0 weak, 3 failed`
  - 观察：scrapling 熔断后混入 bb-browser/opencli fallback，因此该结果不适合作为
    低成本 provider path 的纯净证据。
- 初版严格模式：
  - 结果：`20 total, 2 verified, 0 weak, 18 failed`
  - 观察：仍受 EngineManager circuit state 影响。
- 修正后的严格 provider 模式：
  - 命令：
    `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --cost-tiers low --preferred-providers scrapling --strict-preferred-provider --limit 20 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_low_cost_strict_provider.json`
  - 结果：`20 total, 15 verified, 0 weak, 5 failed`
  - 严格 scrapling 失败项：
    `code_github_fastapi`、`code_stackoverflow_python_asyncio`、
    `academic_pubmed_search`、`news_reuters_world`、`docs_wikipedia_ai`。

当前结论：

- Phase 3.8 已建立可解释的分批验证入口。
- 首批低成本源整体仍可用，但 5 个严格 scrapling 失败项需要后续分类：
  其中多项返回了足量正文但 provider 标记 `blocked`，不应根据单次 live run
  直接删除。

完成前验证：

- `pytest -q tests\unit\test_source_verifier.py tests\unit\test_engine_manager.py tests\unit\test_verify_source_matrix_cli.py`
  - 结果：`38 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
  - httpbin fetch smoke 通过：`scrapling-http`
- `pytest -q`
  - 结果：`382 passed, 34 skipped, 2 warnings`
  - 警告：Windows asyncio subprocess/pipe transport 的资源释放警告，测试结果仍为
    exit `0`。

## Phase 3.8 Update: 失败源分类与 Provider 路径调整

执行目标：

- 分类首批 strict scrapling 失败的 5 个 promoted 源。
- 区分 provider 阻断误判、真实 scrapling 不适配、以及需要 browser provider 的站点。
- 只调整已通过 live follow-up 的源，避免根据一次失败直接删除源。

处理结果：

- `github/fastapi`、`pubmed`、`wikipedia`
  - 问题：长正文页面中出现 `captcha` / `access denied` 相关配置或文本，导致
    `_is_blocked()` 误判为 blocked。
  - 调整：长页面只保留强阻断标记 `ip has been blocked` 和
    `challenge-running`；短挑战页仍识别 captcha/access denied。
  - 结果：继续保持 scrapling 主路径。
- `stackoverflow`、`reuters`
  - 问题：strict scrapling 分别返回 403/401，短正文，属于真实 provider 不适配。
  - follow-up：`bb-browser` 对两者均 live verified。
  - 调整：在 `global_sources.json` 中改为 `expected_provider/preferred_provider`
    = `bb-browser`，`cost_tier` = `medium`，fallback 为 `scrapling`、`opencli`；
    在 `sites.json` 中改为 browser-first engines。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_scrapling_engine.py`
  - 初始结果：长正文包含 `access denied` 时误判 blocked。
- GREEN：
  - 收紧长页面 block markers 后：
    `pytest -q tests\unit\test_scrapling_engine.py`
  - 结果：`6 passed`
- RED：
  - `pytest -q tests\unit\test_source_matrix.py -k browser_provider_path`
  - `pytest -q tests\unit\test_site_registry.py -k browser_verified_static_sources`
  - 初始结果：矩阵和站点注册仍指向 scrapling/opencli 路径。
- GREEN：
  - 调整两个源和两个站点后：
    `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py`
  - 结果：`39 passed`

Live verification：

- 失败源策略复测：
  - 命令：
    `python verify_source_matrix.py --ids code_github_fastapi,code_stackoverflow_python_asyncio,academic_pubmed_search,news_reuters_world,docs_wikipedia_ai --strict-preferred-provider --limit 5 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_failure_recheck_after_strategy.json`
  - 结果：`5 total, 5 verified, 0 weak, 0 failed`
- 低成本 scrapling 批次复测：
  - 命令：
    `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --cost-tiers low --preferred-providers scrapling --strict-preferred-provider --limit 20 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_low_cost_after_strategy.json`
  - 结果：`20 total, 20 verified, 0 weak, 0 failed`

完成前验证：

- `pytest -q tests\unit\test_scrapling_engine.py tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py tests\unit\test_engine_manager.py`
  - 结果：`83 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
  - httpbin fetch smoke 通过：`scrapling-http`
- `pytest -q`
  - 结果：`390 passed, 34 skipped, 2 warnings`
  - 警告：Windows asyncio subprocess/pipe transport 的资源释放警告，测试结果仍为
    exit `0`。

## Phase 3.8 Final Sweep and Closeout

执行目标：

- 对 promoted HTTP/RSS/API、structured adapter、browser-first 路径做最终分批
  live verification。
- 保持 strict preferred-provider 模式，确认每个 promoted 源的首选 provider 路径
  自身可用。
- 对最终失败项只做证据驱动调整，不扩大范围。

Live verification：

- Promoted HTTP/RSS/API：
  `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --strict-preferred-provider --limit 100 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_promoted_http_rss_api_final.json`
  - 结果：`87 total, 87 verified, 0 weak, 0 failed`
- Promoted structured adapters 初始复核：
  `python verify_source_matrix.py --access-types structured_adapter --promotion-statuses promoted --strict-preferred-provider --limit 20 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_structured_promoted_final.json`
  - 结果：`4 total, 3 verified, 0 weak, 1 failed`
  - 失败项：`academic_arxiv_cs_ai`
  - 原因：本地 `opencli` adapter loader 失败，错误来自无关 CLI module
    declaration 校验；不是 arXiv 页面不可访问。
- arXiv provider probe：
  - `bb-browser`：通过，`text_length` 约 `96334`
  - `scrapling`：通过，`text_length` 约 `20462`
  - `opencli`：失败，本地 adapter loader 错误
- 调整：
  - `academic_arxiv_cs_ai` 从 `opencli` first 改为 `bb-browser` first。
  - `opencli` 保留为 fallback，避免删除未来可恢复路径。
  - `app/discovery/sites.json` 中 `arxiv` runtime engines 同步为 browser-first。
- Promoted structured adapters 最终复核：
  `python verify_source_matrix.py --access-types structured_adapter --promotion-statuses promoted --strict-preferred-provider --limit 20 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_structured_promoted_after_strategy.json`
  - 结果：`4 total, 4 verified, 0 weak, 0 failed`

TDD evidence：

- RED：
  - `pytest -q tests\unit\test_source_matrix.py -k arxiv_structured`
  - `pytest -q tests\unit\test_site_registry.py -k arxiv_browser`
  - 两个测试均先失败，确认当前配置仍是 `opencli` first。
- GREEN：
  - `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py`
  - 结果：`44 passed`

当前 Phase 3.8 收尾状态：

- Promoted sources：`91`，已通过 strict provider 分批验证。
- Matrix-only sources：`8`，其中 dynamic/interactive/boundary 源保持隔离。
- Blocked sources：`1`，仅 `commerce_producthunt`。
- 当前基线不再保留 ambiguous `verified_candidate`。

完成前验证：

- `pytest -q tests\unit\test_scrapling_engine.py tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py tests\unit\test_engine_manager.py tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`102 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: `144`
  - fetch smoke 通过：`scrapling-http`
  - search smoke 返回 `2` results
- `pytest -q`
  - 结果：`395 passed, 34 skipped`

## Phase 3.8 Update: Matrix-only Dynamic and Boundary Batch

执行目标：

- 验证 matrix-only 的 dynamic/browser 与 interactive entries。
- 将 blocked/boundary 源单独处理，不混入 promoted 批次。
- 对弱项或失败项只做有证据的 provider/path 分类。

Live verification：

- 初始 matrix-only dynamic/interactive 批次：
  - 命令：
    `python verify_source_matrix.py --access-types dynamic_browser,interactive_session --promotion-statuses matrix_only --strict-preferred-provider --limit 20 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_matrix_only_dynamic_browser.json`
  - 结果：`8 total, 6 verified, 1 weak, 1 failed`
  - 弱项：`search_duckduckgo_python`，strict scrapling 仅 `141` 字符。
  - 失败项：`commerce_producthunt`，strict scrapling `403 blocked`。
- 替代 provider 探测：
  - DuckDuckGo：`bb-browser` verified，约 `23k` 文本；改为 browser-first。
  - ProductHunt：`scrapling`、`bb-browser`、`opencli` 均失败；改为 `blocked`。
- 策略后 matrix-only dynamic/interactive 批次：
  - 命令：
    `python verify_source_matrix.py --access-types dynamic_browser,interactive_session --promotion-statuses matrix_only --strict-preferred-provider --limit 20 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_matrix_only_dynamic_after_strategy.json`
  - 结果：`7 total, 7 verified, 0 weak, 0 failed`
- Boundary 单独批次：
  - 命令：
    `python verify_source_matrix.py --access-types boundary --promotion-statuses matrix_only --strict-preferred-provider --limit 5 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_boundary_matrix_only.json`
  - 结果：`1 total, 1 verified, 0 weak, 0 failed`
  - `commerce_amazon_search` 通过 strict `bb-browser`，但仍保持 `matrix_only`，
    因为它是 high-cost boundary source。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_source_matrix.py -k matrix_only_dynamic_refresh_classification`
  - 初始结果：DuckDuckGo 仍是 scrapling，ProductHunt 未 blocked。
- RED：
  - `pytest -q tests\unit\test_site_registry.py -k duckduckgo_browser`
  - 初始结果：DuckDuckGo registry 未 browser-first。
- GREEN：
  - 调整 DuckDuckGo/ProductHunt 后：
    `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py`
  - 结果：`42 passed`
- Boundary RED/GREEN：
  - 新增 Amazon boundary 隔离测试后先失败，改为 `matrix_only` 后通过。

当前结论：

- Matrix-only dynamic/interactive 当前干净：7/7 verified。
- Boundary 当前干净但隔离：Amazon 1/1 verified，仍不 promoted。
- 当前唯一 blocked source：`commerce_producthunt`。

完成前验证：

- `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py`
  - 结果：`51 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
  - httpbin fetch smoke 通过：`scrapling-http`
- `pytest -q`
  - 结果：`393 passed, 34 skipped, 2 warnings`
  - 警告：Windows asyncio subprocess/pipe transport 的资源释放警告，测试结果仍为
    exit `0`。

## Phase 3.8 Update: Promoted Browser Runtime Batch

执行目标：

- 验证所有 promoted 且 browser-first 的源。
- 重点确认刚从 scrapling 迁移到 `bb-browser` 的 `stackoverflow` 和
  `reuters` 在同一 browser runtime batch 中稳定。
- 保持严格 provider 验证，避免其他 provider fallback 掩盖 daemon/runtime 问题。

Live verification：

- 命令：
  `python verify_source_matrix.py --preferred-providers bb-browser --promotion-statuses promoted --strict-preferred-provider --limit 10 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_browser_promoted.json`
- 结果：`5 total, 5 verified, 0 weak, 0 failed`
- 通过源：
  `code_stackoverflow_python_asyncio`、`news_reuters_world`、
  `social_reddit_programming`、`video_youtube_search`、
  `video_bilibili_search`

当前结论：

- promoted browser-first 路径当前干净。
- `stackoverflow` 与 `reuters` 从 scrapling 转为 browser-first 的调整得到同批次
  live evidence 支撑。
- 下一步应继续处理 matrix-only dynamic/browser 与 boundary 条目，blocked/auth
  required 源继续保持单独批次，不混入 promoted 验证。

完成前验证：

- `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py`
  - 结果：`48 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: 144
  - httpbin fetch smoke 通过：`scrapling-http`
- `pytest -q`
  - 结果：`390 passed, 34 skipped, 2 warnings`
  - 警告：Windows asyncio subprocess/pipe transport 的资源释放警告，测试结果仍为
    exit `0`。

## Phase 4.11 Update: Source Matrix Periodic Regression Profiles

执行目标：

- 继续 Phase 4 产品化，但本轮聚焦长期稳定性而不是扩大运行时复杂度。
- 将 Phase 3.8 已验证的 source matrix 分批验证参数固化为可重复 profile。
- 为 ProductHunt/Amazon 等特殊源建立 evidence watch 路径：记录证据，但不因单次
  通过或失败自动改变晋升等级。

新增能力：

- `verify_source_matrix.py --regression-profile <name>`
  - `promoted-http`：promoted API/RSS/static HTML，strict provider，默认 100 条。
  - `promoted-structured`：promoted structured adapter，strict provider。
  - `promoted-browser`：promoted browser-first，strict `bb-browser`。
  - `boundary-watch`：boundary + matrix_only evidence capture。
  - `special-watch`：当前 ProductHunt/Amazon 特殊源 evidence capture。
- `verify_source_matrix.py --fail-on-unverified`
  - 当 selected sources 出现 weak/failed 时返回 exit `1`。
  - 默认不启用，保留 historical/live evidence capture 的宽松行为。
- `Makefile`
  - `make source-matrix-regression`
  - `make source-matrix-watch`
- `README.md` 与 `docs/architecture.md`
  - 补充周期性 source matrix regression 使用方式和边界策略。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_verify_source_matrix_cli.py`
  - 初始结果：import error，`_build_parser` / `_resolve_regression_profile` /
    `_exit_code_for_summary` 尚不存在。
- GREEN：
  - 实现 parser helper、profile resolution 和 fail-on-unverified 退出码后：
    `pytest -q tests\unit\test_verify_source_matrix_cli.py`
  - 结果：`6 passed`

Live/profile verification：

- Focused regression-profile tests：
  `pytest -q tests\unit\test_verify_source_matrix_cli.py tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py`
  - 结果：`27 passed`
- Promoted structured：
  `python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified --output outputs\source_matrix_regression_promoted_structured_latest.json`
  - 结果：`4 total, 4 verified, 0 weak, 0 failed`
- Promoted browser：
  `python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified --output outputs\source_matrix_regression_promoted_browser_latest.json`
  - 结果：`6 total, 6 verified, 0 weak, 0 failed`
- Promoted HTTP/RSS/API：
  `python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified --output outputs\source_matrix_regression_promoted_http_latest.json`
  - 结果：`87 total, 87 verified, 0 weak, 0 failed`
- Boundary watch：
  `python verify_source_matrix.py --regression-profile boundary-watch --output outputs\source_matrix_regression_boundary_watch_latest.json`
  - 结果：`1 total, 1 verified, 0 weak, 0 failed`
- Special watch：
  `python verify_source_matrix.py --regression-profile special-watch --timeout 45 --min-text-length 200 --output outputs\source_matrix_regression_special_watch_latest.json`
  - 结果：`2 total, 1 verified, 0 weak, 1 failed`
  - Amazon：`bb-browser` verified，继续保持 high-cost boundary `matrix_only`。
  - ProductHunt：`scrapling-stealth` 返回 `403 blocked`，继续保持 `blocked`。

当前结论：

- 周期性 promoted source matrix regression 已有稳定入口。
- ProductHunt/Amazon 的后续策略从“人工判断”收敛为可重复 evidence watch。
- 本轮没有提升 ProductHunt 或 Amazon 的等级，也没有改变运行时路由的 promoted
  边界。

完成前验证：

- `pytest -q tests\unit\test_verify_source_matrix_cli.py tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`41 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: `144`
  - fetch smoke 通过：`scrapling-http`
  - search smoke 返回 `2` results
- `pytest -q`
  - 结果：`399 passed, 34 skipped, 2 warnings`
  - 警告：Windows asyncio subprocess/pipe transport 的资源释放警告，测试结果仍为
    exit `0`。

## Phase 4.12 Update: Bundle Domain Distribution

执行目标：

- 继续增强 research bundle 的调用方可观测性。
- 增加 accepted records 的 canonical domain 分布，帮助调用方快速判断结果是否被
  单一域名垄断。
- 保持旧字段兼容，不改变 ranking、deduplication 或 provider routing。

新增能力：

- `bundle["stats"]["domain_distribution"]`
  - 按 accepted record 的 `canonical_url` host 聚合计数。
  - `www.` 前缀会归一到根 host，例如 `www.example.com` 计入
    `example.com`。
  - 空 host 归入 `unknown`。
- `docs/api.md`
  - Research Bundle Schema 示例和字段说明补充 `domain_distribution`。

TDD 证据：

- RED：
  - `pytest -q tests\unit\test_research_bundle.py`
  - 初始结果：`1 failed, 9 passed`
  - 失败原因：`bundle["stats"]` 尚无 `domain_distribution`。
- GREEN：
  - 实现 `_domain_distribution()` 并接入 bundle stats 后：
    `pytest -q tests\unit\test_research_bundle.py`
  - 结果：`10 passed`
- Benchmark 固化：
  - `pytest -q tests\unit\test_research_bundle_benchmarks.py`
  - 初始结果：`4 failed`
  - 失败原因：4 个 fixture 的 expected stats 尚未包含
    `domain_distribution`。
  - 更新 fixture 后：
    `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`15 passed`

当前结论：

- Phase 4.12 已为 bundle stats 增加 canonical-domain concentration
  observability。
- 该字段由直接单元测试、MCP 兼容测试和 4 个 benchmark fixture 覆盖。

完成前验证：

- `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - 结果：`15 passed`
- `python check.py`
  - Exit `0`
  - `3/3` registered engines available
  - `sites.json` loaded sites: `144`
  - fetch smoke 通过：`scrapling-http`
  - search smoke 返回 `2` results
- `pytest -q`
  - 结果：`400 passed, 34 skipped, 2 warnings`
  - 警告：Windows asyncio subprocess/pipe transport 的资源释放警告，测试结果仍为
    exit `0`。

## Runtime Cleanup: Windows Subprocess Timeout Drain

执行目标：

- 修复全量 pytest 结束时出现的两个 Windows asyncio
  Proactor/SubprocessTransport unraisable warnings。
- 不屏蔽 warning；修复 `_run_subprocess()` timeout 后未完整回收 subprocess pipes 的
  根因。

根因：

- 单独运行 `tests\unit\test_exceptions.py` 不触发 warning。
- 运行 `tests\unit\test_engines_base.py` 的 subprocess timeout 测试后会稳定触发。
- `_run_subprocess()` 原 timeout 分支执行 `proc.kill()` 后立即返回，没有等待
  `proc.communicate()`/pipe transport 完成异步收尾。
- Windows ProactorEventLoop 在 event loop 关闭后才析构残留 transport，因此出现
  `I/O operation on closed pipe` 和 `Event loop is closed`。

修复：

- 新增测试：
  `test_timeout_drains_process_pipes_after_kill`
  - 使用 fake hanging process 验证 timeout 后必须先 `kill()`，再第二次
    `communicate()` drain pipes。
- 更新 `app/engines/base.py`
  - timeout 分支在 `proc.kill()` 后执行
    `await asyncio.wait_for(proc.communicate(), timeout=2)`。
  - 使用 `contextlib.suppress(Exception)` 保持 timeout cleanup best-effort。

验证：

- RED：
  - `pytest -q tests\unit\test_engines_base.py -k "timeout_drains"`
  - 结果：`1 failed`，`communicate_calls == 1`。
- GREEN：
  - `pytest -q tests\unit\test_engines_base.py -k "timeout_drains or timeout"`
  - 结果：`2 passed`
- Warning 复现组合：
  - `pytest -q tests\unit\test_engines_base.py tests\unit\test_exceptions.py`
  - 结果：`45 passed`，无 Proactor/SubprocessTransport warning。
- Full suite：
  - `pytest -q`
  - 结果：`401 passed, 34 skipped`
- Diagnostics：
  - `python check.py`
  - Exit `0`，`3/3` engines available，fetch smoke 通过，search smoke 返回 2
    results。
