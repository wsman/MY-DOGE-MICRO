"""Output-parity tests: modular MCP server vs the legacy ``mcp_server.py`` monolith.

Purpose: prove the modular server
(``src/doge/interfaces/mcp/tools/*`` — the LIVE MCP path) is a byte-for-byte
drop-in for the legacy monolith (``mcp_server.py`` at repo root), so that
deleting the monolith in Batch-6 is provably safe. For EACH of the 6 tools the
MCP surface exposes (``query_stock``, ``stock_overview``, ``rsrs_ranking``,
``market_breadth``, ``volume_anomalies``, ``list_views``) we call the LEGACY
impl (``import mcp_server``; ``await mcp_server.<tool>(...)``) AND the MODULAR
impl (``from doge.interfaces.mcp.tools.<sub> import <tool>``) on the SAME
representative input and assert the outputs are EQUAL.

These are ``@pytest.mark.integration`` tests: they run against the operator's
populated local DuckDB (analytical views) + SQLite research DB (notes). They are
skipped automatically when that live market DB / its views are absent, and CI
can exclude them with ``-m 'not integration'``.

Divergence handling (qa-lead guidance): when an assertion fails, we investigate
whether it is a real regression or a non-deterministic bit (timestamps, row
order). Real, small modular divergences (empty-data markers, formatting) are
FIXED in the modular tool so modular == legacy EXACTLY; genuinely
non-deterministic outputs are normalized in-test and recorded in ``deferred``.
As of this writing all 6 tools hold byte-for-byte parity on the live DB.
"""
import sys

import pytest

# ── Live-DB skip guard ───────────────────────────────────────────────────
# Mirror the convention ``tests/test_mcp_tools.py`` uses for its integration
# tests: they run against the operator's local DuckDB + SQLite. Here we add an
# explicit probe so environments without the market DB skip cleanly instead of
# erroring. The probe opens the configured DuckDB read-only and confirms the
# analytical views are DEFINED (we do not query a view — the views reference
# CN/US tables that the tool runtime ATTACHes into the connection, so a bare
# read-only open cannot see them; checking the view *catalogue* is the right
# availability signal). Any failure (missing file, no views, duckdb import
# error) => skip.
_LIVE_DB_AVAILABLE = True
_SKIP_REASON = ""
try:
    from doge.config.settings import get_settings  # noqa: E402

    _duckdb_path = get_settings().db.duckdb
    if not _duckdb_path.exists():
        _LIVE_DB_AVAILABLE = False
        _SKIP_REASON = (
            f"requires live market DB at {_duckdb_path} (not found); "
            "populate via a market-data scan before running"
        )
    else:
        import duckdb as _duckdb  # noqa: E402

        _probe = _duckdb.connect(str(_duckdb_path), read_only=True)
        _views = {
            row[0]
            for row in _probe.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_type='VIEW'"
            ).fetchall()
        }
        _probe.close()
        _required = {
            "vw_daily_enriched_cn",
            "vw_market_breadth_cn",
            "vw_rsrs_ranking_cn",
            "vw_volume_anomalies_cn",
        }
        if not _required.issubset(_views):
            _LIVE_DB_AVAILABLE = False
            _SKIP_REASON = (
                f"requires live market DB views; missing: {_required - _views}"
            )
except Exception as _exc:  # pragma: no cover - environment-dependent
    _LIVE_DB_AVAILABLE = False
    _SKIP_REASON = f"requires live market DB / views: {type(_exc).__name__}: {_exc}"


# ── Tool imports ─────────────────────────────────────────────────────────
# Legacy: the monolith exposes the 6 async tool fns as module attributes
# (FastMCP's ``@mcp.tool()`` + ``@_timed`` both return the wrapped async fn).
import mcp_server as legacy  # noqa: E402

