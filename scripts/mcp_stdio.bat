@echo off
setlocal enabledelayedexpansion

rem Resolve script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

rem Use project venv if present, otherwise fallback to python in PATH
if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

"%PYTHON%" "%PROJECT_ROOT%\mcp_server.py" --transport stdio %*
