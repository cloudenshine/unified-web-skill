# Project State

Updated: 2026-05-15

## Current Goal

Build a local-first global Web Access MCP Router for AI agents. Chinese sources
remain an important difficult subset, but the target is global resource access.

## Current Phase

Final closeout package is complete for the current baseline. Core tests,
diagnostics, promoted source-matrix regressions, research bundle
productization, and periodic verification entry points are in place.
`academic_arxiv_api_query` and `commerce_openfoodfacts_search` were moved to a
rate-limited watch profile after repeated external 429/503 responses during
final strict promoted HTTP checks; both verified in the latest watch run but
remain outside the release-blocking promoted HTTP batch. Matrix-only
high-cost/dynamic entries remain isolated, and the only currently blocked
source is ProductHunt.

## Stable Baseline

- Single runtime: `app/`
- MCP entry: `python -m app.mcp_server --stdio`
- Diagnostics entry: `python check.py`
- Default providers: `scrapling`, `opencli`, `bb-browser`
- Optional providers remain opt-in: `lightpanda`, `pinchtab`, `clibrowser`

## Completed

- Phase 1: single v3 runtime and deterministic baseline.
- Phase 2: provider metadata, version diagnostics, and stable default provider
  registration.
- Phase 3.1: source strategy metadata added.
- Phase 3.2: source matrix expanded to 75 global representative sources.
- Phase 3.3: project hygiene pass removed obsolete one-off scripts and stale
  generated outputs.
- Phase 3.4: 52 low-cost API/RSS/static HTML sources promoted into
  `sites.json`; dynamic browser, interactive session, and boundary sources were
  not promoted.
- Phase 3.5: `reddit/search`, `youtube/search`, `bilibili/search`, and
  `arxiv/search` live adapter verification passed. Four structured-adapter
  sources are now marked `promoted`; `youtube` runtime routing now includes
  `bb-browser` before lighter fallbacks.
- Phase 3.6: the remaining 9 `verified_candidate` sources were reconciled with
  existing `sites.json` entries and marked `promoted`.
- Phase 3.7: 25 low-friction global sources were added, live-verified, and
  promoted into `sites.json`. Three weak/failed endpoints were replaced before
  promotion.
- Phase 3.8: live verification tooling now filters by access type, promotion
  status, cost tier, and preferred provider. Strict provider mode was added for
  clean batch evidence. The first strict low-cost scrapling batch verified 15
  of 20 promoted API/RSS/static HTML sources; five failures are retained for
  follow-up classification rather than removed from one live run.
- Phase 3.8 follow-up: strict scrapling false positives were reduced by
  tightening long-page block detection. `github`, `pubmed`, and `wikipedia`
  re-verified on scrapling; `stackoverflow` and `reuters` were reclassified to
  browser-first provider paths after strict scrapling failed and `bb-browser`
  verified both.
- Phase 3.8 browser runtime batch: strict `bb-browser` verification passed for
  all five promoted browser-first sources, including the reclassified
  `stackoverflow` and `reuters` routes.
- Phase 3.8 matrix-only dynamic/browser batch: DuckDuckGo moved to
  browser-first after strict scrapling returned weak content, ProductHunt moved
  to `blocked` after all available providers failed, and the remaining
  matrix-only dynamic/interactive batch verified cleanly. Amazon boundary
  verified once via strict `bb-browser` but remains `matrix_only` because it is
  a high-cost boundary source.
- Phase 3.8 final sweep: all promoted HTTP/RSS/API sources verified
  `87/87`, all promoted structured-adapter sources verified `4/4`, and arXiv
  moved from opencli-first to browser-first after the local opencli adapter
  loader failed while `bb-browser` verified.
- Phase 4.1: added `ResearchBundleBuilder` for accepted/rejected records,
  provider traces, failure stats, and deterministic baseline scoring.
- Phase 4.2: strengthened `ResearchBundleBuilder` with injected clock support,
  age-bucket freshness scoring, and ranked citation output for accepted records.
- Phase 4.3: added conservative credibility calibration for authoritative
  domains, structured adapters, and API/RSS fetch modes.
- Phase 4.4: added the first fixed research-bundle regression benchmark fixture
  for global policy research ranking, duplicate handling, citations, score
  breakdowns, and stats.
- Phase 4.5: expanded research-bundle regression benchmarks to cover academic
  literature, package/code, and news research tasks with the same fixed-output
  assertions.
- Phase 4.6: added `bundle.stats.score_summary` for accepted-record score
  count, max, min, and average; benchmark fixtures now pin this output.
