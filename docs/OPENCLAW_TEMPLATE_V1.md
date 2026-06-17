# OpenClaw Template V1

Use this template when registering `unified-web-skill` as the only agent-facing web MCP server.

## `openclaw.json` Example

```json
{
  "mcp": {
    "servers": {
      "unified-web-skill": {
        "command": "C:\\Python312\\python.exe",
        "args": ["-m", "app.mcp_server", "--stdio"],
        "cwd": "E:\\claude_work\\g\\unified-web-skill",
        "env": {
          "OUTPUT_DIR": "E:\\claude_work\\g\\unified-web-skill\\outputs",
          "CLOAK_BROWSER_BASE_URL": "http://127.0.0.1:9222",
          "CLOAK_BROWSER_ENABLED": "true",
          "CLOAK_MANAGER_BASE_URL": "http://127.0.0.1:8080",
          "CLOAK_MANAGER_ENABLED": "true",
          "CLOAK_BROWSER_BASE_URL": "http://127.0.0.1:9222",
          "CLOAK_BROWSER_ENABLED": "true",
          "RESIDENTIAL_PROXY_READY": "false",
          "OPENCLI_BIN": "C:\\Users\\Admin\\AppData\\Roaming\\npm\\opencli.cmd",
          "OPENCLI_BIN": "C:\\Users\\Admin\\AppData\\Roaming\\npm\\opencli.cmd"
        }
      }
    }
  }
}
```

## Policy

- Only expose `unified-web-skill` to agents.
- Do not separately expose engines as tools; use the MCP tool interface instead.
- Keep the high-level tool contract stable.

## Expected Tool Surface

- `web_search`
- `web_fetch`
- `web_interact`
- `research_and_collect`
- `web_profile_list`
- `web_profile_use`



