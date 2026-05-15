# unified-web-skill Roadmap

> Updated: 2026-05-15
> Direction: local-first global Web Access MCP Router for AI agents.

## Product Goal

`unified-web-skill` exposes one MCP router that helps agents search, fetch,
browse, interact with, crawl, and collect web resources across global sources.
Chinese platforms remain an important hard-case subset, but the product target
is global resource access across languages, regions, and content categories.

## Current Baseline

- One runtime architecture: the v3 `app/` EngineManager router.
- One MCP entry point: `python -m app.mcp_server --stdio`.
- One diagnostic entry point: `python check.py`.
- Removed historical v2 runtime files and ring-model conflict paths.
- Default install should remain useful without paid providers.

## Execution Phases

### Phase 1: Reliable Local MVP

- Keep the single v3 runtime/documentation surface stable.
- Ensure diagnostics clearly separate critical dependency failures from optional
  live network/provider warnings.
- Stabilize `research_and_collect`, `web_fetch`, `web_cli`, `web_interact`,
  `web_search`, `web_crawl`, and `engine_status`.
- Maintain deterministic unit tests and explicit live integration tests.

Status: complete for the current baseline; single-version cleanup and full
verification are in place.

### Phase 2: Provider Plugin Layer

- Define provider metadata and configuration contracts for built-in and optional
  providers.
- Keep the default local baseline small and stable: `scrapling`, `bb-browser`,
  and `opencli`.
- Keep browser/session providers opt-in: `lightpanda`, `clibrowser`, and
  `pinchtab` register only when explicitly configured.
- Add optional hosted providers later behind the same interface: Jina Reader,
  Firecrawl, Exa, Tavily, OpenAI Web Search, or Perplexity Sonar.
- Surface provider readiness through `engine_status` and `check.py`.

Status: foundation complete; provider metadata, version diagnostics, and stable
default provider registration are implemented.

### Phase 3: Global Source Coverage Matrix

- Build a verified source matrix by category, language, region, and difficulty.
- Start with a small verified seed set, then expand toward 50 to 100
  representative sources covering docs, code, academic, news, social/forums,
  finance, commerce, search, video, and local resources.
- Track success rate, login needs, extraction quality, and failure modes.
- Promote source rules into `app/discovery/sites.json` only after verification.

Status: active; the matrix has expanded from the first 20-source seed to 75
representative global sources. Phase 3.1 classified sources by access type,
preferred provider, fallback route, cost tier, stability tier, and promotion
status. Phase 3.2 added 25 more low-friction global sources and live-verified
the replacement endpoints that were needed after blocked/rate-limited failures.
Phase 3.4 has promoted 52 low-cost API/RSS/static HTML rules into
`app/discovery/sites.json`. The `bb-browser` daemon runtime issue has been
repaired. Phase 3.5 verified the hard browser-adapter batch and reconciled the
verified structured-adapter sources with runtime routing. Phase 3.6 resolved
the remaining verified-candidate backlog, leaving no ambiguous
`verified_candidate` entries in the 75-source matrix. Phase 3.7 expanded the
matrix to 100 sources, live-verified the 25-source expansion batch, replaced
weak/failed endpoints, and promoted the verified rules into `sites.json`.
Phase 3.8 has started the verification refresh pass: `verify_source_matrix.py`
can now filter by access type, promotion status, cost tier, and preferred
provider, and strict preferred-provider mode keeps low-cost scrapling batches
from being polluted by browser/CLI fallbacks or manager-level circuit state.
The first failure classification pass is complete: long-page block detection
was tightened, `github`, `pubmed`, and `wikipedia` stayed on scrapling, while
`stackoverflow` and `reuters` moved to browser-first provider paths after
`bb-browser` verified both and strict scrapling returned 403/401.
The promoted browser runtime batch now verifies cleanly: five promoted
browser-first sources passed strict `bb-browser` live verification, including
`stackoverflow`, `reuters`, `reddit`, `youtube`, and `bilibili`.
The matrix-only dynamic/browser refresh also verifies cleanly after
classification: DuckDuckGo moved to browser-first, ProductHunt moved to
blocked, and Amazon remains a high-cost boundary `matrix_only` source after one
strict `bb-browser` verification. Phase 3.8 is now complete: all promoted
HTTP/RSS/API sources verified `87/87`, promoted structured adapters verified
`4/4`, and promoted browser-first sources verified `5/5`. arXiv moved to
browser-first after the local `opencli` adapter loader failed while
`bb-browser` and `scrapling` both verified the source.

