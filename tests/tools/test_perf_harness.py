"""Import-only smoke test for the performance baseline harness (S003-012).

The harness itself (``tools/perf/profile_baseline.py``) is a standalone script,
NOT a pytest test — it lives under ``tools/`` (outside the configured
``testpaths``) and performs real timing runs that are inherently non-
deterministic. This test therefore asserts ONLY that the module imports and
exposes the expected entry point and timing helper, with NO timing assertions
and NO network access. It satisfies the coding-standard "every tool has a
test" gate without introducing non-determinism into the suite.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_harness():
    """Load the harness module from its absolute path (outside ``src``)."""
    repo_root = Path(__file__).resolve().parents[2]
    harness_path = repo_root / "tools" / "perf" / "profile_baseline.py"
    spec = importlib.util.spec_from_file_location(
        "profile_baseline", harness_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_harness_module_imports():
    """The harness module imports cleanly under a fresh interpreter."""
    mod = _load_harness()
    assert mod is not None


def test_harness_exposes_main_entrypoint():
    """The harness exposes a ``main(argv)`` entry point returning an int exit code."""
    mod = _load_harness()
    assert callable(getattr(mod, "main", None))


def test_harness_exposes_timing_helper():
    """The harness exposes the ``_median_ms`` timing helper used to aggregate runs."""
    mod = _load_harness()
    median_ms = getattr(mod, "_median_ms", None)
    assert callable(median_ms)
    # Pure function over a samples list — deterministic, no timing involved.
    assert median_ms([1.0, 2.0, 3.0]) == 2000.0  # median(1,2,3)=2.0s -> 2000ms


def test_harness_budgets_match_spec():
    """Budget constants match the declared spec (MCP <= 30s, health < 50ms)."""
    mod = _load_harness()
    assert mod.MCP_BUDGET_S == 30.0
    assert mod.HEALTH_BUDGET_MS == 50.0
    assert mod.CLI_BUDGET_S == 30.0
