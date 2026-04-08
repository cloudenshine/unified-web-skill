# unified-web-skill MCP 服务启动 (PowerShell)
# 运行方式: .\start_mcp.ps1
# 或后台运行: Start-Process pwsh -ArgumentList "-File start_mcp.ps1" -WindowStyle Minimized

$skillDir = "E:\claude_work\g\unified-web-skill"
Set-Location $skillDir

# 确保 .env 存在
if (-not (Test-Path ".env")) {
    Copy-Item ".env.sample" ".env"
    Write-Host ".env created from .env.sample"
}

Write-Host "Starting unified-web-skill MCP server on http://localhost:8000 ..."
python -m app.mcp_server
