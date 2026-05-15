# Unified Web Skill Global Web Access Router Redesign

Date: 2026-05-13
Status: Approved direction, pending implementation plan

## Purpose

`unified-web-skill` should become a local-first Web Access MCP Router for AI agents.

Its purpose is not to compete head-on with hosted scraping infrastructure, search APIs, or cloud browser providers. Its purpose is to orchestrate them, together with local browser access and site-specific adapters, behind a small and reliable MCP interface.

The product target is global resource access. Chinese sites remain important because they are a difficult and useful validation set, but they are not the only focus and should not define the product boundary.

## Current Diagnosis

The project already contains the right ingredients:

- A historical duplicate runtime path that has now been removed.
- A v3 engine manager in `app/`: provider capabilities, routing, health monitoring, intent classification, discovery, quality gates, and storage.
- A site registry that can become the core knowledge asset for global source routing.
- A local MCP shape that fits OpenClaw, Claude Code, Codex, Cursor, and other agent runtimes.

The main issue was convergence. The project now keeps one runtime surface: the v3 MCP router. Some claims still need to stay within the reliability envelope, especially around unrestricted access, browser availability, and anti-bot bypass.

## Market Position

The market is already strong in adjacent categories:

- Search APIs: Tavily, Exa, Perplexity Sonar, OpenAI Web Search.
- LLM-ready scraping: Firecrawl, Jina Reader.
- Cloud browsers and anti-bot infrastructure: Browserbase, Bright Data.
- Scraping platforms and actor marketplaces: Apify.
- Local browser skills: web-access.

The project should not reimplement all of these. It should provide a coherent local orchestration layer:

- Use hosted services when they are the best provider.
- Use local browser/CDP when login state, interactive exploration, or user-context browsing matters.
- Use HTTP and markdown extraction for cheap public pages.
- Use site adapters for platforms with known structure.
- Return consistent, agent-friendly outputs with provenance and quality metadata.

## Product Shape

The product should expose a compact MCP interface:

- `search`: discover candidate sources across configured search providers.
- `fetch`: retrieve and extract one URL through provider fallback.
- `browse`: render a dynamic page through local or remote browser providers.
- `interact`: perform explicit browser actions when extraction requires interaction.
- `research`: run query planning, discovery, fetch, extraction, dedupe, ranking, and storage.
- `status`: show provider readiness, dependency health, and routing diagnostics.

Avoid growing many overlapping tools. Prefer fewer tools with clear provider routing.

## Architecture

### Core Router

The core router owns request normalization, provider selection, fallback, health state, rate limiting, and result schema. This should converge on the v3 `EngineManager` direction, because it already models provider capabilities and health.

### Providers

Providers should be pluggable and optional:

- Local HTTP provider: `httpx`, `trafilatura`, `BeautifulSoup`.
- Local browser provider: Playwright or Patchright.
- Local CLI provider: `bb-browser`, `opencli`, and similar site adapters.
- Reader provider: Jina Reader or equivalent URL-to-markdown service.
- Hosted scrape provider: Firecrawl or equivalent.
- Hosted search provider: Tavily, Exa, OpenAI Web Search, Perplexity Sonar.
- Hosted browser provider: Browserbase or equivalent.

The default install should work without paid accounts. Paid or hosted providers should be additive, not required.

### Source Registry

The site registry should become a global source capability matrix. Each source entry should describe:

- Domains and aliases.
- Region and language coverage.
- Content type: news, docs, academic, social, code, finance, commerce, forum, media, local.
- Recommended search provider.
- Recommended fetch or browser provider.
- Authentication needs.
- Known failure modes.
- Output schema expectations.
- Freshness and credibility hints.

This replaces scattered hardcoded domain lists and makes the project easier to improve incrementally.

### Research Pipeline

The research pipeline should produce a research bundle, not just a list of pages:

