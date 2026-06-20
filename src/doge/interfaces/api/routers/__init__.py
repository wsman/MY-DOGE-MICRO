"""Canonical FastAPI routers for the MY-DOGE API interface layer."""

from doge.interfaces.api.routers import agent, analysis, config, data, documents, macro, notes, scan

__all__ = ["agent", "analysis", "config", "data", "documents", "macro", "notes", "scan"]
