#!/usr/bin/env python3
"""Performance baseline profiler for MY-DOGE-MICRO (story S003-012).

Standalone, re-runnable harness that measures the latency of the major query
surfaces against the declared performance budgets
(``standards/technical-preferences.md`` -> "Performance Budgets"):

    * The 6 MCP tool bodies (budget: <= 30 s, = ``TOOL_TIMEOUT`` in
      ``src/doge/interfaces/mcp/server.py``).
    * FastAPI ``/api/health`` (budget: baseline; CORS preflight < 50 ms).
    * CLI ``rsrs --top 10`` subprocess (budget: baseline; exit code must be 0).

Methodology
-----------
MCP tool **bodies** are timed directly (``asyncio.run(...)`` on the tool-module
async functions) rather than through the MCP stdio transport. The ``@mcp.tool``
wrapper adds only validation + the ``_timed`` decorator, and MCP stdio framing
adds negligible milliseconds, so the tool-body latency is the 30 s-budget-
relevant number. The transport layers are not the budget surface.

Inputs are deterministic (fixed ticker ``000001.SZ``, market ``cn``, fixed
``days``/``top``); only timings vary. One warmup call is run per surface (DuckDB
materializes analytical views on first connection), then each surface is
measured ``N`` times and the **median** is reported.

Local-only invariant
--------------------
Every surface reads from the local DuckDB / SQLite stores via the composition
root (``doge.core.services.composition``). No network source (yfinance /
akshare / opentdx) is invoked. This is verified by reading the tool modules and
the services they delegate to (see the evidence report).

This module is NOT a pytest test (no ``test_`` functions, not collected by
``pytest`` -- it lives under ``tools/``, outside the configured test roots).
Verify with::

    python -m pytest -q --collect-only 2>&1 | grep profile_baseline   # empty

Usage
-----
::

    python tools/perf/profile_baseline.py

Exit code is 0 on success (every profiled surface ran without error and
returned valid data), non-zero if any surface errored or returned empty data
(an "errored fast tool" is NOT a pass -- constraint #4).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable

# ── Path bootstrap (mirrors tests/test_api_routers.py) ──────────────────────
# The operator's site-packages may contain a .pth pointing at a sibling project
# (MY-DOGE-PRO) whose ``src`` package shadows this one. Strip polluting entries
# and insert ONLY this project's root so local package imports resolve here.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]
sys.path.insert(0, str(_PROJECT_ROOT))

# Budgets (from standards/technical-preferences.md "Performance Budgets" +
# src/doge/interfaces/mcp/server.py TOOL_TIMEOUT).
MCP_BUDGET_S = 30.0          # common local MCP query
HEALTH_BUDGET_MS = 50.0      # CORS preflight / health baseline (FastAPI)
CLI_BUDGET_S = 30.0          # CLI bounded to the same envelope as MCP

# Deterministic profiling inputs (timings vary; inputs do not).
TICKER = "000001.SZ"
MARKET = "cn"
DAYS = 20
TOP = 20
BREADTH_DAYS = 10
MIN_RATIO = 3.0
CLI_TOP = 10

# How many measured runs (after warmup) per surface. Median is reported.
DEFAULT_RUNS = 5


# ── Timing primitives ──────────────────────────────────────────────────────
def _median_ms(samples_s: list[float]) -> float:
    """Median of a list of seconds-samples, returned in milliseconds."""
    return statistics.median(samples_s) * 1000.0


def _fmt_ms(ms: float) -> str:
    return f"{ms:8.2f}"


def _verdict(measured_ms: float, budget_ms: float, ok: bool) -> str:
    """PASS only if the surface succeeded AND is under budget."""
    if not ok:
        return "ERROR"
    return "PASS" if measured_ms <= budget_ms else "FAIL"


# ── Surface definitions ────────────────────────────────────────────────────
def _import_tools():
    """Import the 6 MCP tool-body async functions (lazy, after path bootstrap)."""
    from doge.interfaces.mcp.tools import (
        query_stock,
        stock_overview,
        rsrs_ranking,
        market_breadth,
        volume_anomalies,
        list_views,
    )
    return {
        "query_stock": lambda: query_stock(TICKER, MARKET, DAYS),
        "stock_overview": lambda: stock_overview(TICKER, MARKET),
        "rsrs_ranking": lambda: rsrs_ranking(MARKET, TOP),
        "market_breadth": lambda: market_breadth(MARKET, BREADTH_DAYS),
        "volume_anomalies": lambda: volume_anomalies(MIN_RATIO, TOP),
        "list_views": lambda: list_views(),
    }


def _validate_tool_result(name: str, result: Any) -> tuple[bool, str]:
    """A fast tool that ERRORED or returned empty is NOT a pass (constraint #4).

    Returns (ok, shape_description).
    """
    if not isinstance(result, str):
        return False, f"non-string result: {type(result).__name__}"
    if not result.strip():
        return False, "empty string"
    if result.startswith("Error:"):
        return False, f"error result: {result[:80]}"
    # Sentinel "no data" strings the tools return on empty result sets.
    no_data_markers = ("No data", "No anomalies")
    if result.strip() in no_data_markers:
        return False, "no-data sentinel"
    line_count = len([ln for ln in result.splitlines() if ln.strip()])
    return True, f"str len={len(result)} lines={line_count}"


async def _time_async(coro_factory: Callable[[], Any]) -> tuple[float, Any]:
    """Time a single async tool-body invocation; return (seconds, result)."""
    t0 = time.perf_counter()
    result = await coro_factory()
    elapsed = time.perf_counter() - t0
    return elapsed, result


def profile_mcp_tools(runs: int) -> list[dict]:
    """Profile the 6 MCP tool bodies. Returns one row dict per tool."""
    tools = _import_tools()
    rows: list[dict] = []
    for name, factory in tools.items():
        samples: list[float] = []
        shape = ""
        ok = True
        error = ""
        try:
            # Warmup (DuckDB materializes views on first connection).
            _, warm = asyncio.run(_time_async(factory))
            wok, shape = _validate_tool_result(name, warm)
            if not wok:
                ok = False
                error = f"warmup returned invalid data: {shape}"
            # Measured runs.
            for _ in range(runs):
                elapsed, result = asyncio.run(_time_async(factory))
                samples.append(elapsed)
                rok, rshape = _validate_tool_result(name, result)
                if not rok:
                    ok = False
                    error = f"measured run returned: {rshape}"
                    shape = rshape
                    break
        except Exception as exc:  # noqa: BLE001 -- surface any error explicitly
            ok = False
            error = f"{type(exc).__name__}: {exc}"
            samples = samples or [0.0]

        median_ms = _median_ms(samples)
        rows.append({
            "surface": f"mcp.tool:{name}",
            "median_ms": median_ms,
            "budget_ms": MCP_BUDGET_S * 1000.0,
            "verdict": _verdict(median_ms, MCP_BUDGET_S * 1000.0, ok),
            "runs": len(samples),
            "shape": shape or error,
            "ok": ok,
        })
    return rows


def profile_health(runs: int) -> list[dict]:
    """Profile FastAPI /api/health via Starlette TestClient (no socket)."""
    from starlette.testclient import TestClient
    from doge.interfaces.api import main as api_main

    client = TestClient(api_main.app)
    samples: list[float] = []
    shape = ""
    ok = True
    error = ""
    try:
        # Warmup (app startup + first DuckDB health-check connection).
        w = client.get("/api/health")
        if w.status_code != 200 or w.json().get("status") != "ok":
            ok = False
            error = f"warmup bad response: {w.status_code} {w.text[:80]}"
        shape = f"HTTP {w.status_code} body={w.json()}"
        for _ in range(runs):
            t0 = time.perf_counter()
            r = client.get("/api/health")
            samples.append(time.perf_counter() - t0)
            if r.status_code != 200 or r.json().get("status") != "ok":
                ok = False
                error = f"bad response: {r.status_code} {r.text[:80]}"
                break
    except Exception as exc:  # noqa: BLE001
        ok = False
        error = f"{type(exc).__name__}: {exc}"
        samples = samples or [0.0]

    median_ms = _median_ms(samples)
    return [{
        "surface": "fastapi:/api/health",
        "median_ms": median_ms,
        "budget_ms": HEALTH_BUDGET_MS,
        "verdict": _verdict(median_ms, HEALTH_BUDGET_MS, ok),
        "runs": len(samples),
        "shape": shape or error,
        "ok": ok,
    }]


def profile_cli(runs: int) -> list[dict]:
    """Profile the CLI ``rsrs --top 10`` subprocess (exit code must be 0)."""
    cli_path = str(_PROJECT_ROOT / "src" / "cli.py")
    py = sys.executable
    samples: list[float] = []
    shape = ""
    ok = True
    error = ""
    try:
        # Warmup (python interpreter + DuckDB cold start).
        w = subprocess.run(
            [py, cli_path, "rsrs", "--top", str(CLI_TOP)],
            capture_output=True, text=True, timeout=CLI_BUDGET_S,
        )
        if w.returncode != 0:
            ok = False
            error = f"warmup exit={w.returncode} stderr={w.stderr[:120]}"
        shape = f"exit={w.returncode} stdout_lines={len(w.stdout.splitlines())}"
        for _ in range(runs):
            t0 = time.perf_counter()
            r = subprocess.run(
                [py, cli_path, "rsrs", "--top", str(CLI_TOP)],
                capture_output=True, text=True, timeout=CLI_BUDGET_S,
            )
            samples.append(time.perf_counter() - t0)
            if r.returncode != 0:
                ok = False
                error = f"exit={r.returncode} stderr={r.stderr[:120]}"
                break
    except subprocess.TimeoutExpired:
        ok = False
        error = f"timeout after {CLI_BUDGET_S}s"
        samples = samples or [0.0]
    except Exception as exc:  # noqa: BLE001
        ok = False
        error = f"{type(exc).__name__}: {exc}"
        samples = samples or [0.0]

    median_ms = _median_ms(samples)
    return [{
        "surface": f"cli:rsrs --top {CLI_TOP}",
        "median_ms": median_ms,
        "budget_ms": CLI_BUDGET_S * 1000.0,
        "verdict": _verdict(median_ms, CLI_BUDGET_S * 1000.0, ok),
        "runs": len(samples),
        "shape": shape or error,
        "ok": ok,
    }]


# ── Reporting ──────────────────────────────────────────────────────────────
def _print_table(rows: list[dict]) -> None:
    """Print the budget-comparison table to stdout."""
    hdr = f"{'Surface':<32} {'Median (ms)':>12} {'Budget (ms)':>12} {'Verdict':>8}  Runs  Result shape"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(
            f"{r['surface']:<32} {_fmt_ms(r['median_ms']):>12} "
            f"{r['budget_ms']:>12.0f} {r['verdict']:>8}  {r['runs']:>4}  {r['shape']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MY-DOGE-MICRO performance baseline profiler (S003-012).",
    )
    parser.add_argument(
        "--runs", type=int, default=DEFAULT_RUNS,
        help=f"measured runs per surface after warmup (default {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--json", dest="json_path", default="",
        help="optional path to also write a machine-readable JSON snapshot",
    )
    args = parser.parse_args(argv)

    print("MY-DOGE-MICRO performance baseline profile")
    print(f"date={date.today().isoformat()}  python={platform.python_version()}")
    print(f"platform={platform.platform()}")
    print(f"inputs: ticker={TICKER} market={MARKET} days={DAYS} top={TOP} "
          f"breadth_days={BREADTH_DAYS} min_ratio={MIN_RATIO} cli_top={CLI_TOP}")
    print(f"runs per surface (post-warmup): {args.runs}")
    print(f"budgets: mcp/CLI <= {MCP_BUDGET_S:.0f}s, health < {HEALTH_BUDGET_MS:.0f}ms")
    print()

    print("[1/3] MCP tool bodies (budget <= 30000 ms) ...")
    rows = profile_mcp_tools(args.runs)
    print()
    print("[2/3] FastAPI /api/health (budget < 50 ms) ...")
    rows += profile_health(args.runs)
    print()
    print("[3/3] CLI rsrs (budget <= 30000 ms) ...")
    rows += profile_cli(args.runs)
    print()

    _print_table(rows)
    print()

    errors = [r for r in rows if not r["ok"]]
    fails = [r for r in rows if r["ok"] and r["verdict"] == "FAIL"]
    overall = "PASS" if not errors and not fails else (
        "ERROR" if errors else "FAIL"
    )
    print(f"Overall: {overall}  "
          f"({sum(1 for r in rows if r['verdict']=='PASS')} PASS, "
          f"{len(fails)} FAIL, {len(errors)} ERROR of {len(rows)} surfaces)")

    if args.json_path:
        snapshot = {
            "date": date.today().isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "inputs": {
                "ticker": TICKER, "market": MARKET, "days": DAYS, "top": TOP,
                "breadth_days": BREADTH_DAYS, "min_ratio": MIN_RATIO,
                "cli_top": CLI_TOP,
            },
            "budgets": {
                "mcp_s": MCP_BUDGET_S, "health_ms": HEALTH_BUDGET_MS,
                "cli_s": CLI_BUDGET_S,
            },
            "runs": args.runs,
            "surfaces": rows,
            "overall": overall,
        }
        Path(args.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_path).write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8",
        )
        print(f"JSON snapshot written to {args.json_path}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