- Phase 4.7: extended `bundle.stats.score_summary` with high/medium/low
  quality buckets while preserving score values and existing response fields.
- Phase 4.8: added `bundle.stats.rejection_reasons` so callers can inspect
  rejected-record reason counts without scanning detailed records.
- Phase 4.9: added `bundle.stats.language_distribution` so callers can inspect
  accepted-record language coverage for global research results.
- Phase 4.10: added `bundle.stats.provider_distribution` and
  `bundle.stats.source_type_distribution`, and documented the research bundle
  schema in `docs/api.md`.
- Phase 4.11: added stable source-matrix regression profiles to
  `verify_source_matrix.py`, Makefile targets for promoted regression and
  special-source watch runs, and documented the periodic verification workflow.
  Promoted HTTP/RSS/API, structured, and browser-first regression profiles
  verified cleanly; Amazon remains boundary `matrix_only`, ProductHunt remains
  blocked.
- Phase 4.12: added `bundle.stats.domain_distribution` so callers can detect
  canonical-domain concentration in accepted research results; benchmark
  fixtures and API schema docs now pin the field.
- Final source-matrix stabilization: moved arXiv API and Open Food Facts API to
  a rate-limited watch profile and removed their default runtime routes from
  `sites.json`, keeping strict promoted HTTP regression deterministic.
- Runtime cleanup: fixed `_run_subprocess()` timeout cleanup on Windows by
  draining subprocess pipes after `kill()`, removing the previous pytest
  Proactor/SubprocessTransport unraisable warnings.
- Final closeout package: added
  `docs/superpowers/reports/2026-05-15-final-closeout-report.md` with current
  deliverables, verification evidence, file hygiene notes, and residual live
  source risk.
- GitHub closeout preparation: latest stable provider versions confirmed for
  the active local providers (`bb-browser` 0.11.6, `opencli` 1.7.18,
  `scrapling` 0.4.8). A stale orphan `bb-browser` daemon process on port 19824
  was stopped and the daemon was restarted cleanly before browser regressions.

## Verification Snapshot

- Focused promotion tests: `pytest -q tests\unit\test_site_registry.py tests\unit\test_source_matrix.py`
  - Latest observed: `35 passed`
- Diagnostics: `python check.py`
  - Latest observed: exit `0`, `3/3` engines available, 144 sites loaded.
- Full test suite: `pytest -q`
  - Latest observed: `375 passed, 34 skipped`.
- Focused adapter/routing tests:
  `pytest -q tests\unit\test_site_registry.py tests\unit\test_source_matrix.py tests\unit\test_adapter_verifier.py tests\unit\test_verify_site_adapters_cli.py`
  - Latest observed: `48 passed`
- Focused candidate-closure tests:
  `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py`
  - Latest observed: `37 passed`
- Phase 3.7 source expansion verification:
  `python verify_source_matrix.py --ids <25 new source ids> --limit 25 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_100_final.json`
  - Latest observed: `25 verified, 0 weak, 0 failed`
- Phase 4.1 focused tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py`
  - Latest observed: `4 passed`
- Phase 4.2 focused bundle tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py`
  - Latest observed: `6 passed`
- Phase 4.3 focused bundle tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py`
  - Latest observed: `7 passed`
- Phase 4.4 benchmark tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `8 passed`
- Phase 4.5 benchmark tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `11 passed`
- Phase 4.6 focused tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `12 passed`
- Phase 4.7 focused tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `12 passed`
- Phase 4.8 focused tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `12 passed`
- Phase 4.9 focused tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `13 passed`
- Phase 4.10 focused tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `14 passed`
- Phase 4.11 focused regression-profile tests:
  `pytest -q tests\unit\test_verify_source_matrix_cli.py tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py`
  - Latest observed: `27 passed`
- Phase 4.11 promoted HTTP source-matrix regression:
  `python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified --output outputs\source_matrix_regression_promoted_http_latest.json`
  - Latest observed: `87 total, 87 verified, 0 weak, 0 failed`.
- Phase 4.11 promoted structured source-matrix regression:
  `python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified --output outputs\source_matrix_regression_promoted_structured_latest.json`
  - Latest observed: `4 total, 4 verified, 0 weak, 0 failed`.
- Phase 4.11 promoted browser source-matrix regression:
  `python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified --output outputs\source_matrix_regression_promoted_browser_latest.json`
  - Latest observed: `6 total, 6 verified, 0 weak, 0 failed`.
- Phase 4.11 special-source watch:
  `python verify_source_matrix.py --regression-profile special-watch --timeout 45 --min-text-length 200 --output outputs\source_matrix_regression_special_watch_latest.json`
  - Latest observed: `2 total, 1 verified, 0 weak, 1 failed`.
  - Amazon verified through `bb-browser`; ProductHunt failed with `403 blocked`
    through `scrapling-stealth`.
- Phase 4.11 focused completion tests:
  `pytest -q tests\unit\test_verify_source_matrix_cli.py tests\unit\test_source_verifier.py tests\unit\test_source_matrix.py tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `41 passed`.
