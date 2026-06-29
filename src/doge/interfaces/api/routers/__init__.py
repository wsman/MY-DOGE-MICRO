"""Compatibility shims for legacy FastAPI routers.

Canonical implementations live under ``doge.interfaces.api_legacy.routers``.
"""

from doge.interfaces.api_legacy.routers import agent, analysis, config, data, documents, macro, notes, scan

__all__ = ["agent", "analysis", "config", "data", "documents", "macro", "notes", "scan"]
