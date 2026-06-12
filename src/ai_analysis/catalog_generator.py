"""
数据字典生成器 —— 自动扫描数据库结构并生成 catalog.json

Usage:
    python src/ai_analysis/catalog_generator.py
"""

import json
import os

# S002-009 / TR-011: package-qualified sibling import (editable install), no
# sys.path shim (ADR-0001 forbidden pattern ``sys_path_insert``). The legacy
# ``get_project_path`` symbol never existed on the ``ai_analysis`` package, so
# the prior ``from ai_analysis import get_project_path`` made this module
# unimportable; catalog output path is now sourced from get_settings().
from ai_analysis import (
    CN_DB,
    US_DB,
    RESEARCH_DB,
    get_sqlite_stats,
    connect_duckdb,
    run_views_sql,
    get_duckdb_view_stats,
)
from doge.config import get_settings


def generate_catalog():
    """生成完整数据字典"""
    con = connect_duckdb()
    run_views_sql(con)

    cn_tables = get_sqlite_stats(CN_DB)
    us_tables = get_sqlite_stats(US_DB)
    research_tables = get_sqlite_stats(RESEARCH_DB)
    duckdb_views = get_duckdb_view_stats(con)
    con.close()

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
    }

    from datetime import datetime
    catalog["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    catalog_path = str(get_settings().catalog_json)
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print("catalog.json written to {}".format(catalog_path))
    cn_sp = cn_tables.get("stock_prices", {})
    us_sp = us_tables.get("stock_prices", {})
    print("  CN: {} stocks, {:,} rows".format(
        cn_sp.get("distinct_tickers", 0), cn_sp.get("row_count", 0)))
    print("  US: {} stocks, {:,} rows".format(
        us_sp.get("distinct_tickers", 0), us_sp.get("row_count", 0)))
    print("  Views: {}".format(len(duckdb_views)))
    return catalog


if __name__ == "__main__":
    generate_catalog()
