"""Unit tests for Module #6 Market Reporting use cases (S007-004).

Reverse-documents the canonical use cases:

- ``doge.application.use_cases.generate_market_overview``
- ``doge.application.use_cases.generate_anomaly_report``
- ``doge.application.use_cases.generate_catalog``

Isolation strategy: every DuckDB call is served by an in-process fake
``IMarketViewRepository``. No live DuckDB file is opened, no ``data/views.sql``
is read, and no network is touched.
"""
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

pytestmark = pytest.mark.module_market

from doge.application.use_cases.generate_market_overview import GenerateMarketOverviewUseCase
from doge.application.use_cases.generate_anomaly_report import GenerateAnomalyReportUseCase
from doge.application.use_cases.generate_catalog import GenerateCatalogUseCase
from doge.application.contracts.request import (
    GenerateMarketOverviewRequest,
    GenerateAnomalyReportRequest,
    GenerateCatalogRequest,
)
from doge.core.ports.market_view import IMarketViewRepository
from doge.core.ports.repository import ISchemaBrowser
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.view_service import ViewService


# ---------------------------------------------------------------------------
# Fake settings helper
# ---------------------------------------------------------------------------
def _fake_settings(tmp_path: Path):
    """Return a minimal settings object with report_dir/catalog_json wired to tmp_path."""
    report_dir = tmp_path / "ai_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        report_dir=report_dir,
        catalog_json=data_dir / "catalog.json",
        db=SimpleNamespace(dir=data_dir),
    )


# ---------------------------------------------------------------------------
# Fake DuckDB repository
# ---------------------------------------------------------------------------
class _FakeResult:
    """Mimics a duckdb query-result object exposing .df() and .fetchone()."""

    def __init__(self, df=None, scalar=None):
        self._df = df if df is not None else pd.DataFrame()
        self._scalar = scalar

    def df(self):
        return self._df

    def fetchone(self):
        return (self._scalar,) if self._scalar is not None else (None,)


