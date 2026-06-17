# Project State

> Baseline: v3.0.0 — 3 engines (scrapling, opencli, cloakbrowser), 13 MCP tools, 142 verified sources, 379 passing tests.

---

## Architecture

One runtime: v3 engine-manager MCP router.

```
AI Agent / MCP Client
  └─ app.mcp_server (13 MCP tools)
       ├─ EngineManager → 3 engines
       ├─ ResearchPipeline — Full research pipeline
       ├─ CredentialStore — Cookie/credential management
       └─ SiteRegistry — 142 source metadata + regression
```

## Implemented Phases

| Phase | Status | Deliverables |
|-------|--------|-------------|
| v3 Baseline | ✅ Complete | 3-engine router, 13 tools, 142 sources, credential module |
| Engine Cleanup | ✅ Complete | Removed bb-browser/lightpanda/pinchtab/clibrowser/searxng/cloak-manager |
| Documentation | ✅ Complete | All docs rewritten for v3 architecture |
| Source Matrix | ✅ Complete | 142 sources verified, 6 regression profiles |

## Test Results

```bash
$ python -m pytest tests/unit/ -q --tb=short
379 passed in 4.11s
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Engines | 3 (scrapling, opencli, cloakbrowser) |
| MCP Tools | 13 |
| Verified Sources | 142 |
| Unit Tests | 379 |
| Pipeline Steps | 7 (classify → expand → discover → fetch → extract → score → bundle) |
| Credential Platforms | cookie extraction + encrypted YAML storage + engine injection |

## Next Steps

### Phase 1 — Agent Benchmark Suite
- Design 20+ agent evaluation tasks
- Coverage: search, fetch, research, interact, credential, error recovery
- Automated scoring script

### Phase 2 — Startup Auto-Recovery
- Windows Service registration for MCP server
- Engine failure auto-recovery + notification

### Phase 3 — Release
- pyproject.toml + PyPI publishing
- GitHub Actions CI
- Docker one-click deployment

### Phase 4 — Capability Expansion
- More site adapters (142+)
- Browser fingerprint rotation
- Agent Reach credential sync protocol
