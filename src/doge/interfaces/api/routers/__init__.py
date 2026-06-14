"""Canonical FastAPI routers for the MY-DOGE API interface layer."""

from doge.interfaces.api.routers import analysis, config, data, macro, notes, scan

__all__ = ["analysis", "config", "data", "macro", "notes", "scan"]
