# Agent Bootstrap Template V1

Use this checklist when bringing a new local agent online.

## 1. Register MCP

- Register only `unified-web-skill`
- Do not register raw provider endpoints as separate agent tools

## 2. Apply System Prompt

- Use `AGENT_SYSTEM_PROMPT_V1.md`
- Or use `CODEX_CLAUDE_PROMPT_TEMPLATE_V1.md` as the embedded policy block

## 3. Confirm Environment

- `CLOAK_MANAGER_BASE_URL=http://127.0.0.1:8080`
- `CLOAK_BROWSER_BASE_URL=http://127.0.0.1:9222`
- `RESIDENTIAL_PROXY_READY=false` unless actually verified

## 4. Verify Tool Behavior

Run these in order:

1. `web_search` on a simple query
2. `web_fetch` on a public page
3. `web_profile_list`
4. `web_profile_use` with `stable-local-windows`
5. `web_interact` with `intent=js_render`
6. `research_and_collect` with `need_browser_verification=false`

## 5. Promotion Rules

An agent is ready for real work only after:
- high-level tools are callable
- `trace_id` and `audit` appear in results
- profile selection works
- browser interaction works on a local test page

## 6. Default Usage Pattern

- research -> `web_search`
- read -> `web_fetch`
- identity -> `web_profile_use`
- act -> `web_interact`
- bundle -> `research_and_collect`

## 7. Anti-Patterns

Do not ship an agent that:
- directly exposes provider names
- starts with browser interaction for ordinary research
- skips profile binding on login flows
- mixes local and US profiles in the same account task
