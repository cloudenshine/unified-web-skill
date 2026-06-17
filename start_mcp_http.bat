@echo off
REM Unified Web Skill MCP Server — HTTP/SSE 启动器
REM 端口 8000，启动后托盘运行；停止请运行 stop_unified_web_mcp.bat

cd /d "E:\claude_work\g\unified-web-skill"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] venv missing. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "logs" mkdir logs

REM Stop any old instances first
for /f "tokens=2" %%i in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [INFO] Killing old listener on :8000 PID=%%i
    taskkill /F /PID %%i >nul 2>&1
)

echo [INFO] Starting unified-web-skill MCP server in HTTP/SSE mode on :8000 ...
set FORCE_HTTP=1
start "unified-web-skill-mcp" /B .venv\Scripts\python.exe -m app.mcp_server

REM Wait for /health to come up
set /a n=0
:WAIT_LOOP
set /a n+=1
if !n! gtr 15 (
    echo [WARN] Server did not respond to /health within 15s
    goto :END
)
timeout /t 1 /nobreak >nul
curl -sf http://127.0.0.1:8000/health >nul 2>&1 && (
    echo [OK] Server up on http://127.0.0.1:8000
    echo [OK] /sse ready for MCP clients
    goto :END
)
goto :WAIT_LOOP

:END
exit /b 0
