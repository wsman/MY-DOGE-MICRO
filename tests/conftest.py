"""pytest shared fixtures."""
import pytest


def pytest_configure(config):
    """Register custom markers used across the suite."""
    config.addinivalue_line(
        "markers",
        "integration: end-to-end tests that hit the operator's local live "
        "DB (DuckDB views + SQLite research DB). Skipped automatically when "
        "the live DB / views are absent; excluded from CI via -m 'not integration'.",
    )
