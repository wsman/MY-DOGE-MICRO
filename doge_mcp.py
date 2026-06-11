#!/usr/bin/env python3
"""Modular MCP server entry point.

Replaces the monolithic mcp_server.py with the fully modular version.
Usage:
    python doge_mcp.py --transport stdio
    python doge_mcp.py --transport sse --host 127.0.0.1 --port 8902
"""
import sys

# Ensure the src/ directory is on the path (fallback for non-editable installs)
import os
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.join(_PROJECT_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src"))

from doge.interfaces.mcp.server import main

if __name__ == "__main__":
    main()
