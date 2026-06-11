# Source Pytest Evidence

> **Generated**: 2026-06-11
> **Source repository**: `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO`
> **Command**: `pytest`
> **Result**: PASS

## Environment

| Field | Value |
|-------|-------|
| Platform | Windows |
| Python | 3.12.12 |
| pytest | 9.0.1 |
| Config | `pyproject.toml` |
| Test path | `tests` |

## Summary

```text
collected 88 items
88 passed, 2 warnings in 12.76s
```

## Coverage by Test File

| Test File | Result |
|-----------|--------|
| `tests/test_database.py` | Passed |
| `tests/test_mcp_tools.py` | Passed |
| `tests/test_transport.py` | Passed |

## Warnings

- `websockets.legacy` is deprecated.
- `websockets.server.WebSocketServerProtocol` is deprecated through Uvicorn websocket protocol imports.

## Import Interpretation

The imported source state has working Python test coverage for database behavior, MCP tools, and transport behavior. The warnings should be tracked as dependency-upgrade risk, but they do not block the metadata import.