# Modular: import the concrete async fns directly from their submodules. The
# package ``__init__`` re-exports function names that shadow the submodule
# attribute on the parent package, so ``from ...tools import query_stock``
# yields the FUNCTION — fine here, we only need the callable.
from doge.interfaces.mcp.tools.query_stock import query_stock, stock_overview  # noqa: E402
from doge.interfaces.mcp.tools.ranking import market_breadth, rsrs_ranking  # noqa: E402
from doge.interfaces.mcp.tools.anomaly import volume_anomalies  # noqa: E402
from doge.interfaces.mcp.tools.views import list_views as mod_list_views  # noqa: E402


pytestmark = pytest.mark.integration

# Skip the WHOLE module when the live DB / views are unavailable. We surface
# the captured reason so a developer on a fresh checkout knows to populate.
if not _LIVE_DB_AVAILABLE:
    pytestmark = [
        pytest.mark.integration,
        pytest.mark.skip(reason=_SKIP_REASON),
    ]


# Representative inputs chosen to be deterministic on a populated DB: small
# LIMITs so output is stable, and a real CN ticker (600000.SH) that every
# market-data scan writes. These mirror the integration probes in
# ``tests/test_mcp_tools.py``.
_REPR_INPUTS = [
    # (label, legacy callable, modular callable, args, kwargs)
    (
        "query_stock",
        legacy.query_stock,
        query_stock,
        ("600000", "cn", 5),
        {},
    ),
    (
        "stock_overview",
        legacy.stock_overview,
        stock_overview,
        ("600000", "cn"),
        {},
    ),
    (
        "rsrs_ranking",
        legacy.rsrs_ranking,
        rsrs_ranking,
        ("cn", 5),
        {},
    ),
    (
        "market_breadth",
        legacy.market_breadth,
        market_breadth,
        ("cn", 5),
        {},
    ),
    (
        "volume_anomalies",
        legacy.volume_anomalies,
        volume_anomalies,
        (3.0, 5),
        {},
    ),
    (
        "list_views",
        legacy.list_views,
        mod_list_views,
        (),
        {},
    ),
]


def _first_diff(legacy_out: str, modular_out: str) -> str:
    """Return a human-readable description of the first divergent line.

    Returns an empty string when the two strings are identical. Used to make
    parity-failure diagnostics actionable (the qa-lead's 'investigate every
    failure' step).
    """
    if legacy_out == modular_out:
        return ""
    ll = legacy_out.splitlines()
    ml = modular_out.splitlines()
    for i in range(max(len(ll), len(ml))):
        a = ll[i] if i < len(ll) else "<missing>"
        b = ml[i] if i < len(ml) else "<missing>"
        if a != b:
            return f"line {i}: legacy={a!r} modular={b!r}"
    return f"length differs: legacy={len(ll)} lines modular={len(ml)} lines"


@pytest.mark.integration
class TestModularLegacyParity:
    """Assert each modular tool is a byte-for-byte drop-in for the legacy one."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "label,legacy_fn,modular_fn,args,kwargs",
        _REPR_INPUTS,
        ids=[row[0] for row in _REPR_INPUTS],
    )
    async def test_modular_tool_matches_legacy_output(
        self, label, legacy_fn, modular_fn, args, kwargs
    ):
        # Arrange / Act — call BOTH impls on the identical representative input.
        legacy_out = await legacy_fn(*args, **kwargs)
        modular_out = await modular_fn(*args, **kwargs)

        # Assert — modular must match legacy exactly. On failure, surface the
        # first divergent line so the regression is immediately diagnosable.
        # (Passing this suite is the evidence Batch-6 needs to delete
        # mcp_server.py.)
        diff = _first_diff(legacy_out, modular_out)
        assert legacy_out == modular_out, (
            f"{label}: modular output diverges from legacy. {_first_diff(legacy_out, modular_out) or '(see diff)'}\n"
            f"--- LEGACY ---\n{legacy_out}\n"
            f"--- MODULAR ---\n{modular_out}\n"
        )
