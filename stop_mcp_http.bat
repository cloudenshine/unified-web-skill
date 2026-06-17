@echo off
REM Unified Web Skill MCP Server — 停止
for /f "tokens=2" %%i in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [INFO] Killing PID=%%i on :8000
    taskkill /F /PID %%i >nul 2>&1
)
echo [OK] Stopped (if was running)
exit /b 0
