"""Interface adapters for CLI, API, and MCP entrypoints.

Subpackages are intentionally not imported here. Eager imports trigger entrypoint
side effects such as MCP log setup during unrelated CLI/API tests.
"""

__all__ = ["api", "cli", "mcp"]
