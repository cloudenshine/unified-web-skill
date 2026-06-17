# Agent SOP V1

## Goal

This SOP standardizes how agents should use `unified-web-skill` so they stay on the lightest valid path and only escalate to persistent browser interaction when needed.

## Default Workflow

### 1. Discovery

Use `web_search` when:
- the destination URL is not known
- the user wants references or candidate sources
- the task is open-ended research

Expected result:
- a short set of candidate links with `trace_id` and `audit`

### 2. Extraction

Use `web_fetch` when:
- the target page is public
- the goal is to extract text or verify page content
- browser interaction is not yet justified

Expected result:
- extracted text, title, provider, and `trace_id`

### 3. Profile Selection

Use `web_profile_list` and `web_profile_use` when:
- the task requires login
- the task requires a persistent identity
- the task requires US/local browser geography consistency

Expected result:
- selected profile and binding reason

### 4. Browser Escalation

Use `web_interact` only when:
- the task requires login
- JS rendering is required
- the user asks for screenshots
- a form must be submitted
- `web_fetch` failed or returned insufficient content

Required fields:
- `intent`
- `profile` for login or persistent identity tasks

### 5. Research Bundles

Use `research_and_collect` when:
- the task is multi-source research
- the final result should include consolidated citations
- you need automatic escalation after weak fetch results

Recommended settings:
- `need_browser_verification=true` only when necessary
- `browser_profile` only when browser fallback is expected or acceptable

## Quick Decision Matrix

| User need | Tool |
|---|---|
| Find sources | `web_search` |
| Read a public page | `web_fetch` |
| Log in / click / screenshot | `web_profile_use` -> `web_interact` |
| Build a research brief | `research_and_collect` |
| Inspect available identities | `web_profile_list` |

## Profile Rules

### `stable-local-windows`
- Local daily tasks
- Low-risk workflows
- Chinese or mixed-language browsing

### `us-household-east`
- US market validation
- US browser checks
- Boston cloud egress matching

### `us-household-resi`
- High-risk US tasks only
- Requires residential proxy readiness

## Escalation Rules

Escalate from `web_fetch` to `web_interact` only if one of these is true:
- login is required
- page content depends on JS execution
- a screenshot is required
- a form must be completed
- the fetch path failed
- the fetch path produced insufficient content

## Reporting Rules

When returning results to the user or to an orchestrator:
- include `trace_id`
- include `audit.provider`
- include `audit.profile` when relevant
- include `audit.fallback_count`
- mention browser escalation when it occurred

## Anti-Patterns

Do not:
- jump to browser interaction for simple research tasks
- skip profile binding for login workflows
- switch profiles during one account workflow
- think in provider names instead of task semantics
- expose internal provider choice as if it were a user decision
