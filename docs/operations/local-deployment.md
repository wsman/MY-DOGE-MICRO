# Local Deployment

MY-DOGE-MICRO is designed for local workstation operation. The canonical
operator runbook remains [runbook.md](runbook.md);
this page is the concise deployment entry.

## Default Surfaces

| Surface | Command | Default bind |
|---------|---------|--------------|
| FastAPI | `python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901` | `127.0.0.1:8901` |
| MCP stdio | `scripts\mcp_stdio.bat` or `./scripts/mcp_stdio.sh` | stdio |
| MCP SSE | `scripts\start_mcp_sse.bat` or `./scripts/start_mcp_sse.sh` | `127.0.0.1:8902` |
| Web | `cd web && npm run dev` | Vite dev server |
| PyQt | `python src/interface/dashboard.py` | local desktop window |

## Safety Boundary

The HTTP API and MCP SSE surfaces are intended to bind loopback. Remote bind,
enterprise auth, secret provider rollout, SIEM/WORM, and SDK publication remain
controlled validation paths, not production readiness proof.

## Before Running

1. Install the package with `pip install -e .`.
2. Confirm local databases under `DOGE_DB_DIR` or allow the product to create
   local state as workflows run.
3. Export `DEEPSEEK_API_KEY` only when using LLM macro paths.
4. Keep `MOONSHOT_API_KEY` optional unless running live Kimi validation.

See [../guides/getting-started.md](../guides/getting-started.md) for the longer first-run
walkthrough.