- Query variants used.
- Candidate sources discovered.
- Records accepted and rejected.
- Per-record provenance, provider chain, credibility score, freshness, language, and content type.
- Deduplication evidence.
- Failure statistics.
- Output files in JSON and Markdown.

The output should be designed for downstream agent reasoning.

## Global Resource Coverage Strategy

Phase 3 should be renamed from "Strengthen Chinese Sites" to "Global Source Coverage Matrix".

The goal is broad global coverage across resource categories:

- Global search and general web: Google-compatible providers, Bing, DuckDuckGo, Exa, Tavily, OpenAI Web Search.
- Documentation and code: GitHub, Stack Overflow, npm, PyPI, official docs, MDN.
- Academic: arXiv, Semantic Scholar, PubMed, DOI landing pages, university domains.
- News and current events: Reuters, AP, BBC, major regional outlets, official press pages.
- Social and forums: Reddit, X/Twitter, Hacker News, YouTube, Bilibili, Zhihu, Weibo, Xiaohongshu, V2EX.
- Finance and markets: SEC, company IR pages, Yahoo Finance, Nasdaq, Eastmoney, Xueqiu.
- Commerce and products: Amazon, Product Hunt, JD, Taobao, pricing pages, vendor docs.
- Local and maps-adjacent sources: official venue pages, travel sites, review platforms where allowed.

Chinese platforms should be included as a high-friction subset, alongside other hard platforms such as X/Twitter, Reddit, YouTube, TikTok, Instagram, and commerce sites.

## Execution Phases

### Phase 0: Convergence and Truthfulness

- Pick one primary entry point and one primary architecture.
- Align README, docs, API reference, tests, and diagnostics.
- Fix the health monitor threshold/test mismatch.
- Replace overbroad claims such as unrestricted access with accurate capability language.
- Ensure diagnostics distinguish dependency readiness from real network reachability.

### Phase 1: Reliable Local MVP

- Stabilize `search`, `fetch`, `browse`, `interact`, `research`, and `status`.
- Make browser dependency checks actionable.
- Ensure every tool returns a consistent schema.
- Add a benchmark fixture set covering public pages, docs pages, dynamic pages, and blocked pages.
- Keep the default path free of paid accounts.

### Phase 2: Provider Plugin Layer

- Define a provider interface and provider configuration model.
- Add Jina Reader and Firecrawl as optional content providers.
- Add Exa, Tavily, OpenAI Web Search, or similar search providers as optional discovery backends.
- Keep local HTTP/browser providers as the fallback baseline.

### Phase 3: Global Source Coverage Matrix

- Build a global source matrix by category, language, region, and difficulty.
- Start with 50 to 100 representative sources across categories.
- Track success rate, output quality, login needs, and failure mode per source.
- Promote source rules into `SiteRegistry` only after they are verified.

### Phase 4: Research Bundle Productization

- Improve ranking, deduplication, freshness, and credibility scoring.
- Add structured research output with citations and provider traces.
- Add regression benchmarks for common research tasks.
- Make the system useful as a dependable context collector for downstream agents.

## Non-Goals

- Do not build a full scraping marketplace in the near term.
- Do not promise universal bypass of anti-bot systems.
- Do not require paid SaaS providers for the default experience.
- Do not optimize only for Chinese resources.
- Do not add more MCP tools when provider routing can solve the problem behind existing tools.

## Success Criteria

The redesign is successful when:

- A new user can install and run the default MCP server with clear diagnostics.
- The project has one documented architecture and one main entry point.
- Unit tests and smoke diagnostics agree with the documented behavior.
- Global source coverage is measured by benchmarks instead of claims.
- Optional providers improve capability without making the core fragile.
- `research` returns useful, cited, quality-scored bundles for global topics.

## Open Decisions for Implementation Planning

- Which follow-on provider interfaces should be implemented first after the single-version cleanup.
- Which external providers should be implemented first.
- Whether the local browser path should use standalone Playwright/Patchright first or user Chrome CDP first.
- What benchmark source set should define the first global coverage milestone.
