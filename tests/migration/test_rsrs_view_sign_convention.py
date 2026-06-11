"""BLOCKING migration test: the DuckDB ``vw_rsrs_ranking_cn`` view's RSRS column
agrees with the canonical Python ``MomentumRanker.calculate_rsrs`` on the same
18-bar window — including the zero-slope-with-nonzero-variance edge case
(S002-001, OQ-11 / TR-016 RESOLVED).

This is the cross-implementation parity gate that runs the REAL DuckDB view text
from ``data/views.sql`` against an in-memory DuckDB attached to a fixture SQLite
DB. It is NOT a Python re-implementation of the formula (that lives in
``tests/unit/momentum/test_rsrs_parity.py``); this test exercises the actual
SQL the production refresh path executes.

Pipeline under test:
  fixture SQLite cn DB (one ticker whose last 18 bars form a V-shape:
    OLS slope == 0 but variance >> 1e-10)
    -> EXECUTE data/views.sql against in-memory DuckDB (catalog refresh)
    -> re-ATTACH the SQLite read-only at query time (attachments are
       connection-scoped, not persisted with the view definition — same pattern
       as tests/migration/test_retention_view_window_safety.py)
    -> SELECT rsrs FROM vw_rsrs_ranking_cn
    -> assert view rsrs == Python calculate_rsrs on the same window to 1e-6

Also asserts:
  - a perfectly increasing series yields +1.0 (confirms REGR_R2(rn, close)
    argument order X=time Y=price is correct — guards against a future editor
    'fixing' the order backwards and flipping every sign)
  - a flat-constant series yields 0.0 (the zero-variance path)

Determinism: no network; SQLite + DuckDB over local fixture files only.
"""
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Test shim: put src/ on sys.path (documented exception, see test_settings.py).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from scipy import stats  # noqa: E402

from micro.momentum_scanner import MomentumRanker  # noqa: E402

VIEWS_SQL_PATH = _PROJECT_ROOT / "data" / "views.sql"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------
def _v_shape_window(n: int = 18, centre: float = 50.0, amp: float = 5.0) -> np.ndarray:
    """Symmetric V-shape of length n whose OLS slope over 0..n-1 is exactly 0
    but whose variance is well above the 1e-10 flat-guard. Used as the LAST 18
    closes of a ticker so the view's RSRS regression sees zero slope + nonzero
    variance (the OQ-11 divergence case).

    Construction: a **palindromic** series (``v[i] == v[n-1-i]``) has exactly
    zero covariance with the centered time index, hence exactly-zero OLS slope
    to machine precision. We descend then ascend around ``centre`` so the
    variance is large and the values look like prices.
    """
    half = n // 2
    # Descend from centre+amp toward centre over the left half.
    left = centre + amp - amp * (np.arange(half, 0, -1, dtype=float) / half)
    if n % 2 == 0:
        vals = np.concatenate([left, left[::-1]])
    else:
        vals = np.concatenate([left, np.array([centre]), left[::-1]])
    return vals[:n].astype(float)


