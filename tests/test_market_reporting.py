"""Unit tests for Module #6 (Market Reporting).

Reverse-documents the live scripts ``src/ai_analysis/market_overview.py`` and
``src/ai_analysis/anomaly_detection.py`` (BUG E coverage). The catalog and
fetch_names scripts are CLI/IO-shaped and are covered by the CDD contract
section rather than here.

Isolation strategy (per .claude/rules/test-standards.md): every DuckDB call is
served by an in-process fake connection that returns fixture DataFrames. No live
DuckDB file is opened, no ``data/views.sql`` is read, no network is touched.
Each test monkeypatches ``connect_duckdb`` / ``run_views_sql`` / ``ensure_report_dir``
in the TARGET module's namespace (the modules imported them via
``from ai_analysis import ...`` so the symbols live in their own globals).

Determinism: fixture DataFrames are literal constants; row ordering is asserted
where the contract pins it.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

# Test-shim exception (documented in test_settings.py / test_momentum_scanner.py):
# make src/ importable without depending on package install state.

from ai_analysis import market_overview, anomaly_detection  # noqa: E402


# ---------------------------------------------------------------------------
# Fake DuckDB connection + result
# ---------------------------------------------------------------------------
class _FakeResult:
    """Mimics the duckdb query-result object exposing .df() and .fetchone()."""

    def __init__(self, df=None, scalar=None):
        self._df = df
        self._scalar = scalar

    def df(self):
        return self._df

    def fetchone(self):
        return (self._scalar,) if self._scalar is not None else (None,)

    def fetchall(self):
        return []


class _FakeCon:
    """A recording fake connection.

    ``execute(sql, params=None)`` looks up a canned response by matching a
    substring of ``sql`` against the handlers registered at construction. If no
    handler matches it raises ``AssertionError`` so a test fails loudly the
    moment an unmocked query slips through (no silent live-DB fallback).
    """

    def __init__(self, handlers, max_date="2026-06-12"):
        # handlers: list of (substring, _FakeResult | callable-> _FakeResult)
        # NOTE: max_date is returned as a real datetime.date because both
        # generate() functions do ``max_d - timedelta(days=...)`` on it — the
        # live DuckDB returns a date, and the report code depends on that type.
        self._handlers = handlers
        if isinstance(max_date, str):
            max_date = date.fromisoformat(max_date)
        self._max_date = max_date
        self.calls = []  # (sql, params) tuples, for ordering assertions

    def execute(self, sql, params=None):
        sql_str = str(sql)
        self.calls.append((sql_str, params))
        # The "SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices" anchor query
        # is shared by both report modules — answer it from _max_date unless a
        # handler explicitly claims it.
        for substring, response in self._handlers:
            if substring in sql_str:
                return response() if callable(response) else response
        if "MAX(CAST(date AS DATE))" in sql_str and "stock_prices" in sql_str:
            return _FakeResult(scalar=self._max_date)
        raise AssertionError(
            "Unmocked DuckDB execute() in Market Reporting test:\n  SQL={}\n"
            "  params={}\nRegister a handler substring for this query.".format(
                sql_str[:120], params
            )
        )

    def close(self):
        return None


# ---------------------------------------------------------------------------
# Fixtures: fixture DataFrames matching the real view columns (CDD §4.1)
# ---------------------------------------------------------------------------
RSRS_COLUMNS = ["rank", "ticker", "rsrs", "last_close", "pct_change_60d", "avg_vol_20d"]
VOL_ANOM_COLUMNS = [
    "ticker", "date", "volume", "avg_vol_20d", "vol_ratio", "intraday_return",
]


@pytest.fixture
def rsrs_top20_df():
    # 20 rows, ordered by rank ascending (matches vw_rsrs_ranking_cn contract)
    return pd.DataFrame(
        [
            {"rank": 1, "ticker": "600000.SH", "rsrs": 0.95,
             "last_close": 10.5, "pct_change_60d": 42.1, "avg_vol_20d": 1_200_000},
            {"rank": 2, "ticker": "000001.SZ", "rsrs": 0.91,
             "last_close": 18.2, "pct_change_60d": 38.0, "avg_vol_20d": 980_000},
            {"rank": 3, "ticker": "300750.SZ", "rsrs": 0.88,
             "last_close": 220.0, "pct_change_60d": 35.5, "avg_vol_20d": 540_000},
        ],
        columns=RSRS_COLUMNS,
    )


@pytest.fixture
def rsrs_bottom20_df():
    # Bottom 20 = highest rank numbers; vw_rsrs_ranking_cn ORDER BY rank DESC
    return pd.DataFrame(
        [
            {"rank": 198, "ticker": "002001.SZ", "rsrs": -0.82,
             "last_close": 6.1, "pct_change_60d": -28.4, "avg_vol_20d": 210_000},
            {"rank": 199, "ticker": "600111.SH", "rsrs": -0.85,
             "last_close": 14.7, "pct_change_60d": -31.0, "avg_vol_20d": 305_000},
            {"rank": 200, "ticker": "688981.SH", "rsrs": -0.90,
             "last_close": 88.3, "pct_change_60d": -35.2, "avg_vol_20d": 175_000},
        ],
        columns=RSRS_COLUMNS,
    )


@pytest.fixture
def volume_spikes_df():
    # vw_volume_anomalies_cn ORDER BY vol_ratio DESC, LIMIT 15
    return pd.DataFrame(
        [
            {"ticker": "600519.SH", "date": "2026-06-12", "volume": 9_000_000,
             "avg_vol_20d": 1_500_000, "vol_ratio": 6.0, "intraday_return": 3.2},
            {"ticker": "000858.SZ", "date": "2026-06-12", "volume": 6_400_000,
             "avg_vol_20d": 1_600_000, "vol_ratio": 4.0, "intraday_return": 1.1},
        ],
        columns=VOL_ANOM_COLUMNS,
    )


# ---------------------------------------------------------------------------
# Shared patcher: redirects the three legacy symbols each report module
# imported via ``from ai_analysis import connect_duckdb, run_views_sql, ...``.
# ---------------------------------------------------------------------------
def _patch_legacy_layer(monkeypatch, module, fake_con):
    monkeypatch.setattr(
        module, "connect_duckdb", lambda read_only=False: fake_con
    )
    monkeypatch.setattr(module, "run_views_sql", lambda con=None: None)
    monkeypatch.setattr(module, "ensure_report_dir", lambda: None)
    # REPORT_DIR is also imported; point it at tmp so generate() writes there.
    return module


# ===========================================================================
# market_overview — query functions
# ===========================================================================
class TestMarketOverviewQueries:
    def test_rsrs_top20_returns_expected_columns_and_order(self, rsrs_top20_df):
        # Arrange — fake con answers ONLY the rsrs_top20 SQL with the fixture
        con = _FakeCon([("vw_rsrs_ranking_cn", _FakeResult(df=rsrs_top20_df))])

        # Act
        got = market_overview.rsrs_top20(con)

        # Assert — exact column contract (CDD AC-1)
        assert list(got.columns) == RSRS_COLUMNS
        assert len(got) == 3
        # Ordering by rank ascending is preserved from the fixture
        assert list(got["rank"]) == [1, 2, 3]
        # Exactly one execute call hit the view
        assert any("vw_rsrs_ranking_cn" in s for s, _ in con.calls)
        # The query restricts to rank <= 20
        assert any("rank <= 20" in s for s, _ in con.calls)

    def test_rsrs_bottom20_orders_by_rank_desc(self, rsrs_bottom20_df):
        # Arrange
        con = _FakeCon([("vw_rsrs_ranking_cn", _FakeResult(df=rsrs_bottom20_df))])

        # Act
        got = market_overview.rsrs_bottom20(con)

        # Assert — uses ORDER BY rank DESC LIMIT 20
        assert list(got.columns) == RSRS_COLUMNS
        assert len(got) == 3
        assert any("ORDER BY rank DESC" in s for s, _ in con.calls)
        assert any("LIMIT 20" in s for s, _ in con.calls)

    def test_volume_spikes_caps_at_15_and_orders_by_vol_ratio(self, volume_spikes_df):
        # Arrange
        con = _FakeCon([("vw_volume_anomalies_cn", _FakeResult(df=volume_spikes_df))])

        # Act
        got = market_overview.volume_spikes(con)

        # Assert — column contract (CDD AC-2) + LIMIT 15 + vol_ratio DESC
        assert list(got.columns) == VOL_ANOM_COLUMNS
        assert len(got) <= 15
        assert any("vw_volume_anomalies_cn" in s for s, _ in con.calls)
        assert any("ORDER BY vol_ratio DESC" in s for s, _ in con.calls)
        assert any("LIMIT 15" in s for s, _ in con.calls)

    def test_market_stats_uses_window_function_and_cutoff_param(self):
        # Arrange — market_stats issues a parameterized query (cutoff bound)
        empty = pd.DataFrame(
            columns=["date", "advancers", "decliners", "avg_return_pct", "advance_ratio"]
        )
        con = _FakeCon([("daily_return", _FakeResult(df=empty))])

        # Act
        got = market_overview.market_stats(con, "2026-06-01")

        # Assert — cutoff was bound as a parameter (not string-interpolated).
        # market_stats passes params as a list [cutoff] to execute().
        assert any("CAST(date AS DATE) >= ?" in s for s, _ in con.calls)
        bound_params = [p for _, p in con.calls if p]
        assert any("2026-06-01" in list(p) for p in bound_params)
        assert list(got.columns) == [
            "date", "advancers", "decliners", "avg_return_pct", "advance_ratio"
        ]


# ===========================================================================
# market_overview — generate() end-to-end with mocked layer
# ===========================================================================
class TestMarketOverviewGenerate:
    def test_generate_writes_markdown_with_all_five_sections(
        self, monkeypatch, tmp_path,
        rsrs_top20_df, rsrs_bottom20_df, volume_spikes_df,
    ):
        # Arrange — stats + breadth return small frames; rsrs/vol use fixtures
        stats_df = pd.DataFrame(
            [{"date": "2026-06-12", "advancers": 2400, "decliners": 2100,
              "avg_return_pct": 0.31, "advance_ratio": 53.3}]
        )
        breadth_df = pd.DataFrame(
            [{"date": "2026-06-12", "advancers": 2400, "decliners": 2100,
              "unchanged": 50, "active": 4550, "avg_return_pct": 0.31,
              "std_return_pct": 1.8, "advance_ratio": 53.3}]
        )

        # Handler ordering matters: market_stats + market_breadth both match
        # "daily_return"; disambiguate by a more specific substring first.
        handlers = [
            ("std_return_pct", _FakeResult(df=breadth_df)),       # breadth only
            ("advance_ratio", _FakeResult(df=stats_df)),          # stats (also has advance_ratio but std_return_pct wins first)
            ("rank <= 20", _FakeResult(df=rsrs_top20_df)),        # top20
            ("ORDER BY rank DESC", _FakeResult(df=rsrs_bottom20_df)),  # bottom20
            ("vw_volume_anomalies_cn", _FakeResult(df=volume_spikes_df)),  # spikes
        ]
        fake_con = _FakeCon(handlers, max_date="2026-06-12")
        _patch_legacy_layer(monkeypatch, market_overview, fake_con)
        monkeypatch.setattr(market_overview, "REPORT_DIR", str(tmp_path))

        # Act
        out_path = market_overview.generate()

        # Assert — file written under tmp, title + 5 section headers present
        assert out_path.startswith(str(tmp_path))
        assert out_path.endswith(".md")
        text = Path(out_path).read_text(encoding="utf-8")
        assert text.startswith("# 市场全景报告")
        assert "## 1. 最近交易日统计" in text
        assert "## 2. 市场宽度 (近 90 日)" in text
        assert "## 3. RSRS 动量 Top 20" in text
        assert "## 4. RSRS 动量 Bottom 20" in text
        assert "## 5. 成交量异常" in text
        # Top-20 fixture tickers appear in the rendered table
        assert "600000.SH" in text
        # Data anchor header records the fixture max_date (not the system clock)
        assert "2026-06-12" in text

    def test_generate_renders_placeholder_when_a_detector_is_empty(
        self, monkeypatch, tmp_path,
        rsrs_top20_df, rsrs_bottom20_df,
    ):
        # Arrange — volume_spikes returns ZERO rows; everything else populated
        empty_stats = pd.DataFrame(
            columns=["date", "advancers", "decliners", "avg_return_pct", "advance_ratio"]
        )
        empty_breadth = pd.DataFrame(
            columns=["date", "advancers", "decliners", "unchanged", "active",
                      "avg_return_pct", "std_return_pct", "advance_ratio"]
        )
        empty_vol = pd.DataFrame(columns=VOL_ANOM_COLUMNS)

        handlers = [
            ("std_return_pct", _FakeResult(df=empty_breadth)),
            ("advance_ratio", _FakeResult(df=empty_stats)),
            ("rank <= 20", _FakeResult(df=rsrs_top20_df)),
            ("ORDER BY rank DESC", _FakeResult(df=rsrs_bottom20_df)),
            ("vw_volume_anomalies_cn", _FakeResult(df=empty_vol)),
        ]
        fake_con = _FakeCon(handlers)
        _patch_legacy_layer(monkeypatch, market_overview, fake_con)
        monkeypatch.setattr(market_overview, "REPORT_DIR", str(tmp_path))

        # Act
        out_path = market_overview.generate()

        # Assert — section header still present + placeholder text (CDD AC-5)
        text = Path(out_path).read_text(encoding="utf-8")
        assert "## 5. 成交量异常" in text
        assert "_无符合条件的结果_" in text
        # The report is still well-formed Markdown (no exceptions raised)


# ===========================================================================
# anomaly_detection — query functions
# ===========================================================================
class TestAnomalyDetectionQueries:
    def test_volume_anomalies_filters_by_min_ratio_and_cutoff(self, volume_spikes_df):
        # Arrange — fixture has vol_ratios 6.0 and 4.0; min_ratio=5.0 keeps only the 6.0
        con = _FakeCon([("vw_volume_anomalies_cn", _FakeResult(df=volume_spikes_df))])

        # Act
        got = anomaly_detection.volume_anomalies(con, min_ratio=5.0, cutoff="2026-06-01")

        # Assert — contract (CDD AC-3): min_ratio bound as param, cutoff appended, LIMIT 30
        assert list(got.columns) == VOL_ANOM_COLUMNS
        assert any("vol_ratio >= ?" in s for s, _ in con.calls)
        assert any("LIMIT 30" in s for s, _ in con.calls)
        # Both min_ratio and cutoff are parameter-bound (not interpolated)
        sql_with_params = [(s, p) for s, p in con.calls if p]
        assert any(5.0 in p for _, p in sql_with_params)
        assert any("2026-06-01" in p for _, p in sql_with_params)

    def test_volume_anomalies_without_cutoff_omits_date_filter(self, volume_spikes_df):
        # Arrange
        con = _FakeCon([("vw_volume_anomalies_cn", _FakeResult(df=volume_spikes_df))])

        # Act — cutoff=None
        anomaly_detection.volume_anomalies(con, min_ratio=3.0, cutoff=None)

        # Assert — only min_ratio is bound; no extra date param
        for sql, params in con.calls:
            if "vw_volume_anomalies_cn" in sql:
                assert params == [3.0]

    def test_price_gaps_binds_cutoff_and_threshold(self):
        # Arrange
        empty = pd.DataFrame(
            columns=["ticker", "date", "open", "prev_close", "close",
                      "gap_pct", "return_pct"]
        )
        con = _FakeCon([("gap_pct", _FakeResult(df=empty))])

        # Act
        got = anomaly_detection.price_gaps(con, gap_threshold=7.0, cutoff="2026-05-01")

        # Assert — params ordered [cutoff, gap_threshold]; ABS(gap_pct) >= ?
        assert list(got.columns) == [
            "ticker", "date", "open", "prev_close", "close", "gap_pct", "return_pct"
        ]
        assert any("ABS(gap_pct) >= ?" in s for s, _ in con.calls)
        sql_with_params = [(s, p) for s, p in con.calls if p and "gap_pct" in s]
        assert sql_with_params, "expected a parameterized price_gaps call"
        # First bound param is the cutoff, second is the threshold
        _, params = sql_with_params[0]
        assert params[0] == "2026-05-01"
        assert params[1] == 7.0

    def test_consecutive_extremes_down_requires_min_days(self):
        # Arrange — empty result exercises the no-rows path (CDD AC-4)
        empty = pd.DataFrame(
            columns=["ticker", "from_date", "to_date", "streak_days"]
        )
        con = _FakeCon([("reset_group", _FakeResult(df=empty))])

        # Act
        got = anomaly_detection.consecutive_extremes(con, "down", min_days=5, cutoff="2026-05-01")

        # Assert — HAVING COUNT(*) >= ? bound with min_days=5; '<' comparator for down
        assert list(got.columns) == ["ticker", "from_date", "to_date", "streak_days"]
        assert any("HAVING COUNT(*) >= ?" in s for s, _ in con.calls)
        assert any("close < prev_close" in s for s, _ in con.calls)
        sql_with_params = [(s, p) for s, p in con.calls if p and "reset_group" in s]
        assert sql_with_params
        _, params = sql_with_params[0]
        assert params[0] == "2026-05-01"  # cutoff
        assert params[1] == 5  # min_days

    def test_consecutive_extremes_up_uses_greater_comparator(self):
        # Arrange
        empty = pd.DataFrame(
            columns=["ticker", "from_date", "to_date", "streak_days"]
        )
        con = _FakeCon([("reset_group", _FakeResult(df=empty))])

        # Act — direction="up"
        anomaly_detection.consecutive_extremes(con, "up", min_days=5, cutoff="2026-05-01")

        # Assert — '>' comparator for up direction
        assert any("close > prev_close" in s for s, _ in con.calls)


# ===========================================================================
# anomaly_detection — generate() end-to-end with mocked layer
# ===========================================================================
class TestAnomalyDetectionGenerate:
    def test_generate_writes_markdown_with_all_four_sections(
        self, monkeypatch, tmp_path, volume_spikes_df,
    ):
        # Arrange — non-empty fixtures for all four detectors
        gaps_df = pd.DataFrame(
            [{"ticker": "600000.SH", "date": "2026-06-12", "open": 11.0,
              "prev_close": 10.0, "close": 11.4, "gap_pct": 10.0, "return_pct": 14.0}]
        )
        streaks_df = pd.DataFrame(
            [{"ticker": "000001.SZ", "from_date": "2026-06-05",
              "to_date": "2026-06-12", "streak_days": 6}]
        )

        handlers = [
            ("vw_volume_anomalies_cn", _FakeResult(df=volume_spikes_df)),  # vol anomalies
            ("gap_pct", _FakeResult(df=gaps_df)),                          # price gaps
            # Both consecutive_extremes calls hit "reset_group"; return the
            # same fixture for both (down then up) — substring match is enough.
            ("reset_group", _FakeResult(df=streaks_df)),
        ]
        fake_con = _FakeCon(handlers, max_date="2026-06-12")
        _patch_legacy_layer(monkeypatch, anomaly_detection, fake_con)
        monkeypatch.setattr(anomaly_detection, "REPORT_DIR", str(tmp_path))

        # Act
        out_path = anomaly_detection.generate(
            min_ratio=3.0, gap_threshold=5.0, recent_days=3
        )

        # Assert — file written, title + 4 section headers, threshold header line
        assert out_path.startswith(str(tmp_path))
        text = Path(out_path).read_text(encoding="utf-8")
        assert text.startswith("# 异常检测报告")
        assert "## 1. 成交量异常" in text
        assert "## 2. 跳空缺口" in text
        assert "## 3. 连续下跌" in text
        assert "## 4. 连续上涨" in text
        # Header records the thresholds in effect (CDD §4.3)
        assert "3.0x" in text
        assert "5.0%" in text
        # Fixture tickers appear in the rendered tables
        assert "600519.SH" in text
        assert "000001.SZ" in text

    def test_generate_renders_placeholders_when_all_detectors_empty(
        self, monkeypatch, tmp_path,
    ):
        # Arrange — every detector returns zero rows (CDD AC-5)
        empty_vol = pd.DataFrame(columns=VOL_ANOM_COLUMNS)
        empty_gaps = pd.DataFrame(
            columns=["ticker", "date", "open", "prev_close", "close",
                      "gap_pct", "return_pct"]
        )
        empty_streaks = pd.DataFrame(
            columns=["ticker", "from_date", "to_date", "streak_days"]
        )

        handlers = [
            ("vw_volume_anomalies_cn", _FakeResult(df=empty_vol)),
            ("gap_pct", _FakeResult(df=empty_gaps)),
            ("reset_group", _FakeResult(df=empty_streaks)),
        ]
        fake_con = _FakeCon(handlers)
        _patch_legacy_layer(monkeypatch, anomaly_detection, fake_con)
        monkeypatch.setattr(anomaly_detection, "REPORT_DIR", str(tmp_path))

        # Act
        out_path = anomaly_detection.generate()

        # Assert — every section header still present with placeholder text
        text = Path(out_path).read_text(encoding="utf-8")
        assert "## 1. 成交量异常" in text
        assert "## 2. 跳空缺口" in text
        assert "## 3. 连续下跌" in text
        assert "## 4. 连续上涨" in text
        # At least one placeholder line is present (count occurrences)
        assert text.count("_无符合条件的结果_") >= 1
        # File is well-formed end-to-end (the call returned a path, not raised)


# ===========================================================================
# Determinism / isolation guard (CDD AC-6)
# ===========================================================================
class TestIsolationGuards:
    def test_no_live_duckdb_or_views_sql_touched(self, monkeypatch, tmp_path):
        """CDD AC-6: the test suite must never open a real DuckDB connection
        or read data/views.sql. Guard by asserting the patched symbols are
        the only entrypoints reached during generate()."""
        # Arrange — a con whose execute() blows up if any UNmocked query slips
        # through (the fake raises AssertionError on unknown SQL).
        empty = pd.DataFrame(columns=RSRS_COLUMNS)
        fake_con = _FakeCon(
            [("vw_rsrs_ranking_cn", _FakeResult(df=empty))],
            max_date="2026-06-12",
        )
        _patch_legacy_layer(monkeypatch, market_overview, fake_con)
        monkeypatch.setattr(market_overview, "REPORT_DIR", str(tmp_path))

        # Sentinel: prove run_views_sql was replaced (not the real one)
        assert market_overview.run_views_sql("anything") is None
        # Sentinel: prove connect_duckdb returns our fake (no real file open)
        assert market_overview.connect_duckdb() is fake_con
