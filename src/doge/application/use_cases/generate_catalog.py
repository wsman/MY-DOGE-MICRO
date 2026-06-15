"""Generate catalog use case.

Generates a catalog.json from schema and view metadata.
Replaces ``src/ai_analysis/catalog_generator.py`` with a port-backed
implementation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from doge.application.contracts.request import GenerateCatalogRequest
from doge.application.contracts.response import CatalogResponse
from doge.config import get_settings
from doge.core.ports.repository import ISchemaBrowser
from doge.core.services.view_service import ViewService


class GenerateCatalogUseCase:
    """Generate a catalog.json from schema and view metadata."""

    def __init__(
        self,
        schema_browser: ISchemaBrowser,
        view_service: ViewService,
    ) -> None:
        """Initialize with injected services.

        Args:
            schema_browser: SQLite schema introspection port.
            view_service: DuckDB view introspection service.
        """
        self._schema_browser = schema_browser
        self._view_service = view_service

    def execute(self, request: GenerateCatalogRequest) -> CatalogResponse:
        """Run the catalog workflow and write ``catalog.json``."""
        settings = get_settings()
        catalog_path = settings.catalog_json
        catalog_path.parent.mkdir(parents=True, exist_ok=True)

        cn_tables = self._schema_browser.get_sqlite_stats("cn")
        us_tables = self._schema_browser.get_sqlite_stats("us")
        research_tables = self._schema_browser.get_sqlite_stats("research")
        duckdb_views = self._view_service.get_view_stats()

        cn_sp = cn_tables.get("stock_prices", {})
        us_sp = us_tables.get("stock_prices", {})

        catalog = {
            "version": "1.0",
            "databases": {
                "market_data_cn": {
                    "path": "data/market_data_cn.db",
                    "engine": "sqlite",
                    "description": "A-shares daily OHLCV",
                    "tables": cn_tables,
                },
                "market_data_us": {
                    "path": "data/market_data_us.db",
                    "engine": "sqlite",
                    "description": "US stocks daily OHLCV",
                    "tables": us_tables,
                },
                "research_insights": {
                    "path": "data/research_insights.db",
                    "engine": "sqlite",
                    "description": "AI research report archive",
                    "tables": research_tables,
                },
            },
            "duckdb": {
                "path": "data/market.duckdb",
                "views_sql": "src/doge/infrastructure/database/views.sql",
                "views_sql_mirror": "data/views.sql",
                "engine": "duckdb",
                "description": "Columnar analytics - reads SQLite zero-copy",
                "views": duckdb_views,
                "usage": "duckdb data/market.duckdb -c 'SELECT * FROM vw_market_breadth_cn LIMIT 10'",
            },
            "analysis_scripts": {
                "market_overview": "src/ai_analysis/market_overview.py",
                "anomaly_detection": "src/ai_analysis/anomaly_detection.py",
                "catalog_generator": "src/ai_analysis/catalog_generator.py",
            },
            "report_directory": "ai_report/",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        catalog_path.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return CatalogResponse(
            path=str(catalog_path),
            entry_count=len(cn_tables) + len(us_tables) + len(research_tables) + len(duckdb_views),
        )