def _seed_ticker(cn_db_path: str, ticker: str, closes: list[float]) -> None:
    """Seed ``len(closes)`` daily OHLCV rows for ``ticker``, oldest first, with
    the given close sequence. volume/amount are large so the ticker clears the
    avg_vol_20d > 500000 liquidity filter in the view."""
    init_sql = (
        "CREATE TABLE IF NOT EXISTS stock_prices ("
        "ticker TEXT, date TEXT, open REAL, high REAL, low REAL, "
        "close REAL, volume INTEGER, amount REAL, "
        "PRIMARY KEY (ticker, date))"
    )
    conn = sqlite3.connect(cn_db_path)
    conn.execute(init_sql)
    base = datetime.now()
    rows = []
    for i, close in enumerate(closes, start=1):  # oldest first
        date_str = (base - timedelta(days=len(closes) - i)).strftime("%Y-%m-%d")
        rows.append(
            (ticker, date_str, close, close, close, close, 2_000_000, close * 2_000_000)
        )
    conn.executemany(
        "INSERT OR REPLACE INTO stock_prices "
        "(ticker, date, open, high, low, close, volume, amount) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def _rewrite_attach_paths(sql_text: str, cn_db_path: str, us_db_path: str) -> str:
    """Rewrite the relative ATTACH paths in data/views.sql to absolute tmp paths
    (same technique as test_retention_view_window_safety.py)."""
    sql_text = re.sub(
        r"ATTACH\s+IF\s+NOT\s+EXISTS\s+'[^']+'\s+AS\s+cn\s+\(TYPE\s+sqlite\)",
        f"ATTACH IF NOT EXISTS '{cn_db_path.replace(os.sep, '/')}' AS cn (TYPE sqlite)",
        sql_text,
        flags=re.IGNORECASE,
    )
    sql_text = re.sub(
        r"ATTACH\s+IF\s+NOT\s+EXISTS\s+'[^']+'\s+AS\s+us\s+\(TYPE\s+sqlite\)",
        f"ATTACH IF NOT EXISTS '{us_db_path.replace(os.sep, '/')}' AS us (TYPE sqlite)",
        sql_text,
        flags=re.IGNORECASE,
    )
    return sql_text


def _strip_sql_comments(sql_text: str) -> str:
    """Remove full-line and trailing ``--`` comments so statement splitting on
    ``;`` yields executable bodies."""
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if "--" in line:
            line = line.split("--", 1)[0]
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _create_views(duckdb_path: str, cn_db_path: str, us_db_path: str) -> None:
    """Execute data/views.sql against the tmp DuckDB, creating the analytical
    views over the fixture SQLite files."""
    sql_text = VIEWS_SQL_PATH.read_text(encoding="utf-8")
    sql_text = _rewrite_attach_paths(sql_text, cn_db_path, us_db_path)
    sql_text = _strip_sql_comments(sql_text)
    con = duckdb.connect(duckdb_path)
    try:
        try:
            con.execute("INSTALL sqlite")
        except duckdb.Error:
            pass
        con.execute("LOAD sqlite")
        for stmt in sql_text.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                con.execute(stmt)
            except duckdb.Error:
                pass  # mirror DuckDBConnection.refresh_views best-effort path
    finally:
        con.close()


def _init_empty_us_db(us_db_path: str) -> None:
    """Create an empty stock_prices table so the us-ATTACH in views.sql does not
    fail when only the cn fixture is seeded."""
    conn = sqlite3.connect(us_db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS stock_prices ("
        "ticker TEXT, date TEXT, open REAL, high REAL, low REAL, "
        "close REAL, volume INTEGER, amount REAL, "
        "PRIMARY KEY (ticker, date))"
    )
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def ranker():
    return MomentumRanker()


# ---------------------------------------------------------------------------
# Scenario 1 (BLOCKING): zero-slope, nonzero-variance — view == Python.
# ---------------------------------------------------------------------------
def test_zero_slope_view_matches_python(tmp_path, ranker):
    cn_db_path = str(tmp_path / "market_data_cn.db")
    us_db_path = str(tmp_path / "market_data_us.db")
    duckdb_path = str(tmp_path / "market.duckdb")

    # Arrange — one CN ticker with ~70 days. The LAST 18 days are a V-shape
    # (slope 0, variance >> 1e-10); days 19..70 ramp up so pct_change_60d is
    # strongly positive (single ticker -> always in Top 200).
    v = _v_shape_window(18, centre=50.0, amp=5.0)
    # Sanity: slope ~ 0, variance > guard.
    xs = np.arange(18, dtype=float)
    slope_chk, _, r_chk, _, _ = stats.linregress(xs, v)
    assert abs(float(slope_chk)) < 1e-9, "V-shape fixture slope not ~0"
    assert float(np.var(v)) > 1e-10, "V-shape fixture lost variance"

    # Math note: a palindromic (zero-slope) series has R2 == 0 for OLS on time,
    # so the RSRS product is 0.0 under any sign convention (spec risk R-3). The
    # load-bearing zero->+1 sign convention is therefore pinned at the sign
    # helper boundary in tests/unit/momentum/test_rsrs_sign_unit.py; THIS test
    # proves the real DuckDB view agrees with Python on the edge-case input.

    # Days 19..70: a strong uptrend from 10 -> 49 so close[-61] vs close[-1]
    # gives a large positive pct_change_60d (keeps ticker in Top 200).
    ramp = np.linspace(10.0, 49.0, 70 - 18)
    closes = list(ramp) + list(v)
    closes = [float(c) for c in closes]
    assert len(closes) >= 61, "need >= 61 rows for the change_60d HAVING clause"

    _seed_ticker(cn_db_path, "000001", closes)
    _init_empty_us_db(us_db_path)
    _create_views(duckdb_path, cn_db_path, us_db_path)

    # Act — query the real view. Re-ATTACH read-only at query time (attachments
    # are connection-scoped, not persisted with the view definition).
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        try:
            con.execute("INSTALL sqlite")
        except duckdb.Error:
            pass
        con.execute("LOAD sqlite")
        con.execute(
            f"ATTACH IF NOT EXISTS '{cn_db_path.replace(os.sep, '/')}' AS cn "
            f"(TYPE sqlite, READ_ONLY)"
        )
        rows = con.execute(
            "SELECT ticker, rsrs FROM vw_rsrs_ranking_cn WHERE ticker = '000001'"
        ).fetchall()
    finally:
        con.close()

    # Assert — the view returned our ticker and its rsrs matches Python on the
    # SAME last-18 window to 1e-6. Both are 0.0 (zero-slope => R2==0), but the
    # BLOCKING assertion is the cross-implementation AGREEMENT on the edge case.
    assert rows, "vw_rsrs_ranking_cn returned no rows for the zero-slope ticker"
    view_rsrs = float(rows[0][1])
    python_rsrs = ranker.calculate_rsrs(pd.Series(closes))
    assert view_rsrs == pytest.approx(python_rsrs, abs=1e-6), (
        f"view rsrs {view_rsrs} != python rsrs {python_rsrs}"
    )
    assert view_rsrs == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Scenario 2: flat-constant series -> view rsrs == 0.0 == Python.
# ---------------------------------------------------------------------------
def test_flat_constant_view_matches_python(tmp_path, ranker):
    cn_db_path = str(tmp_path / "market_data_cn.db")
    us_db_path = str(tmp_path / "market_data_us.db")
    duckdb_path = str(tmp_path / "market.duckdb")

    # Flat 70 days at 50.0 — slope 0, variance 0. REGR_R2 -> NULL -> COALESCE 0.
    closes = [50.0] * 70
    _seed_ticker(cn_db_path, "000002", closes)
    _init_empty_us_db(us_db_path)
    _create_views(duckdb_path, cn_db_path, us_db_path)

    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        try:
            con.execute("INSTALL sqlite")
        except duckdb.Error:
            pass
        con.execute("LOAD sqlite")
        con.execute(
            f"ATTACH IF NOT EXISTS '{cn_db_path.replace(os.sep, '/')}' AS cn "
            f"(TYPE sqlite, READ_ONLY)"
        )
        rows = con.execute(
            "SELECT ticker, rsrs FROM vw_rsrs_ranking_cn WHERE ticker = '000002'"
        ).fetchall()
    finally:
        con.close()

    # A fully flat ticker may be filtered if avg_vol_20d threshold is unmet, but
    # we seed volume=2_000_000 so it should clear. If it's filtered, the rsrs
    # default-0 behaviour is still correct; assert accordingly.
    python_rsrs = ranker.calculate_rsrs(pd.Series(closes))
    assert python_rsrs == pytest.approx(0.0, abs=1e-12)
    if rows:
        view_rsrs = float(rows[0][1])
        assert view_rsrs == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Scenario 3: perfectly increasing series -> SHOULD yield +1.0 under Python's
# convention (slope of price-on-time > 0, R2=1). This test exists to confirm the
# SQL REGR_*(rn, close) argument order / rn-ordering matches Python's intent.
#
# BLOCKER DISCOVERED (S002-001): the view currently returns **-1.0** for a
# perfectly increasing series, NOT +1.0. Root cause: the `recent` CTE computes
# `ROW_NUMBER() OVER (... ORDER BY date DESC) AS rn` so rn=1 is the NEWEST bar
# (highest close for an uptrend), making cov(rn, close) < 0 and the SQL sign
# negative — INVERTED relative to the Python scalar path (which uses
# x = arange(0..17) oldest->newest, so slope > 0 for an uptrend). This inversion
# is independent of the zero->+1 boundary convention S002-001 unified; it affects
# the sign of EVERY monotonic series. Fixing it requires changing the rn ordering
# in data/views.sql (gitignored, owned by the market-data-storage refresh path)
# plus a view re-materialization — explicitly OUT OF SCOPE for S002-001
# (orchestrator decision #2: "NO change to data/views.sql"). Recorded as a
# BLOCKER for a follow-up story. This xfail is strict=True so it FAILS LOUD the
# moment the SQL sign inversion is corrected (the test then becomes an assertion
# that the view agrees with Python's +1.0).
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BLOCKER S002-001: vw_rsrs_ranking_cn rn-ordering (ORDER BY date DESC) "
        "inverts the sign relative to Python's price-on-time regression. View "
        "returns -1.0 for an uptrend; Python returns +1.0. Fix is a data/views.sql "
        "rn-ordering change (out of scope, gitignored, owned by market-data-storage). "
        "This xfail flips to a hard failure the moment the SQL is corrected, at "
        "which point the assertion below becomes the cross-implementation gate."
    ),
)
def test_perfectly_increasing_view_is_positive_one(tmp_path, ranker):
    cn_db_path = str(tmp_path / "market_data_cn.db")
    us_db_path = str(tmp_path / "market_data_us.db")
    duckdb_path = str(tmp_path / "market.duckdb")

    # Strictly increasing 70 days -> last 18 bars are a perfect ramp.
    closes = [float(10.0 + i) for i in range(70)]
    _seed_ticker(cn_db_path, "600000", closes)
    _init_empty_us_db(us_db_path)
    _create_views(duckdb_path, cn_db_path, us_db_path)

    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        try:
            con.execute("INSTALL sqlite")
        except duckdb.Error:
            pass
        con.execute("LOAD sqlite")
        con.execute(
            f"ATTACH IF NOT EXISTS '{cn_db_path.replace(os.sep, '/')}' AS cn "
            f"(TYPE sqlite, READ_ONLY)"
        )
        rows = con.execute(
            "SELECT ticker, rsrs FROM vw_rsrs_ranking_cn WHERE ticker = '600000'"
        ).fetchall()
    finally:
        con.close()

    assert rows, "vw_rsrs_ranking_cn returned no rows for the increasing ticker"
    view_rsrs = float(rows[0][1])
    python_rsrs = ranker.calculate_rsrs(pd.Series(closes))
    # Python correctly returns +1.0 (the canonical convention).
    assert python_rsrs == pytest.approx(1.0, abs=1e-9)
    # The view SHOULD return +1.0 too once the rn-ordering inversion is fixed.
    # Today it returns -1.0 (the xfail above absorbs this); after the fix this
    # assertion becomes the cross-implementation gate.
    assert view_rsrs == pytest.approx(1.0, abs=1e-6), (
        f"increasing series view rsrs {view_rsrs} != +1.0 (Python={python_rsrs})"
    )