### Phase 4: Research Bundle Productization

- Improve ranking, deduplication, freshness, and credibility scoring.
- Return structured research bundles with citations, provider traces, accepted
  and rejected records, and failure statistics.
- Add regression benchmarks for recurring global research tasks.

Status: complete for the current baseline; Phase 4.1 added a structured research bundle builder and
included bundle output in `research_and_collect` without removing the legacy
response fields. Phase 4.2 strengthened scoring with deterministic freshness
decay and added ranked citations for accepted records. Phase 4.3 added
conservative credibility calibration based on authoritative domains,
structured adapters, and API/RSS fetch modes. Phase 4.4 added the first fixed
regression benchmark fixture for global policy research bundle behavior. Phase
4.5 expanded benchmark coverage to academic, package/code, and news research
tasks. Phase 4.6 added score distribution summaries to bundle stats and pinned
them in the benchmark fixtures. Phase 4.7 added high/medium/low quality
buckets to the score summary for caller-facing observability. Phase 4.8 added
rejection reason counts to bundle stats so callers can inspect why records were
rejected without scanning every rejected record. Phase 4.9 added
accepted-record language distribution to bundle stats for global research
coverage observability. Phase 4.10 added accepted-record provider and
source-type distributions, and documented the research bundle schema in
`docs/api.md`. Phase 4.11 added stable source-matrix regression profiles,
Makefile targets, and documentation for periodic promoted checks plus
boundary/special evidence watch runs. Phase 4.12 added accepted-record
canonical-domain distribution to bundle stats and pinned it in benchmark
fixtures. Final closeout is complete with core tests, diagnostics, and
release-blocking promoted source-matrix regressions passing. arXiv API and Open
Food Facts are isolated in `rate-limited-watch` after observed external
429/503 volatility, and ProductHunt remains blocked.

## Near-Term Execution Order

1. Continue focused bundle behavior hardening where it improves caller
   observability without adding runtime complexity.
2. Keep the 100-source matrix clean: remove or replace endpoints that fail live
   verification instead of keeping weak entries.
3. Keep live verification batches separate by access type and provider path:
   HTTP/RSS/API, structured adapters, browser runtime, and boundary cases.
4. Keep `bb-browser` daemon health monitored before and during future
   browser-adapter verification batches.
5. Promote only verified source rules into `app/discovery/sites.json`.
6. Add Phase 4 regression benchmark fixtures for recurring global research
   tasks after bundle scoring is stable.
7. Keep the Phase 3.8 browser-first reclassified sources under future browser
   batch monitoring: `code_stackoverflow_python_asyncio`,
   `news_reuters_world`, and `academic_arxiv_cs_ai`.
8. Treat Phase 3.8 as closed for the current baseline. Keep ProductHunt as the
   only currently blocked source unless a later provider path verifies it, and
   keep Amazon plus other high-cost/dynamic sources `matrix_only` until a
   separate promotion decision is made.
9. Use `make source-matrix-regression` for strict promoted periodic checks and
   `make source-matrix-watch` for ProductHunt/Amazon/rate-limited evidence
   capture.
10. If arXiv API or Open Food Facts must return to release-blocking promoted
    HTTP regression, first add source-specific cooldown/backoff and collect
    sustained watch-profile stability evidence.
