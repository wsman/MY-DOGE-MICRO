"""pytest shared fixtures."""
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT_STR = str(_PROJECT_ROOT)
_POLLUTING_PATH_MARKERS = {
    "nev-ads-synthetic-data-factory",
    "MY-DOGE-PRO",
    "opendoge",
}

_clean_sys_path = [
    p for p in sys.path
    if p and not any(marker in p for marker in _POLLUTING_PATH_MARKERS)
]
sys.path[:] = [
    _PROJECT_ROOT_STR,
    *[p for p in _clean_sys_path if p != _PROJECT_ROOT_STR],
]

for module_name in list(sys.modules):
    if module_name == "src" or module_name.startswith("src.api"):
        module = sys.modules[module_name]
        module_file = getattr(module, "__file__", "") or ""
        if module_file and _PROJECT_ROOT_STR not in module_file:
            sys.modules.pop(module_name, None)


def pytest_configure(config):
    """Register custom markers used across the suite."""
    config.addinivalue_line(
        "markers",
        "integration: end-to-end tests that hit the operator's local live "
        "DB (DuckDB views + SQLite research DB). Skipped automatically when "
        "the live DB / views are absent; excluded from CI via -m 'not integration'.",
    )
