# MCP Reference Entry

The authoritative MCP server/tool reference remains [../MCP_SERVER.md](../MCP_SERVER.md).

This page provides a stable lower-case reference path while preserving the
existing uppercase file used by ADRs, CDDs, and operator docs.

Important entrypoints:

- Repo-root MCP entrypoint: `doge_mcp.py`
- Modular server: `src/doge/interfaces/mcp/server.py`
- Windows stdio helper: `scripts/mcp_stdio.bat`
- POSIX stdio helper: `scripts/mcp_stdio.sh`
- Windows SSE helper: `scripts/start_mcp_sse.bat`
- POSIX SSE helper: `scripts/start_mcp_sse.sh`

The server supports stdio and SSE transports. It is local-first and defaults to
loopback for network transport.
