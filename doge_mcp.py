#!/usr/bin/env python3
"""Modular MCP server entry point.

Canonical doge-db MCP entry point.
Usage:
    python doge_mcp.py --transport stdio
    python doge_mcp.py --transport sse --host 127.0.0.1 --port 8902
"""

from pathlib import Path
import site

_SRC = Path(__file__).resolve().parent / "src"
site.addsitedir(str(_SRC))

from doge.interfaces.mcp.server import main

if __name__ == "__main__":
    main()
