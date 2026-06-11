@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

if not defined DOGE_DB_DIR set "DOGE_DB_DIR=%PROJECT_ROOT%\data"
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

if not defined MCP_HOST set "MCP_HOST=127.0.0.1"
if not defined MCP_PORT set "MCP_PORT=8902"

echo Starting MY-DOGE MCP Server ^(SSE^) on %MCP_HOST%:%MCP_PORT%
"%PYTHON%" "%PROJECT_ROOT%\mcp_server.py" --transport sse --host %MCP_HOST% --port %MCP_PORT%