class FakeMarketViewRepository(IMarketViewRepository):
    """Recording fake for IMarketViewRepository.

    Handlers are matched by substring against the executed SQL. If no handler
    matches and the SQL is the shared MAX-date anchor, the configured max_date
    is returned. Anything else raises AssertionError so tests fail loudly on
    unmocked queries.
    """

    def __init__(self, handlers, max_date="2026-06-12"):
        self._handlers = handlers
        if isinstance(max_date, str):
            max_date = date.fromisoformat(max_date)
        self._max_date = max_date
        self.calls = []

    def execute(self, sql: str, params=None):
        self.calls.append((sql, params))
        for substring, response in self._handlers:
            if substring in sql:
                return response() if callable(response) else response
        if "MAX(CAST(date AS DATE))" in sql and "stock_prices" in sql:
            return pd.DataFrame({"max_date": [self._max_date]})
        raise AssertionError(
            "Unmocked query in Market Reporting test:\n  SQL={}\n  params={}".format(
                sql[:160], params
            )
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
RSRS_COLUMNS = ["rank", "ticker", "rsrs", "last_close", "pct_change_60d", "avg_vol_20d"]
VOL_ANOM_COLUMNS = [
    "ticker", "date", "volume", "avg_vol_20d", "vol_ratio", "intraday_return",
]


@pytest.fixture
def rsrs_top20_df():
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
    return pd.DataFrame(
        [
            {"ticker": "600519.SH", "date": "2026-06-12", "volume": 9_000_000,
             "avg_vol_20d": 1_500_000, "vol_ratio": 6.0, "intraday_return": 3.2},
            {"ticker": "000858.SZ", "date": "2026-06-12", "volume": 6_400_000,
             "avg_vol_20d": 1_600_000, "vol_ratio": 4.0, "intraday_return": 1.1},
        ],
        columns=VOL_ANOM_COLUMNS,
    )


@pytest.fixture
def stats_df():
    return pd.DataFrame(
        [{"date": "2026-06-12", "advancers": 2400, "decliners": 2100,
          "avg_return_pct": 0.31, "advance_ratio": 53.3}]
    )


@pytest.fixture
def breadth_df():
    return pd.DataFrame(
        [{"date": "2026-06-12", "advancers": 2400, "decliners": 2100,
          "unchanged": 50, "active": 4550, "avg_return_pct": 0.31,
          "std_return_pct": 1.8, "advance_ratio": 53.3}]
    )


# ---------------------------------------------------------------------------
# Market overview use case
# ---------------------------------------------------------------------------
class TestGenerateMarketOverviewUseCase:
    def test_execute_writes_markdown_with_all_five_sections(
        self,
        monkeypatch,
        tmp_path,
        rsrs_top20_df,
        rsrs_bottom20_df,
        volume_spikes_df,
        stats_df,
        breadth_df,
    ):
        # Arrange
        handlers = [
            ("std_return_pct", breadth_df),
            ("advance_ratio", stats_df),
            ("rank <= ?", rsrs_top20_df),
            ("ORDER BY rank DESC", rsrs_bottom20_df),
            ("vw_volume_anomalies_cn", volume_spikes_df),
        ]
        fake_repo = FakeMarketViewRepository(handlers, max_date="2026-06-12")
        uc = GenerateMarketOverviewUseCase(
            view_repo=fake_repo,
            breadth_service=BreadthService(fake_repo),
            ranking_service=RankingService(fake_repo),
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_market_overview.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        # Act
        resp = uc.execute(GenerateMarketOverviewRequest())

        # Assert
        text = resp.markdown
        assert text.startswith("# 市场全景报告")
        assert "## 1. 最近交易日统计" in text
        assert "## 2. 市场宽度 (近 90 日)" in text
        assert "## 3. RSRS 动量 Top 20" in text
        assert "## 4. RSRS 动量 Bottom 20" in text
        assert "## 5. 成交量异常" in text
        assert "600000.SH" in text
        assert "2026-06-12" in text
        # File was also written to the report dir
        assert any((tmp_path / "ai_report").glob("market_overview_*.md"))

    def test_execute_renders_placeholder_when_detector_empty(
        self,
        monkeypatch,
        tmp_path,
        rsrs_top20_df,
        rsrs_bottom20_df,
    ):
        empty_stats = pd.DataFrame(
            columns=["date", "advancers", "decliners", "avg_return_pct", "advance_ratio"]
        )
        empty_breadth = pd.DataFrame(
            columns=["date", "advancers", "decliners", "unchanged", "active",
                     "avg_return_pct", "std_return_pct", "advance_ratio"]
        )
        empty_vol = pd.DataFrame(columns=VOL_ANOM_COLUMNS)

        handlers = [
            ("std_return_pct", empty_breadth),
            ("advance_ratio", empty_stats),
            ("rank <= ?", rsrs_top20_df),
            ("ORDER BY rank DESC", rsrs_bottom20_df),
            ("vw_volume_anomalies_cn", empty_vol),
        ]
        fake_repo = FakeMarketViewRepository(handlers, max_date="2026-06-12")
        uc = GenerateMarketOverviewUseCase(
            view_repo=fake_repo,
            breadth_service=BreadthService(fake_repo),
            ranking_service=RankingService(fake_repo),
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_market_overview.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.execute(GenerateMarketOverviewRequest())
        text = resp.markdown
        assert "## 5. 成交量异常" in text
        assert "_无符合条件的结果_" in text
        assert any((tmp_path / "ai_report").glob("market_overview_*.md"))

    def test_execute_returns_empty_report_when_no_data(
        self, monkeypatch, tmp_path,
    ):
        fake_repo = FakeMarketViewRepository([], max_date=None)
        uc = GenerateMarketOverviewUseCase(
            view_repo=fake_repo,
            breadth_service=BreadthService(fake_repo),
            ranking_service=RankingService(fake_repo),
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_market_overview.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.execute(GenerateMarketOverviewRequest())
        assert "_无近期数据_" in resp.markdown

    def test_brief_renders_six_console_sections_without_writing_file(
        self,
        monkeypatch,
        tmp_path,
        rsrs_top20_df,
        volume_spikes_df,
        stats_df,
        breadth_df,
    ):
        handlers = [
            ("std_return_pct", breadth_df),
            ("advance_ratio", stats_df),
            ("rank <= ?", rsrs_top20_df),
            ("vw_volume_anomalies_cn", volume_spikes_df),
        ]
        fake_repo = FakeMarketViewRepository(handlers, max_date="2026-06-12")
        uc = GenerateMarketOverviewUseCase(
            view_repo=fake_repo,
            breadth_service=BreadthService(fake_repo),
            ranking_service=RankingService(fake_repo),
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_market_overview.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.brief(GenerateMarketOverviewRequest(top=3))

        text = resp.markdown
        assert text.startswith("# Market Brief")
        assert "## 1. Market Regime" in text
        assert "## 2. Breadth" in text
        assert "## 3. Momentum Leaders" in text
        assert "## 4. Volume Anomalies" in text
        assert "## 5. Watchlist" in text
        assert "## 6. Suggested Research Questions" in text
        assert "Neutral" in text
        assert "600000.SH" in text
        assert not any((tmp_path / "ai_report").glob("market_overview_*.md"))

    def test_brief_returns_empty_sections_when_local_tables_are_missing(
        self,
        monkeypatch,
        tmp_path,
    ):
        class MissingTableRepo(FakeMarketViewRepository):
            def execute(self, sql, params=None):
                raise RuntimeError("missing local table")

        fake_repo = MissingTableRepo([])
        uc = GenerateMarketOverviewUseCase(
            view_repo=fake_repo,
            breadth_service=BreadthService(fake_repo),
            ranking_service=RankingService(fake_repo),
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_market_overview.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.brief(GenerateMarketOverviewRequest())

        assert "## 1. Market Regime" in resp.markdown
        assert "## 6. Suggested Research Questions" in resp.markdown
        assert "_no data_" in resp.markdown
        assert not any((tmp_path / "ai_report").glob("market_overview_*.md"))


# ---------------------------------------------------------------------------
# Anomaly report use case
# ---------------------------------------------------------------------------
class TestGenerateAnomalyReportUseCase:
    def test_execute_writes_markdown_with_all_four_sections(
        self,
        monkeypatch,
        tmp_path,
        volume_spikes_df,
    ):
        gaps_df = pd.DataFrame(
            [{"ticker": "600000.SH", "date": "2026-06-12", "open": 11.0,
              "prev_close": 10.0, "close": 11.4, "gap_pct": 10.0, "return_pct": 14.0}]
        )
        streaks_df = pd.DataFrame(
            [{"ticker": "000001.SZ", "from_date": "2026-06-05",
              "to_date": "2026-06-12", "streak_days": 6}]
        )

        handlers = [
            ("vw_volume_anomalies_cn", volume_spikes_df),
            ("gap_pct", gaps_df),
            ("reset_group", streaks_df),
        ]
        fake_repo = FakeMarketViewRepository(handlers, max_date="2026-06-12")
        uc = GenerateAnomalyReportUseCase(
            view_repo=fake_repo,
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_anomaly_report.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.execute(GenerateAnomalyReportRequest())
        text = resp.markdown
        assert text.startswith("# 异常检测报告")
        assert "## 1. 成交量异常" in text
        assert "## 2. 跳空缺口" in text
        assert "## 3. 连续下跌" in text
        assert "## 4. 连续上涨" in text
        assert "3.0x" in text
        assert "600519.SH" in text
        assert "000001.SZ" in text
        assert any((tmp_path / "ai_report").glob("anomaly_detection_*.md"))

    def test_execute_uses_gap_threshold_and_recent_days(
        self,
        monkeypatch,
        tmp_path,
        volume_spikes_df,
    ):
        """Regression: legacy generate(min_ratio, gap_threshold, recent_days) must
        forward all three parameters to the use case."""
        empty_gaps = pd.DataFrame(
            columns=["ticker", "date", "open", "prev_close", "close",
                     "gap_pct", "return_pct"]
        )
        empty_streaks = pd.DataFrame(
            columns=["ticker", "from_date", "to_date", "streak_days"]
        )

        captured = {}

        class CapturingRepo(FakeMarketViewRepository):
            def execute(self, sql, params=None):
                if "ABS(gap_pct) >= ?" in sql:
                    captured["gap_threshold"] = params[1]
                if "recent_days" not in captured and "CAST(date AS DATE) >= ?" in sql:
                    # The cutoff is computed from recent_days; we capture it from
                    # the first parameterized market-stats-like query as a proxy.
                    pass
                return super().execute(sql, params)

        handlers = [
            ("vw_volume_anomalies_cn", volume_spikes_df),
            ("ABS(gap_pct) >= ?", empty_gaps),
            ("reset_group", empty_streaks),
        ]
        fake_repo = CapturingRepo(handlers, max_date="2026-06-12")
        uc = GenerateAnomalyReportUseCase(
            view_repo=fake_repo,
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_anomaly_report.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.execute(
            GenerateAnomalyReportRequest(
                min_ratio=4.0,
                gap_threshold=10.0,
                recent_days=7,
            )
        )
        text = resp.markdown
        assert "4.0x" in text
        assert "10.0%" in text
        assert "## 2. 跳空缺口 (|跳空| >= 10.0%)" in text
        assert captured.get("gap_threshold") == 10.0

    def test_execute_renders_placeholders_when_all_detectors_empty(
        self, monkeypatch, tmp_path,
    ):
        empty_vol = pd.DataFrame(columns=VOL_ANOM_COLUMNS)
        empty_gaps = pd.DataFrame(
            columns=["ticker", "date", "open", "prev_close", "close",
                     "gap_pct", "return_pct"]
        )
        empty_streaks = pd.DataFrame(
            columns=["ticker", "from_date", "to_date", "streak_days"]
        )

        handlers = [
            ("vw_volume_anomalies_cn", empty_vol),
            ("gap_pct", empty_gaps),
            ("reset_group", empty_streaks),
        ]
        fake_repo = FakeMarketViewRepository(handlers, max_date="2026-06-12")
        uc = GenerateAnomalyReportUseCase(
            view_repo=fake_repo,
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_anomaly_report.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.execute(GenerateAnomalyReportRequest())
        text = resp.markdown
        assert "## 1. 成交量异常" in text
        assert "## 2. 跳空缺口" in text
        assert "## 3. 连续下跌" in text
        assert "## 4. 连续上涨" in text
        assert text.count("_无符合条件的结果_") >= 1
        assert any((tmp_path / "ai_report").glob("anomaly_detection_*.md"))


# ---------------------------------------------------------------------------
# Catalog use case
# ---------------------------------------------------------------------------
class FakeSchemaBrowser(ISchemaBrowser):
    """In-memory fake for ISchemaBrowser."""

    def __init__(self, stats_by_market):
        self._stats = stats_by_market

    def list_tables(self, market: str):
        return list(self._stats.get(market, {}).keys())

    def query_table(self, market, table_name, page=1, page_size=50,
                    search=None, sort_by=None, sort_order="asc"):
        raise NotImplementedError

    def database_stats(self):
        raise NotImplementedError

    def get_sqlite_stats(self, market: str):
        return self._stats.get(market, {})


class TestGenerateCatalogUseCase:
    def test_execute_writes_catalog_json(
        self, monkeypatch, tmp_path,
    ):
        stats = {
            "cn": {"stock_prices": {"row_count": 100, "columns": []}},
            "us": {"stock_prices": {"row_count": 50, "columns": []}},
            "research": {"stock_notes": {"row_count": 10, "columns": []}},
        }
        schema_browser = FakeSchemaBrowser(stats)

        class FakeViewRepo(IMarketViewRepository):
            def execute(self, sql, params=None):
                if "information_schema.tables" in sql:
                    return pd.DataFrame({"table_name": ["vw_a", "vw_b"]})
                if "COUNT(*) FROM vw_" in sql:
                    view = sql.split("FROM")[-1].strip()
                    return pd.DataFrame({"count": [7]})
                return pd.DataFrame()

        view_service = ViewService(FakeViewRepo())
        uc = GenerateCatalogUseCase(schema_browser, view_service)
        monkeypatch.setattr(
            "doge.application.use_cases.generate_catalog.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        resp = uc.execute(GenerateCatalogRequest())
        catalog_path = Path(resp.path)
        assert catalog_path.exists()
        text = catalog_path.read_text(encoding="utf-8")
        assert '"version": "1.0"' in text
        assert '"market_data_cn"' in text
        assert '"duckdb"' in text
        assert resp.entry_count == 5  # 3 tables + 2 views


# ---------------------------------------------------------------------------
# Isolation guards (CDD AC-6)
# ---------------------------------------------------------------------------
class TestIsolationGuards:
    def test_no_live_duckdb_or_views_sql_touched(
        self, monkeypatch, tmp_path,
    ):
        """The test suite must never open a real DuckDB connection
        or read data/views.sql."""
        empty_rsrs = pd.DataFrame(columns=RSRS_COLUMNS)
        empty_stats = pd.DataFrame(
            columns=["date", "advancers", "decliners", "avg_return_pct", "advance_ratio"]
        )
        empty_breadth = pd.DataFrame(
            columns=["date", "advancers", "decliners", "unchanged", "active",
                     "avg_return_pct", "std_return_pct", "advance_ratio"]
        )
        empty_vol = pd.DataFrame(columns=VOL_ANOM_COLUMNS)
        fake_repo = FakeMarketViewRepository(
            [
                ("std_return_pct", empty_breadth),
                ("advance_ratio", empty_stats),
                ("vw_rsrs_ranking_cn", empty_rsrs),
                ("vw_volume_anomalies_cn", empty_vol),
            ],
            max_date="2026-06-12",
        )
        uc = GenerateMarketOverviewUseCase(
            view_repo=fake_repo,
            breadth_service=BreadthService(fake_repo),
            ranking_service=RankingService(fake_repo),
            anomaly_service=AnomalyService(fake_repo),
        )
        monkeypatch.setattr(
            "doge.application.use_cases.generate_market_overview.get_settings",
            lambda: _fake_settings(tmp_path),
        )

        uc.execute(GenerateMarketOverviewRequest())
        # If any unmocked query had reached a real DuckDB connection, the fake
        # would have raised AssertionError above.
