#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${PROJECT_ROOT}/venv/bin/python" ]]; then
    PYTHON="${PROJECT_ROOT}/venv/bin/python"
elif [[ -f "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
else
    PYTHON="python3"
fi

export DOGE_DB_DIR="${DOGE_DB_DIR:-${PROJECT_ROOT}/data}"
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

HOST="${MCP_HOST:-127.0.0.1}"
PORT="${MCP_PORT:-8902}"

echo "Starting MY-DOGE MCP Server (SSE) on ${HOST}:${PORT}"
exec "${PYTHON}" "${PROJECT_ROOT}/doge_mcp.py" --transport sse --host "${HOST}" --port "${PORT}"
