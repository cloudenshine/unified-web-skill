# Routing Policy v3

## Purpose

This document defines the stable routing and rejection rules for agent-facing web tasks.

## Tool-to-Provider Policy

| Tool | Primary route | Allowed fallback | Notes |
|---|---|---|---|
| `web_search` | `Scrapling/opencli` | search-capable providers | search/discovery only |
| `web_fetch` | `Scrapling` | `OpenCLI` -> `CloakBrowser` | public content extraction |
| `web_interact` | `CloakBrowser` | legacy interact providers | explicit intent required |
| `web_profile_list` | `CloakBrowser` | none | profile inventory only |
| `web_profile_use` | `CloakBrowser` | none | approved profiles only |
| `research_and_collect` | orchestrated | uses the above tools | browser only when justified |

## Decision Table

### Use `web_search`
When the task is about:
- finding candidate links
- market/source discovery
- current-result exploration
- finding official references before extraction

### Use `web_fetch`
When the task is about:
- extracting public-page text
- summarizing an article
- verifying page content
- reading a non-login page

### Use `web_interact`
When the task is about:
- JS-rendered pages where fetch is insufficient
- login-required flows
- clicking, filling, scrolling, screenshotting, downloading

### Use `research_and_collect`
When the task is about:
- multi-source research bundles
- ranked citations
- search + fetch + filter + summarize workflows

## Hard Rejection Rules

Reject the request when:
- `web_interact` has no `intent`
- `login_required` or `require_login=true` has no profile
- `us-household-resi` is requested without residential proxy readiness
- a research-only task asks to skip directly to browser interaction
- an agent attempts to create or invent a new production profile

## Profile Rules

### `stable-local-windows`
Use for:
- local daily tasks
- low-risk Chinese or mixed-language workflows

### `us-household-east`
Use for:
- US-market validation
- US website checks using the current Boston cloud egress

### `us-household-resi`
Use for:
- high-risk US tasks
- only after a residential proxy is configured and verified

## Logging Requirements

Every routed task should emit:
- `trace_id`
- requested tool
- chosen provider
- fallback count
- profile used, if any
- reason for browser escalation, if any

## Agent UX Rule

Agents should think in task semantics, not provider names:
- search -> `web_search`
- read -> `web_fetch`
- act -> `web_interact`
- research -> `research_and_collect`
- identity -> `web_profile_*`


