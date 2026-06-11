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

export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

exec "${PYTHON}" "${PROJECT_ROOT}/mcp_server.py" --transport stdio "$@"
