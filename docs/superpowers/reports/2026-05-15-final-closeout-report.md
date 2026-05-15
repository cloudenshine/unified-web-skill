# Final Closeout Report

Date: 2026-05-15
Workspace: `E:\claude_work\g\unified-web-skill`

## Conclusion

当前项目阶段可以作为可交付基线收尾。核心运行时、provider 层、source matrix、
research bundle 产品化、周期性回归入口、Windows subprocess timeout cleanup
均已完成并通过本轮验证。下一步是将该收尾包发布到 GitHub。

## Delivered Baseline

- Single runtime: `app/`
- MCP entry: `python -m app.mcp_server --stdio`
- Diagnostics entry: `python check.py`
- Default providers: `scrapling`, `opencli`, `bb-browser`
- Optional providers: `lightpanda`, `pinchtab`, `clibrowser`
- Source matrix: 100 global representative sources.
- Runtime site registry: 142 loaded site rules.
- Research bundle output:
  - accepted/rejected records
  - citations
  - provider traces
  - score breakdown
  - score summary
  - rejection reasons
  - language distribution
  - provider distribution
  - source type distribution
  - canonical domain distribution
- Periodic verification:
  - `verify_source_matrix.py --regression-profile ...`
  - `make source-matrix-regression`
  - `make source-matrix-watch`

## Completed Phases

- Phase 1: single v3 runtime and deterministic baseline.
- Phase 2: provider metadata, version diagnostics, stable default provider registration.
- Phase 3: global source matrix, promoted/matrix-only/blocked classification, strict provider-path verification.
- Phase 4: research bundle productization and regression benchmarks through Phase 4.12.
- Runtime cleanup: Windows `_run_subprocess()` timeout cleanup now drains subprocess pipes after `kill()`.
- Final matrix stabilization: arXiv API and Open Food Facts API are isolated in
  `rate-limited-watch` instead of the release-blocking promoted HTTP batch.
- Browser daemon hygiene: a stale orphan `bb-browser` daemon on port 19824 was
  stopped, then `bb-browser daemon start` verified a healthy daemon before
  browser regressions.

## Fresh Verification

- Full test suite:
  - Command: `pytest -q`
  - Result: `403 passed, 34 skipped`
- Diagnostics:
  - Command: `python check.py`
  - Result: exit `0`, `3/3` engines available, `142` sites loaded.
  - Fetch smoke: `scrapling-http`
  - Search smoke: `2` results.
- Promoted HTTP/RSS/API source regression:
  - Command: `python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified --output outputs\source_matrix_regression_final_promoted_http_clean2.json`
  - Result: `83 total, 83 verified, 0 weak, 0 failed`.
- Promoted structured source regression:
  - Command: `python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified --output outputs\source_matrix_regression_final_promoted_structured_clean3.json`
  - Result: `4 total, 4 verified, 0 weak, 0 failed`.
- Promoted browser source regression:
  - Command: `python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified --output outputs\source_matrix_regression_final_promoted_browser_clean3.json`
  - Result: `6 total, 6 verified, 0 weak, 0 failed`.
- Special source watch:
  - Command: `python verify_source_matrix.py --regression-profile special-watch --timeout 45 --min-text-length 200 --output outputs\source_matrix_regression_final_special_watch_clean2.json`
  - Result: `2 total, 1 verified, 0 weak, 1 failed`.
  - Amazon verified via `bb-browser`; ProductHunt remained `403 blocked`.
- Rate-limited watch:
  - Command: `python verify_source_matrix.py --regression-profile rate-limited-watch --timeout 60 --min-text-length 200 --output outputs\source_matrix_regression_final_rate_limited_watch_clean2.json`
  - Result: `2 total, 2 verified, 0 weak, 0 failed`.
  - arXiv API and Open Food Facts both verified in the latest watch run.
- CI unit-test command:
  - Command: `pytest -v tests/unit/ --tb=short --timeout=30`
  - Result after adding `pytest-timeout`: `403 passed`.

## Live Verification Policy

Promoted HTTP/RSS/API regression is now green. Two externally volatile API
sources were removed from the release-blocking batch and kept as matrix-only
watch sources:

- `academic_arxiv_api_query`: repeated final-run 429 responses before later
  watch verification.
- `commerce_openfoodfacts_search`: repeated final-run 503 responses before
  later watch verification.

Interpretation:

- These are external service volatility conditions, not unit test, runtime
  import, or provider registration failures.
- arXiv API usage guidance commonly recommends a delay of at least 3 seconds
  between repeated API calls; HTTP `429` means too many requests in a time
  window and may include or imply retry-after behavior.
- The product baseline closes with a deterministic release-blocking promoted
  batch and a separate watch profile for volatile evidence collection.

Recommended future hardening if these sources must return to strict promoted
regression:

1. Add source/domain-specific verifier cooldown for `export.arxiv.org` and
   `world.openfoodfacts.org`.
2. Add 429/503-aware exponential backoff with jitter and `Retry-After` support.
3. Require sustained watch-profile stability before returning either source to
   release-blocking promoted HTTP.
4. Prefer the already verified `academic_arxiv_cs_ai` browser-first structured
   route when a live arXiv evidence path is needed immediately.

References used for the residual-risk interpretation:

- arXiv API user manual notes responsible usage and a 3-second delay between
  repeated calls.
- MDN defines `429 Too Many Requests` as rate limiting and notes `Retry-After`
  may tell clients how long to wait before retrying.

## File Hygiene

- `__pycache__` directories under `app/` and `tests/` were removed after tests.
- `outputs/` was preserved because it is gitignored and may contain historical
  verification/user data.
- Historical V2/runtime-conflict files remain deleted in the working tree.
- No new throwaway root scripts were added.
- Untracked external `web-access-source/` clone was removed because it was not
  referenced by the project and should not be published as part of this repo.
- `.pytest-tmp/` is ignored and used as a cross-platform pytest basetemp so
  local Windows runs and Ubuntu CI do not depend on a machine-specific temp
  path.

## Current Repository State

- Branch before publish: `main`
- Git worktree type: normal repo (`.git` equals common git dir).
- Worktree changes are intended to be committed to a `codex/` branch and pushed
  to GitHub.

## Final Recommendation

Close the current project phase as a verified baseline. The release-blocking
test and promoted regression lines are green; ProductHunt remains blocked, and
arXiv/Open Food Facts remain watch-only until stronger stability evidence
exists.

Recommended next phase after GitHub publication: hosted provider experiments
and CI scheduling for source-matrix regression/watch profiles.