- Phase 4.12 focused bundle tests:
  `pytest -q tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `15 passed`.
- Diagnostics: `python check.py`
  - Latest observed: exit `0`, `3/3` engines available, 144 sites loaded;
    fetch smoke passed via `scrapling-http`, search smoke returned two results.
- Final full test suite: `pytest -q`
  - Latest observed: `401 passed, 34 skipped`.
- Final diagnostics: `python check.py`
  - Latest observed: exit `0`, `3/3` engines available, 144 sites loaded;
    fetch smoke passed via `scrapling-http`, search smoke returned two results.
- Final release-blocking promoted HTTP source-matrix regression:
  `python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified --output outputs\source_matrix_regression_final_promoted_http_clean2.json`
  - Latest observed: `83 total, 83 verified, 0 weak, 0 failed`.
- Final release-blocking promoted structured source-matrix regression:
  `python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified --output outputs\source_matrix_regression_final_promoted_structured_clean3.json`
  - Latest observed: `4 total, 4 verified, 0 weak, 0 failed`.
- Final release-blocking promoted browser source-matrix regression:
  `python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified --output outputs\source_matrix_regression_final_promoted_browser_clean3.json`
  - Latest observed: `6 total, 6 verified, 0 weak, 0 failed`.
- Final rate-limited watch:
  `python verify_source_matrix.py --regression-profile rate-limited-watch --timeout 60 --min-text-length 200 --output outputs\source_matrix_regression_final_rate_limited_watch_clean2.json`
  - Latest observed: `2 total, 2 verified, 0 weak, 0 failed`.
  - arXiv API and Open Food Facts verified in this watch run but remain
    `matrix_only` because recent strict promoted runs showed 429/503 external
    volatility.
- Final special-source watch:
  `python verify_source_matrix.py --regression-profile special-watch --timeout 45 --min-text-length 200 --output outputs\source_matrix_regression_final_special_watch_clean2.json`
  - Latest observed: `2 total, 1 verified, 0 weak, 1 failed`.
  - Amazon verified through `bb-browser`; ProductHunt remained `403 blocked`.
- Final full test suite: `pytest -q`
  - Latest observed: `403 passed, 34 skipped`.
- Final diagnostics: `python check.py`
  - Latest observed: exit `0`, `3/3` engines available, 142 sites loaded;
    fetch smoke passed via `scrapling-http`, search smoke returned two results.
- Phase 3.8 source verification tooling tests:
  `pytest -q tests\unit\test_source_verifier.py tests\unit\test_engine_manager.py tests\unit\test_verify_source_matrix_cli.py`
  - Latest observed: `38 passed`
- Phase 3.8 focused routing/classification tests:
  `pytest -q tests\unit\test_scrapling_engine.py tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py tests\unit\test_engine_manager.py`
  - Latest observed: `83 passed`
- Phase 3.8 focused browser-batch tests:
  `pytest -q tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py`
  - Latest observed: `51 passed`
- Phase 3.8 strict low-cost provider batch:
  `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --cost-tiers low --preferred-providers scrapling --strict-preferred-provider --limit 20 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_low_cost_strict_provider.json`
  - Latest observed: `20 total, 15 verified, 0 weak, 5 failed`.
  - Failed strict scrapling path: `code_github_fastapi`,
    `code_stackoverflow_python_asyncio`, `academic_pubmed_search`,
    `news_reuters_world`, `docs_wikipedia_ai`.
  - Note: several failed entries returned substantial text but provider status
    remained blocked, so they require strategy/provider classification rather
    than immediate source removal.
- Phase 3.8 failure classification:
  `python verify_source_matrix.py --ids code_github_fastapi,code_stackoverflow_python_asyncio,academic_pubmed_search,news_reuters_world,docs_wikipedia_ai --strict-preferred-provider --limit 5 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_failure_recheck_after_strategy.json`
  - Latest observed: `5 total, 5 verified, 0 weak, 0 failed`.
- Phase 3.8 low-cost batch after strategy update:
  `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --cost-tiers low --preferred-providers scrapling --strict-preferred-provider --limit 20 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_low_cost_after_strategy.json`
  - Latest observed: `20 total, 20 verified, 0 weak, 0 failed`.
- Phase 3.8 promoted browser provider batch:
  `python verify_source_matrix.py --preferred-providers bb-browser --promotion-statuses promoted --strict-preferred-provider --limit 10 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_browser_promoted.json`
  - Latest observed: `5 total, 5 verified, 0 weak, 0 failed`.
  - Verified: `code_stackoverflow_python_asyncio`, `news_reuters_world`,
    `social_reddit_programming`, `video_youtube_search`,
    `video_bilibili_search`.
- Phase 3.8 matrix-only dynamic/interactive batch:
  `python verify_source_matrix.py --access-types dynamic_browser,interactive_session --promotion-statuses matrix_only --strict-preferred-provider --limit 20 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_matrix_only_dynamic_after_strategy.json`
  - Latest observed: `7 total, 7 verified, 0 weak, 0 failed`.
- Phase 3.8 boundary matrix-only batch:
  `python verify_source_matrix.py --access-types boundary --promotion-statuses matrix_only --strict-preferred-provider --limit 5 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_boundary_matrix_only.json`
  - Latest observed: `1 total, 1 verified, 0 weak, 0 failed`.
  - Verified: `commerce_amazon_search`; kept `matrix_only` because it remains a
    high-cost boundary source.
- Phase 3.8 final promoted HTTP/RSS/API sweep:
  `python verify_source_matrix.py --access-types api,rss,static_html --promotion-statuses promoted --strict-preferred-provider --limit 100 --timeout 30 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_promoted_http_rss_api_final.json`
  - Latest observed: `87 total, 87 verified, 0 weak, 0 failed`.
- Phase 3.8 final promoted structured-adapter sweep:
  `python verify_source_matrix.py --access-types structured_adapter --promotion-statuses promoted --strict-preferred-provider --limit 20 --timeout 45 --min-text-length 200 --output outputs\source_matrix_verification_phase_3_8_structured_promoted_after_strategy.json`
  - Latest observed: `4 total, 4 verified, 0 weak, 0 failed`.
- Diagnostics: `python check.py`
  - Latest observed: exit `0`, `3/3` engines available, 144 sites loaded;
    httpbin fetch smoke passed via `scrapling-http`, search smoke returned
    two results.
- Phase 3.8 final focused regression:
  `pytest -q tests\unit\test_scrapling_engine.py tests\unit\test_source_matrix.py tests\unit\test_site_registry.py tests\unit\test_source_verifier.py tests\unit\test_verify_source_matrix_cli.py tests\unit\test_engine_manager.py tests\unit\test_research_bundle.py tests\unit\test_mcp_research_response.py tests\unit\test_research_bundle_benchmarks.py`
  - Latest observed: `102 passed`.
- Full test suite: `pytest -q`
  - Latest observed: `395 passed, 34 skipped`.

## Keep / Avoid

- Keep `check.py`, `verify_source_matrix.py`, `verify_site_adapters.py`, and
  `test_deploy_v3.py`.
- Keep `outputs/` unless the user explicitly confirms deletion; it is gitignored
  and may contain historical user data.
- Remove untracked external source clones such as `web-access-source/` when they
  are not referenced by the project and would pollute publication.
- Do not resurrect V2 or `core/rings` runtime paths.
- Do not keep one-off root scripts, fixed-query scratch scripts, stale test
  result JSON files, or cache directories when they are clearly disposable.

## Next Step

Current baseline is ready for GitHub publication:

1. Keep ProductHunt blocked unless a future provider path verifies it.
2. Keep Amazon and other high-cost/dynamic sources as `matrix_only` until a
   separate promotion decision is made.
3. Keep arXiv API and Open Food Facts in `rate-limited-watch` unless
   source-specific cooldown/backoff and sustained stability evidence are added.
4. Use `make source-matrix-regression` for promoted periodic checks and
   `make source-matrix-watch` for boundary/special/rate-limited evidence
   capture.
5. Publish the finalized baseline to GitHub on a `codex/` branch and open a
   draft PR for review.

Recommended continuation prompt:

```text
读取 PROJECT_STATE.md、PLAN.md 和必要代码，继续当前 Phase；完成后更新 PROJECT_STATE.md 与执行报告并跑测试。
```
