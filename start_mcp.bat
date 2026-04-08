@echo off
REM unified-web-skill MCP 服务启动脚本
REM 每次系统启动或手动运行此脚本来启动 Web 研究 MCP 服务

cd /d "E:\claude_work\g\unified-web-skill"

REM 检查 .env 文件是否存在
if not exist ".env" (
    copy .env.sample .env
    echo .env created from sample
)

echo Starting unified-web-skill MCP server on port 8000...
python -m app.mcp_server
