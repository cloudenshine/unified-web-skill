# Phase 3.1 Provider Routing Strategy Design

## Purpose

`unified-web-skill` should optimize global web access by choosing the lightest
provider that can produce the required result. The product target is global
resource access across languages and content categories, not a Chinese-only
resource collection. Chinese platforms remain a valuable hard-case subset.

The repaired `bb-browser` daemon restores the hard-path capability, but
`bb-browser` should not become the default path for all difficult pages. It is a
high-capability structured/browser fallback for sources where lighter providers
cannot produce equivalent results.

## Core Principle

For equivalent output quality, prefer providers in this order:

1. Public API, RSS, or JSON endpoint through lightweight HTTP.
2. Static or mostly static HTML fetch through `scrapling`.
3. Site-specific structured adapter through `opencli` or `bb-browser`.
4. Dynamic browser fetch for JavaScript-rendered pages.
5. Interactive browser session for login, click, scroll, form, cookie, or
   screenshot workflows.
6. Boundary recording for CAPTCHA, SMS, strict anti-bot, and paid paywalls.

This keeps the default route fast, low-resource, and stable while preserving
browser capability for the cases that actually need it.

## Provider Classes

### Lightweight HTTP

Primary provider: `scrapling`

Use for:

- Official APIs and JSON endpoints.
- RSS and Atom feeds.
- Public documentation and static pages.
- Package registries and scholarly metadata APIs.
- Simple public news, finance, encyclopedia, and reference pages.

Trade-off:

- Lowest resource cost and best batch stability.
- Limited when content depends on client-side JavaScript or session state.

### Structured CLI Adapters

Primary provider: `opencli` when it returns equivalent quality.
Secondary provider: `bb-browser` when the adapter is broader or better.

Use for:

- Known site commands such as Hacker News, Reddit, YouTube, Bilibili, arXiv, and
  platform-specific search.
- Cases where native JSON-like output is more useful than scraping rendered HTML.

Trade-off:

- More stable than visual browser scraping when adapters are maintained.
- Adapter schema and command availability can change, so verification must be
  separate from generic URL fetch verification.

### Dynamic Browser Fetch

Providers: optional browser-capable engines such as `lightpanda`, Scrapling
dynamic/stealth tiers, or `bb-browser` generic page open.

Use for:

- JavaScript-rendered pages where HTTP returns empty or incomplete content.
- Public pages that need rendering but not login or fine-grained interaction.

Trade-off:

- Higher CPU and memory cost than HTTP.
- More moving parts and longer timeouts.

### Interactive Session

Providers: `bb-browser`, `pinchtab`, or another configured browser interaction
provider.

Use for:

- Login-gated pages when the user has supplied valid session state.
- Cookie reuse, click flows, scroll loading, forms, and screenshot workflows.
- Browser automation tasks where the page state matters.

Trade-off:

- Highest local complexity and runtime fragility.
- Must not be part of the default batch verification path.

### Boundary Cases

Cases such as CAPTCHA, SMS checks, paid subscription paywalls, and strict
fingerprint blocking should be recorded as access boundaries. The system can
report the limitation and prefer official APIs or user-provided credentials when
available, but it should not pretend these are reliable autonomous routes.

## Source Matrix Changes

The global source matrix should become a routing-decision matrix, not just a
list of representative URLs.

Add these fields to each source entry:

- `access_type`: one of `api`, `rss`, `static_html`, `structured_adapter`,
  `dynamic_browser`, `interactive_session`, or `boundary`.
- `preferred_provider`: the provider expected to be best under normal
  conditions.
- `fallback_providers`: ordered provider names to try when the preferred path is
  unavailable or insufficient.
- `cost_tier`: `low`, `medium`, or `high`.
- `stability_tier`: `stable`, `variable`, or `fragile`.
- `promotion_status`: `matrix_only`, `verified_candidate`, `promoted`, or
  `blocked`.
- `failure_modes`: a list using stable values such as `timeout`, `blocked`,
  `auth_required`, `captcha`, `empty_content`, `adapter_changed`, and
  `parser_changed`.

Existing fields such as `difficulty`, `expected_provider`, and `requires_auth`
can remain temporarily for backward compatibility. The new fields should become
the authoritative decision fields.

## Routing Rules

Runtime routing should eventually be driven by verified source or site profiles:

- If a source has `access_type` of `api` or `rss`, use HTTP first.
- If a source is `static_html`, use `scrapling` first.
- If a source is `structured_adapter`, use the best verified adapter provider
  first, then fall back to HTTP or browser only if useful.
- If a source is `dynamic_browser`, use browser-capable providers only after
  HTTP is known to be insufficient.
- If a source is `interactive_session`, require an interaction-capable provider
  and preserve session/cookie assumptions explicitly.
- If a source is `boundary`, do not auto-promote it into default routing.

`sites.json` should receive only verified and intentionally promoted site rules.
The source matrix can contain many benchmark and research candidates that never
belong in runtime routing.

## Verification Strategy

Keep verification tracks separate:

- HTTP/RSS/API batch: fast global coverage and regression stability.
- Structured adapter batch: concrete `opencli` and `bb-browser site` commands.
- Browser runtime batch: daemon, CDP, dynamic rendering, and interaction health.
- Boundary batch: records failure modes without treating failures as product
  regressions.

Success criteria for Phase 3.1:

- The matrix schema can express cost, stability, access type, preferred provider,
  fallbacks, and promotion status.
- Tests enforce valid strategy fields and forbid unknown enum values.
- At least the existing 50 sources are classified without reducing current test
  coverage.
- Documentation explains when to choose `scrapling`, `opencli`, `bb-browser`,
  browser providers, or boundary recording.
- Full deterministic tests and diagnostics still pass after the schema change.

## Execution Boundary

Phase 3.1 should not add a large new source batch first. It should classify the
existing 50 sources, update validation tests, update documentation, and only
then resume expansion toward 100 global sources.

This keeps the project clean: each new global source added after Phase 3.1 must
already carry a routing decision, cost expectation, fallback path, and promotion
status.
