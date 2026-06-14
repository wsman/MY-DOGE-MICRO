"""Regression gate: only whitelisted test files may contain sys.path shims.

The editable install plus ``tool.pytest.ini_options.pythonpath = ["src"]``
means most test files no longer need ``sys.path.insert`` / ``sys.path.append``.
A previous cleanup attempt removed required shims and broke the suite; this
gate documents the permanent whitelist and fails loudly if a new executable
shim is introduced.

Determinism: pure filesystem grep — no network, no DB, no imports.
"""
import re
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parents[2]  # tests/unit/layer_gates -> tests/unit -> tests

# Match an actual sys.path.insert(...) or sys.path.append(...) call, allowing
# leading whitespace. This deliberately does NOT match the tokens when they
# appear inside docstrings, comments, or assertion messages of other gate tests.
_SHIM_RE = re.compile(r"^\s*sys\.path\.(?:insert|append)\s*\(")

# The only legitimate shims remaining in tests/. Each entry is a path relative
# to tests/ with a human-readable justification.
_ALLOWED_SHIMS: dict[str, str] = {
    "test_settings.py": (
        "Bootstrap exception: this file polices all other shims and must be "
        "runnable as a script before the editable install is guaranteed."
    ),
    "test_pyqt_smoke.py": (
        "src/interface/ is a flat directory with no __init__.py; PyQt modules "
        "do sibling imports that require the src/interface/ path on sys.path."
    ),
    "unit/storage/test_save_stock_data_custom_storage_write_error.py": (
        "Bare sibling imports from src/micro/ (e.g. 'import database') require "
        "src/micro/ on sys.path until rewritten to use importlib."
    ),
    "unit/storage/test_market_scanner_write_tolerance.py": (
        "Same bare sibling import pattern from src/micro/."
    ),
    "unit/micro/test_scanner_opentdx_optional.py": (
        "Manipulates sys.modules to simulate a clean process and imports "
        "micro/api as top-level packages; the shim keeps this deterministic."
    ),
}


def _grep_tests_for_sys_path_shims() -> dict[str, list[tuple[int, str]]]:
    """Return {relative_path: [(lineno, line), ...]} for every sys.path shim."""
    hits: dict[str, list[tuple[int, str]]] = {}
    if not _TESTS_DIR.exists():
        return hits
    for py in _TESTS_DIR.rglob("*.py"):
        rel = py.relative_to(_TESTS_DIR).as_posix()
        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        file_hits: list[tuple[int, str]] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _SHIM_RE.match(line):
                file_hits.append((lineno, line.strip()))
        if file_hits:
            hits[rel] = file_hits
    return hits


class TestTestSysPathShimGate:
    def test_only_whitelisted_test_files_contain_sys_path_shims(self):
        """Fail if any new sys.path shim appears in tests/."""
        hits = _grep_tests_for_sys_path_shims()
        unexpected = {
            rel: lines
            for rel, lines in hits.items()
            if rel not in _ALLOWED_SHIMS
        }
        assert unexpected == {}, (
            "Unexpected executable sys.path.insert/append shims found in tests/. "
            "Either remove the shim (preferred) or add it to _ALLOWED_SHIMS "
            "in this test with a documented justification:\n"
            + "\n".join(
                f"  {rel}:{lineno}: {line}"
                for rel, lines in unexpected.items()
                for lineno, line in lines
            )
        )

    @pytest.mark.parametrize("rel", list(_ALLOWED_SHIMS))
    def test_whitelisted_shim_file_still_exists(self, rel):
        """Sanity: whitelisted files were not deleted."""
        assert (_TESTS_DIR / rel).exists(), f"whitelisted shim file missing: {rel}"
